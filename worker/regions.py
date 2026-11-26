"""v0.4.0: local multiscale ink proposals and exhaustive box-reference evaluation."""
import argparse
import json
from pathlib import Path
import worker as w

VERSION = "0.4.0"
# Width and height fractions of rendered page; fixed engineering parameters.
SCALES = ((.045, .018), (.09, .036), (.18, .072))


def starts(size, window):
    w.require(1 <= window <= size, "Invalid window")
    return sorted(set(range(0, size-window+1, max(1, window//2))) | {size-window})


def propose(pdf, expected_sha, groups, out, pages=None, max_regions=30000):
    import fitz
    import numpy as np
    from PIL import Image
    w.require(w.sha(pdf) == expected_sha, "PDF SHA256 mismatch")
    w.require(type(max_regions) is int and 1 <= max_regions <= 100000, "Invalid region budget")
    mapping = w.read(groups); out = Path(out)
    w.require(not out.exists(), "Output directory already exists")
    with fitz.open(pdf) as doc:
        pages = sorted(int(k) for k in mapping) if pages is None else pages
        w.require(isinstance(pages, list) and 0 < len(pages) <= 213 and len(set(pages)) == len(pages), "Invalid pages")
        w.require(all(type(p) is int and 1 <= p <= len(doc) and isinstance(mapping.get(str(p)), str) and mapping[str(p)].strip() for p in pages), "Invalid page or leaf group")
        # Incomplete runs never publish a manifest. Existing output cannot be overwritten.
        out.mkdir(parents=True); (out/'crops').mkdir()
        records = []; screened = 0; dimensions = {}
        for page in sorted(pages):
            pix = doc[page-1].get_pixmap(dpi=200, colorspace=fitz.csRGB, alpha=False)
            img = Image.frombytes('RGB', (pix.width,pix.height),pix.samples)
            width,height = img.size; dimensions[str(page)] = [width,height]
            ink = np.asarray(img.convert('L')) < 160
            integral = np.pad(ink.cumsum(0,dtype=np.int64).cumsum(1,dtype=np.int64), ((1,0),(1,0)))
            seen = set()
            for scale,(wf,hf) in enumerate(SCALES):
                bw,bh = max(1,round(width*wf)),max(1,round(height*hf))
                for y in starts(height,bh):
                    for x in starts(width,bw):
                        box=(x,y,x+bw,y+bh)
                        if box in seen: continue
                        seen.add(box); screened += 1
                        count=int(integral[y+bh,x+bw]-integral[y,x+bw]-integral[y+bh,x]+integral[y,x])
                        if not .015 <= count/(bw*bh) <= .35: continue
                        w.require(len(records)<max_regions, "Region budget exhausted; no complete manifest")
                        rid=f'M{page:04d}-{scale}-{x}-{y}'; name=f'crops/{rid}.png'
                        img.crop(box).save(out/name)
                        records.append(dict(id=rid,page=page,group=mapping[str(page)],box=[x/width,y/height,(x+bw)/width,(y+bh)/height],pixel_box=list(box),file=name,sha256=w.sha(out/name)))
    manifest=dict(version=VERSION,source_sha256=expected_sha,groups_sha256=w.sha(groups),dpi=200,renderer=fitz.VersionBind,
                  proposal_method='multiscale-dark-pixel-v1',scales=SCALES,screened=screened,page_dimensions=dimensions,regions=records)
    w.write(out/'manifest.json',manifest)
    return {'screened':screened,'proposals':len(records),'scientific_status':'UNADJUDICATED'}


def valid_box(b):
    return isinstance(b,list) and len(b)==4 and all(type(x) in (int,float) for x in b) and 0<=b[0]<b[2]<=1 and 0<=b[1]<b[3]<=1


def iou(a,b):
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    return inter/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)


def matching(pred, truth, threshold):
    # Maximum-cardinality bipartite matching, iterative augmenting paths.
    edges=[[j for j,t in enumerate(truth) if iou(b,t)>=threshold] for b in pred]
    right={}; left={}
    for start in range(len(pred)):
        queue=[start]; parent={}; visited={start}; end=None
        for u in queue:
            for v in edges[u]:
                if v in parent: continue
                parent[v]=u
                if v not in right:
                    end=v; break
                nxt=right[v]
                if nxt not in visited: visited.add(nxt); queue.append(nxt)
            if end is not None: break
        while end is not None:
            u=parent[end]; old=left.get(u); left[u]=end; right[end]=u; end=old
    return len(right)


def evaluate(manifest, reference, out):
    """Fixed IoU thresholds; only explicitly exhaustive pages are eligible."""
    m=w.read(manifest); ref=w.read(reference); out=Path(out)
    w.require(not out.exists(), 'Evaluation output already exists')
    w.require(ref['source_sha256']==m['source_sha256'] and ref['groups_sha256']==m['groups_sha256'], 'Reference source/group mismatch')
    w.require(ref.get('exhaustive') is True and isinstance(ref.get('reviewer'),str) and ref['reviewer'].strip(), 'Exhaustive independent reference declaration required')
    pages=ref['pages']; w.require(isinstance(pages,dict) and pages and set(pages)==set(m['page_dimensions']), 'Reference must cover exactly the processed pages')
    records=m['regions']; w.require(len({r['id'] for r in records})==len(records), 'Duplicate proposal IDs')
    for r in records:
        w.require(str(r['page']) in pages and valid_box(r['box']), 'Invalid proposal')
        w.require(w.sha(w.within(Path(manifest).parent,r['file']))==r['sha256'], 'Crop hash mismatch')
    for boxes in pages.values():
        w.require(isinstance(boxes,list) and all(valid_box(b) for b in boxes) and len(set(map(tuple,boxes)))==len(boxes), 'Invalid or duplicate reference box')
    results={}
    for threshold in (.3,.5,.7):
        rows=[]
        for page,truth in sorted(pages.items(),key=lambda x:int(x[0])):
            pred=[r['box'] for r in records if str(r['page'])==page]
            n=matching(pred,truth,threshold)
            covered=sum(any(iou(b,t)>=threshold for b in pred) for t in truth)
            rows.append(dict(page=int(page),proposals=len(pred),reference=len(truth),matched=n,covered=covered))
        n=sum(r['matched'] for r in rows); p=sum(r['proposals'] for r in rows); t=sum(r['reference'] for r in rows); c=sum(r['covered'] for r in rows)
        results[str(threshold)]=dict(matched=n,proposals=p,reference=t,one_to_one_precision=n/p if p else None,one_to_one_recall=n/t if t else None,proposal_recall=c/t if t else None,pages=rows)
    report=dict(version=VERSION,manifest_sha256=w.sha(manifest),reference_sha256=w.sha(reference),metrics=results,scientific_status='UNADJUDICATED',note='Reference exhaustiveness and reviewer independence are declared, not established by software. Unmatched proposals are not necessarily non-script.')
    w.write(out,report); return report


def main():
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('propose')
    for k in ('pdf','expected_sha','groups','out'): p.add_argument(k)
    p.add_argument('--pages',nargs='+',type=int); p.add_argument('--max-regions',type=int,default=30000)
    p=sub.add_parser('evaluate')
    for k in ('manifest','reference','out'): p.add_argument(k)
    args=vars(parser.parse_args()); action=args.pop('action'); print(json.dumps({'propose':propose,'evaluate':evaluate}[action](**args),indent=2))


if __name__=='__main__': main()

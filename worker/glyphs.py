"""v0.5.0 local glyph proposals, corrected-box consensus and prototype classifier."""
import argparse
import hashlib
import json
from pathlib import Path
import worker as w

VERSION = '0.5.0'
UNKNOWN = 'unknown'


def boxes(image):
    """Vertical projection baseline for single-line crops; no glyph assertion."""
    import numpy as np
    ink = np.asarray(image.convert('L')) < 160
    active = ink.any(axis=0)
    runs = []; start = None
    for x, on in enumerate([*active, False]):
        if on and start is None: start = x
        if not on and start is not None:
            ys = np.where(ink[:, start:x].any(axis=1))[0]
            runs.append([start, int(ys[0]), x, int(ys[-1])+1]); start = None
    return runs


def inventory(path):
    obj = w.read(path); labels = obj['labels']
    w.require(isinstance(obj['convention'], str) and obj['convention'].strip(), 'Convention required')
    w.require(isinstance(labels, list) and 2 <= len(labels) <= 256 and all(isinstance(x,str) and x and x != UNKNOWN for x in labels) and len(set(labels)) == len(labels), 'Invalid inventory')
    return obj


def propose(manifest, output, reviewer):
    from PIL import Image
    m = w.dataset(manifest); output = Path(output)
    w.require(not output.exists() and reviewer.strip(), 'New output and reviewer required')
    regions = {}
    for r in m['regions']:
        with Image.open(w.within(Path(manifest).parent,r['file'])) as im:
            regions[r['id']] = {'status':'unreviewed','glyphs':[{'box':b,'label':UNKNOWN} for b in boxes(im)]}
    w.write(output,dict(schema=1,manifest_sha256=w.sha(manifest),reviewer=reviewer,regions=regions))


def checked_review(path, manifest, sizes, labels):
    a = w.read(path)
    w.require(a['schema']==1 and a['manifest_sha256']==w.sha(manifest) and isinstance(a['reviewer'],str) and a['reviewer'].strip(), 'Invalid review provenance')
    w.require(set(a['regions'])==set(sizes), 'Review must account for every region')
    for rid, row in a['regions'].items():
        w.require(row['status'] in ('unreviewed','single_line','reject','uncertain'), 'Invalid review status')
        width,height=sizes[rid]; seen=set()
        for g in row['glyphs']:
            b=g['box']; w.require(isinstance(b,list) and len(b)==4 and all(type(v) is int for v in b) and 0<=b[0]<b[2]<=width and 0<=b[1]<b[3]<=height, 'Invalid glyph box')
            w.require(tuple(b) not in seen and (g['label'] in labels or g['label']==UNKNOWN), 'Duplicate box or invalid label'); seen.add(tuple(b))
        if row['status']=='single_line':
            w.require(bool(row['glyphs']), 'Empty accepted line')
            ordered=sorted(row['glyphs'],key=lambda g:g['box'][0])
            w.require(all(a['box'][2]<=b['box'][0] for a,b in zip(ordered,ordered[1:])), 'Overlapping glyph boxes; mark uncertain')
    return a


def feature(im):
    from PIL import ImageOps
    import numpy as np
    # Preserve aspect ratio and padding. No inferred stroke or glyph normalization.
    return (1-np.asarray(ImageOps.pad(im.convert('L'),(32,32),color=255),dtype=np.float32)/255).reshape(-1)


def cohorts(manifest,left,right,alphabet,split):
    from PIL import Image
    labels=inventory(alphabet)['labels']; m=w.dataset(manifest); sizes={}
    for r in m['regions']:
        with Image.open(w.within(Path(manifest).parent,r['file'])) as im: sizes[r['id']]=im.size
    a,b=[checked_review(p,manifest,sizes,labels) for p in (left,right)]
    w.require(a['reviewer']!=b['reviewer'],'Distinct reviewer IDs required')
    s=w.read(split); groups={r['group'] for r in m['regions']}
    w.require(set(s)=={'train','test'} and all(isinstance(v,list) and v and len(set(v))==len(v) for v in s.values()), 'Invalid split')
    train,test=set(s['train']),set(s['test']); w.require(not train & test and train|test==groups,'Physical-leaf leakage or incomplete split')
    sets={'train':[],'test':[]}; excluded={'train':0,'test':0}; unknown_labels={'train':0,'test':0}; fingerprints={'train':set(),'test':set()}; pages={}
    for r in m['regions']:
        side='train' if r['group'] in train else 'test'; rid=r['id']
        w.require(pages.setdefault(r['page'],side)==side,'Same page across split')
        x,y=a['regions'][rid],b['regions'][rid]
        if x['status']!='single_line' or x!=y:
            excluded[side]+=1; continue
        with Image.open(w.within(Path(manifest).parent,r['file'])) as im:
            for g in x['glyphs']:
                f=feature(im.crop(g['box'])); fingerprints[side].add(hashlib.sha256(f.tobytes()).hexdigest())
                if g['label']==UNKNOWN:
                    unknown_labels[side]+=1; continue
                sets[side].append((rid,g['box'],g['label'],f))
    w.require(not fingerprints['train'] & fingerprints['test'],'Exact normalized glyph duplicate across split')
    w.require(all({v[2] for v in rows}==set(labels) for rows in sets.values()),'Every inventory label needs agreed train and test support')
    return labels,sets,excluded,unknown_labels


def classify(features, prototypes):
    import torch
    distances=(features[:,None,:]-prototypes[None,:,:]).square().mean(2)
    best,idx=distances.topk(2,largest=False)
    return [(int(i),float(d),float(gap)) for i,d,gap in zip(idx[:,0].tolist(),best[:,0].tolist(),(best[:,1]-best[:,0]).tolist())]


def decision(label,d,gap):
    return label if d<=.12 and gap>=.005 else UNKNOWN


def train(manifest,left,right,alphabet,split,out,device='auto'):
    import torch
    labels,sets,excluded,unknown_labels=cohorts(manifest,left,right,alphabet,split); out=Path(out)
    w.require(not out.exists(),'Output already exists; do not rescore holdout')
    info=w.device_info(device); dev=info['device']
    def tensor(rows): return torch.tensor([r[3].tolist() for r in rows],dtype=torch.float32,device=dev)
    prototypes=torch.stack([tensor([r for r in sets['train'] if r[2]==label]).mean(0) for label in labels])
    rows=[]
    for start in range(0,len(sets['test']),128):
        batch=sets['test'][start:start+128]
        for row,(i,d,gap) in zip(batch,classify(tensor(batch),prototypes)):
            rows.append(dict(region_id=row[0],box=row[1],truth=row[2],predicted=decision(labels[i],d,gap)))
    n=len(rows); correct=sum(r['truth']==r['predicted'] for r in rows); unknown=sum(r['predicted']==UNKNOWN for r in rows)
    confusion={l:{k:sum(r['truth']==l and r['predicted']==k for r in rows) for k in labels+[UNKNOWN]} for l in labels}
    out.mkdir(parents=True); model=out/'glyph_model.json'
    w.write(model,dict(version=VERSION,labels=labels,prototypes=prototypes.cpu().tolist(),inventory_sha256=w.sha(alphabet),code_sha256=w.sha(__file__),thresholds=[.12,.005]))
    report=dict(version=VERSION,scientific_status='UNADJUDICATED',environment=info,model_sha256=w.sha(model),input_sha256={k:w.sha(v) for k,v in dict(manifest=manifest,left=left,right=right,alphabet=alphabet,split=split).items()},train_n=len(sets['train']),test_n=n,excluded_regions=excluded,excluded_unknown_glyphs=unknown_labels,accuracy_including_unknown=correct/n,coverage=(n-unknown)/n,confusion=confusion,rows=rows)
    w.write(out/'glyph_report.json',report); return report


def predict(manifest, review, alphabet, model_path, report_path, output, device='auto'):
    import torch
    from PIL import Image
    labels=inventory(alphabet)['labels']; m=w.dataset(manifest); model=w.read(model_path); report=w.read(report_path)
    w.require(report['model_sha256']==w.sha(model_path) and model['inventory_sha256']==w.sha(alphabet) and model['code_sha256']==w.sha(__file__) and model['labels']==labels and model['thresholds']==[.12,.005], 'Model provenance mismatch')
    w.require(not Path(output).exists(), 'Output already exists')
    sizes={}
    for r in m['regions']:
        with Image.open(w.within(Path(manifest).parent,r['file'])) as im: sizes[r['id']]=im.size
    a=checked_review(review,manifest,sizes,labels); info=w.device_info(device); dev=info['device']
    prototypes=torch.tensor(model['prototypes'],dtype=torch.float32,device=dev)
    w.require(prototypes.shape==(len(labels),1024) and bool(torch.isfinite(prototypes).all()) and bool(((prototypes>=0)&(prototypes<=1)).all()), 'Invalid model prototypes')
    rows=[]; excluded=0
    for r in m['regions']:
        line=a['regions'][r['id']]
        if line['status']!='single_line': excluded+=1; continue
        glyphs=sorted(line['glyphs'],key=lambda g:g['box'][0])
        with Image.open(w.within(Path(manifest).parent,r['file'])) as im:
            for start in range(0,len(glyphs),128):
                chunk=glyphs[start:start+128]
                f=torch.tensor([feature(im.crop(g['box'])).tolist() for g in chunk],dtype=torch.float32,device=dev)
                for g,(i,d,gap) in zip(chunk,classify(f,prototypes)):
                    rows.append(dict(region_id=r['id'],box=g['box'],predicted=decision(labels[i],d,gap),distance=d,margin=gap))
    result=dict(version=VERSION,scientific_status='UNADJUDICATED',environment=info,manifest_sha256=w.sha(manifest),review_sha256=w.sha(review),model_sha256=w.sha(model_path),excluded_regions=excluded,rows=rows)
    w.write(output,result); return result


def main():
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('propose')
    for k in ('manifest','output','reviewer'): p.add_argument(k)
    p=sub.add_parser('train')
    for k in ('manifest','left','right','alphabet','split','out'): p.add_argument(k)
    p.add_argument('--device',choices=['auto','cpu','cuda'],default='auto')
    p=sub.add_parser('predict')
    for k in ('manifest','review','alphabet','model_path','report_path','output'): p.add_argument(k)
    p.add_argument('--device',choices=['auto','cpu','cuda'],default='auto')
    args=vars(parser.parse_args()); action=args.pop('action'); result={'propose':propose,'train':train,'predict':predict}[action](**args)
    if result is not None: print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))


if __name__=='__main__': main()

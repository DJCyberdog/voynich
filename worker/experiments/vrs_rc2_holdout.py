"""RC2-02h offline box evaluation. No recognition, model tuning or scientific approval."""
import argparse
import hashlib
import json
from collections import deque
from pathlib import Path

METHODS=('raster','improved_raster','vector','hybrid')
THRESHOLDS=((1,2),(3,4))
KINDS=('glyph','compound','other_handwriting','mixed','illustration','material','blank','unknown')
NEGATIVE={'other_handwriting','illustration','material','blank'}
MAX_BYTES=32*1024*1024

def require(ok,msg):
    if not ok:raise ValueError(msg)

def fields(value,names):
    require(type(value) is dict and set(value)==set(names),'Unexpected fields')

def digest(s):
    require(type(s) is str and len(s)==64 and all(x in '0123456789abcdef' for x in s),'Invalid digest')
    return s

def text(s):
    require(type(s) is str and 0<len(s.strip())<=256,'Invalid identifier')
    return s

def box(b,extent):
    require(type(b) is list and len(b)==4 and all(type(x) is int for x in b),'Invalid box')
    l,t,r,z=b; L,T,R,Z=extent
    require(L<=l<r<=R and T<=t<z<=Z,'Box outside evaluation window')
    return tuple(b)

def intersection(a,b):
    return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))

def area(b):return (b[2]-b[0])*(b[3]-b[1])

def match(pred,ref,threshold):
    """Deterministic maximum-cardinality one-to-one matching at fixed box IoU."""
    num,den=threshold
    edges=[]
    for p in pred:
        links=[]
        for j,b in enumerate(ref):
            i=intersection(p,b); u=area(p)+area(b)-i
            if i*den>=u*num:links.append((j,i/u))
        edges.append([j for j,_ in sorted(links,key=lambda x:(-x[1],x[0]))])
    p_to_r={}; r_to_p={}
    for i in range(len(pred)):
        queue=deque([i]); parent={}; seen={i}; end=None
        while queue and end is None:
            p=queue.popleft()
            for j in edges[p]:
                if j in parent:continue
                parent[j]=p
                if j not in r_to_p:
                    end=j;break
                other=r_to_p[j]
                if other not in seen:seen.add(other);queue.append(other)
        while end is not None:
            p=parent[end];old=p_to_r.get(p)
            p_to_r[p]=end;r_to_p[end]=p;end=old
    return len(p_to_r)

def read_pinned(path,sha):
    digest(sha)
    with Path(path).open('rb') as f:raw=f.read(MAX_BYTES+1)
    require(len(raw)<=MAX_BYTES and hashlib.sha256(raw).hexdigest()==sha,'Input pin or size mismatch')
    def unique(pairs):
        d={}
        for k,v in pairs:
            require(k not in d,'Duplicate JSON key');d[k]=v
        return d
    def reject(s):raise ValueError('Nonfinite JSON')
    return json.loads(raw,object_pairs_hook=unique,parse_constant=reject)

def evaluate(reference,prediction,reference_sha):
    """Declared provenance is checked for consistency, not externally certified."""
    digest(reference_sha)
    fields(reference,('schema','source_sha256','registration_sha256','rights_sha256','independent_review_sha256','development_leaves','windows'))
    fields(prediction,('schema','source_sha256','reference_sha256','freeze_sha256','methods'))
    require(type(reference['schema']) is int and reference['schema']==1 and type(prediction['schema']) is int and prediction['schema']==1,'Unsupported schema')
    for k in ('source_sha256','registration_sha256','rights_sha256','independent_review_sha256'):digest(reference[k])
    require(prediction['source_sha256']==reference['source_sha256'] and prediction['reference_sha256']==reference_sha,'Source/reference binding mismatch')
    digest(prediction['freeze_sha256'])
    dev=reference['development_leaves'];require(type(dev) is list and len(dev)<=10000,'Invalid development groups')
    dev=set(map(text,dev));windows=reference['windows']
    require(type(windows) is list and 0<len(windows)<=1000,'Invalid window count')
    table={}; page_leaves={}; extents={}
    for w in windows:
        fields(w,('id','page','leaf','image_sha256','size','box','kind','exhaustive','boxes'))
        wid=text(w['id']);leaf=text(w['leaf']);digest(w['image_sha256'])
        require(wid not in table and leaf not in dev,'Duplicate window or development leaf leakage')
        require(type(w['page']) is int and 1<=w['page']<=214,'Invalid PDF page')
        size=w['size'];require(type(size) is list and len(size)==2 and all(type(x) is int and 0<x<=100000 for x in size),'Invalid native size')
        require(page_leaves.setdefault(w['page'],(leaf,w['image_sha256'],tuple(size)))==(leaf,w['image_sha256'],tuple(size)),'Conflicting page identity')
        extent=box(w['box'],(0,0,*size))
        previous=extents.setdefault(w['page'],[])
        require(not any(intersection(extent,b) for b in previous),'Overlapping holdout windows')
        previous.append(extent)
        kind=w['kind'];require(kind in KINDS and type(w['exhaustive']) is bool,'Invalid annotation scope')
        require(type(w['boxes']) is list and len(w['boxes'])<=512,'Reference box budget')
        targets=[box(b,extent) for b in w['boxes']]
        require(len(set(targets))==len(targets),'Duplicate reference box')
        require((kind in ('glyph','compound') and bool(targets)) or (kind not in ('glyph','compound') and not targets),'Incompatible annotation class')
        require(kind not in NEGATIVE or w['exhaustive'],'Negative window requires explicit exhaustive annotation')
        table[wid]=(kind,w['exhaustive'],extent,targets)
    methods=prediction['methods'];fields(methods,METHODS)
    results={}
    for name in METHODS:
        m=methods[name];fields(m,('implementation_sha256','windows'));digest(m['implementation_sha256'])
        require(type(m['windows']) is dict and set(m['windows'])==set(table),'Method coverage mismatch')
        totals={f'{a}/{b}':dict(tp=0,fn=0,fp=0,unresolved=0,excluded_predictions=0,positive_references=0,negative_predictions_by_class={k:0 for k in sorted(NEGATIVE)}) for a,b in THRESHOLDS}
        diagnostics=dict(split_overlap=0,merge_overlap=0)
        for wid,(kind,exhaustive,extent,targets) in table.items():
            rows=m['windows'][wid];require(type(rows) is list and len(rows)<=512,'Prediction box budget')
            # Duplicate predictions are kept: one can match, remaining ones are counted.
            pred=[box(b,extent) for b in rows]
            if kind in ('glyph','compound'):
                diagnostics['split_overlap']+=sum(sum(intersection(p,b)>0 for p in pred)>1 for b in targets)
                diagnostics['merge_overlap']+=sum(sum(intersection(p,b)>0 for b in targets)>1 for p in pred)
            for threshold in THRESHOLDS:
                a,b=threshold;out=totals[f'{a}/{b}']
                if kind in ('mixed','unknown'):
                    out['excluded_predictions']+=len(pred);continue
                if kind in NEGATIVE:
                    out['fp']+=len(pred);out['negative_predictions_by_class'][kind]+=len(pred);continue
                count=match(pred,targets,threshold)
                out['tp']+=count;out['fn']+=len(targets)-count;out['positive_references']+=len(targets)
                out['fp' if exhaustive else 'unresolved']+=len(pred)-count
        for out in totals.values():
            # Unannotated positives cannot establish precision; mixed/unknown are
            # reported separately and not folded into the scored denominator.
            tp,fn,fp=out['tp'],out['fn'],out['fp']
            out['annotated_reference_recall']=tp/(tp+fn) if tp+fn else None
            out['scored_precision']=tp/(tp+fp) if tp+fp and not out['unresolved'] else None
        results[name]=dict(thresholds=totals,overlap_diagnostics=diagnostics)
    return dict(schema=1,status='METRICS_ONLY_NOT_SCIENTIFIC_ACCEPTANCE',source_sha256=reference['source_sha256'],reference_sha256=reference_sha,freeze_sha256=prediction['freeze_sha256'],windows=len(table),leaves=len({v[0] for v in page_leaves.values()}),classes={k:sum(row[0]==k for row in table.values()) for k in KINDS},methods=results,limitations=['Declared pins do not authenticate independent review, rights, physical leaf grouping or registration.','Box overlap is not pixel ink or glyph identity accuracy.','Positive-only reference recall is not population recall.','No inferred negatives or automatic decisions.'])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('reference');p.add_argument('reference_sha256');p.add_argument('prediction');p.add_argument('prediction_sha256')
    a=p.parse_args()
    print(json.dumps(evaluate(read_pinned(a.reference,a.reference_sha256),read_pinned(a.prediction,a.prediction_sha256),a.reference_sha256),sort_keys=True,indent=2,allow_nan=False))

if __name__=='__main__':main()

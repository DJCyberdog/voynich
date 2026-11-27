"""Bounded, non-destructive alternatives for existing native grouping records."""
import hashlib
import json
from collections import defaultdict
import numpy as np

POLICY = 'native-hybrid-alternatives-v1'
MASKS = ('union', 'majority', 'intersection')
MAX_ALTERNATIVES = 100000
MAX_EXPANSIONS = 500000


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def lineage(parent, child, p_rows, c_rows):
    """Actual shared-pixel membership, not overlap of enclosing rectangles."""
    require(parent.shape == child.shape, 'unaligned masks')
    active = child > 0
    require(not np.any(active & (parent == 0)), 'non-nested masks')
    pairs, counts = np.unique(np.stack((child[active], parent[active]), axis=1), axis=0, return_counts=True)
    require(len(pairs) == len(c_rows) and len(np.unique(pairs[:,0])) == len(c_rows), 'child has multiple parents or missing label')
    result = []; retained = defaultdict(int)
    for (c, p), count in zip(pairs, counts):
        require(1 <= c <= len(c_rows) and 1 <= p <= len(p_rows), 'invalid label')
        cr, pr = c_rows[c-1], p_rows[p-1]
        require(int(count) == cr['area'], 'child area mismatch')
        retained[int(p)] += int(count)
        result.append(dict(child=cr['id'], parent=pr['id'], shared_pixels=int(count), identical=int(count)==pr['area']))
    require(all(retained.get(i,0) <= r['area'] for i,r in enumerate(p_rows,1)), 'parent area mismatch')
    return dict(links=result, parents_without_child=[r['id'] for i,r in enumerate(p_rows,1) if i not in retained],
                removed_pixels=sum(r['area']-retained.get(i,0) for i,r in enumerate(p_rows,1)))


def split_options(mask, row):
    """Projection-valley hypotheses; both disjoint parts retain every pixel."""
    h,w = mask.shape
    if max(h,w)>64 or min(h,w)<3:
        return []
    out=[]; l,t,_,_=row['box']
    for axis, m, offset in [('x',mask,l),('y',mask.T,t)]:
        if m.shape[1]<9:
            continue
        p=m.sum(0); candidates=[]
        for cut in range(3,len(p)-2):
            left,right=p[:cut],p[cut:]
            neck=int(min(p[cut-1],p[cut]))
            peak=int(min(left.max(),right.max()))
            if left.sum()>=6 and right.sum()>=6 and neck>0 and neck*3<=peak:
                candidates.append((neck/peak,abs(cut-len(p)/2),cut))
        if not candidates:
            continue
        score,_,cut=min(candidates)
        a=mask.copy(); b=mask.copy()
        if axis=='x': a[:,cut:]=False; b[:,:cut]=False
        else: a[cut:,:]=False; b[:cut,:]=False
        require(np.array_equal(a|b,mask) and not np.any(a&b),'split conservation')
        parts=[]
        for part in (a,b):
            y,x=np.nonzero(part); x0,y0,x1,y1=map(int,(x.min(),y.min(),x.max()+1,y.max()+1))
            parts.append(dict(box=[l+x0,t+y0,l+x1,t+y1],area=int(part.sum()),mask_sha256=hashlib.sha256(part[y0:y1,x0:x1].astype(np.uint8).tobytes()).hexdigest()))
        item=dict(parent=row['id'],axis=axis,cut=offset+cut,neck_ratio=score,parts=parts,kind='POSSIBLE_SPLIT',script_status='UNRESOLVED')
        item['id']=digest([POLICY,item]);out.append(item)
    return out


def compounds(rows,pairs,boundary):
    """At most two ranked growth prefixes per anchor; all pair evidence retained."""
    boxes={r['id']:r['box'] for r in rows}; adj=defaultdict(set)
    for pair in pairs:
        a,b=pair['members'];require(a!=b and a in boxes and b in boxes,'invalid pair')
        adj[a].add(b);adj[b].add(a)
    out=[]; seen=set(); attempts=0
    def envelope(members):
        bb=[boxes[k] for k in members]
        return [min(b[0] for b in bb),min(b[1] for b in bb),max(b[2] for b in bb),max(b[3] for b in bb)]
    def rank(a,b):
        l,t,r,d=boxes[a]; L,T,R,D=boxes[b]
        dx,dy=max(l-R,L-r,0),max(t-D,T-d,0)
        return (dx*dx+dy*dy,(l+r-L-R)**2+(t+d-T-D)**2,b)
    for i,anchor in enumerate(sorted(adj)):
        if i%128==0: boundary()
        group={anchor}
        for size in (2,3,4):
            options=[]
            for member in sorted(group):
                for other in sorted(adj[member]-group):
                    attempts+=1
                    if attempts%256==0: boundary()
                    require(attempts<=MAX_EXPANSIONS,'compound expansion budget exceeded')
                    box=envelope(group|{other})
                    if max(box[2]-box[0],box[3]-box[1])<=96:
                        options.append((rank(member,other),other))
            if not options: break
            group.add(min(options)[1])
            members=tuple(sorted(group))
            if size<3 or members in seen: continue
            seen.add(members)
            item=dict(members=list(members),box=envelope(group),kind='POSSIBLE_COMPOUND',script_status='UNRESOLVED')
            item['id']=digest([POLICY,item]);out.append(item)
            require(len(out)<=MAX_ALTERNATIVES,'compound budget exceeded')
    return out


def build(outputs,labels,origin,boundary=lambda:None):
    ox,oy=origin; alternatives={}
    for name in MASKS:
        boundary(); lab=labels[name]; rows=outputs[name]['components']
        require(lab.ndim==2 and lab.dtype.kind in 'iu' and lab.min()>=0 and lab.max()<=len(rows),'invalid labels')
        counts=np.bincount(lab.ravel(),minlength=len(rows)+1)
        require(len({r['id'] for r in rows})==len(rows) and all(counts[i]==r['area'] for i,r in enumerate(rows,1)),'component accounting')
        require(sum(r['area'] for r in rows)==outputs[name]['pixels'],'mask accounting')
        splits=[]
        for i,row in enumerate(rows,1):
            if i%128==0: boundary()
            l,t,r,b=row['box'];require(0<=l-ox<r-ox<=lab.shape[1] and 0<=t-oy<b-oy<=lab.shape[0],'component bounds')
            mask=lab[t-oy:b-oy,l-ox:r-ox]==i
            require(int(mask.sum())==row['area'],'component envelope mismatch')
            splits.extend(split_options(mask,row));require(len(splits)<=MAX_ALTERNATIVES,'split budget exceeded')
        alternatives[name]=dict(splits=splits,compounds=compounds(rows,outputs[name]['pairs'],boundary))
    links={}
    for p,c in zip(MASKS,MASKS[1:]):
        boundary();links[p+'_to_'+c]=lineage(labels[p],labels[c],outputs[p]['components'],outputs[c]['components'])
    return dict(policy=POLICY,compound_strategy='nearest_connected_prefixes_3_4',by_mask=alternatives,lineage=links,scientific_status='UNADJUDICATED',exclusion_authorized=False)

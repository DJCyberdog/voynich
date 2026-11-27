"""Fail-closed reference geometry for RC2-02d; annotations are not predictions."""
import hashlib
import math
import re
import xml.etree.ElementTree as ET
import numpy as np

CLASSES = frozenset(('voynichese','other_handwriting','mixed','illustration','material','blank','unknown'))

def digest(b):
    return hashlib.sha256(b).hexdigest()

def parse_words(raw, expected_sha256, folio):
    if digest(raw) != expected_sha256 or len(raw)>4_000_000 or re.search(br'<!\s*(?:DOCTYPE|ENTITY)',raw,re.I):
        raise ValueError('untrusted XML')
    root=ET.fromstring(raw)
    if root.tag!='folio' or root.get('name')!=folio:
        raise ValueError('wrong folio')
    w,h=int(root.attrib['width']),int(root.attrib['height'])
    if not (0<w<=100000 and 0<h<=100000): raise ValueError('invalid dimensions')
    rows=[]; seen=set(); rejected=[]
    for node in root:
        if node.tag!='word': raise ValueError('unknown element')
        i,x,y,bw,bh=[int(node.attrib[k]) for k in ('index','x','y','width','height')]
        if i<0 or i in seen: raise ValueError('duplicate/invalid ID')
        seen.add(i)
        if not (0<=x<x+bw<=w and 0<=y<y+bh<=h):
            rejected.append(i);continue
        rows.append(dict(id=i,box=[x,y,x+bw,y+bh],kind='voynichese',status='EXTERNAL_POSITIVE'))
    if len(seen)!=int(root.attrib['wordCount']):raise ValueError('count mismatch')
    return dict(folio=folio,size=[w,h],sha256=expected_sha256,rows=rows,rejected=rejected)

def fit_registration(train_src, train_dst, check_src, check_dst, *, max_error=3.):
    """Geometry only; caller must verify provenance of matched anchors separately."""
    a,b,c,d=[np.asarray(x,dtype=float) for x in (train_src,train_dst,check_src,check_dst)]
    if any(x.ndim!=2 or x.shape[1]!=2 or not np.isfinite(x).all() for x in (a,b,c,d)) or a.shape!=b.shape or c.shape!=d.shape or len(a)<4 or len(c)<3 or not np.isfinite(max_error) or not 0<max_error<=3:
        raise ValueError('invalid controls')
    if len(set(map(tuple,a)))!=len(a) or len(set(map(tuple,c)))!=len(c) or set(map(tuple,a))&set(map(tuple,c)):
        raise ValueError('controls not disjoint')
    X=np.c_[a,np.ones(len(a))]; C=np.c_[c,np.ones(len(c))]
    if np.linalg.matrix_rank(X)!=3 or np.linalg.matrix_rank(C)!=3:raise ValueError('degenerate controls')
    M=np.linalg.lstsq(X,b,rcond=None)[0].T
    if np.linalg.det(M[:,:2])<=0:raise ValueError('reflection or singular map')
    errors=np.r_[np.linalg.norm(X@M.T-b,axis=1),np.linalg.norm(C@M.T-d,axis=1)]
    return dict(matrix=M.tolist(),max_error=float(errors.max()),geometry_status='CHECKED' if errors.max()<=max_error else 'REJECTED',train_count=len(a),check_count=len(c),threshold=float(max_error))

def project(box, matrix, target_size):
    x,y,X,Y=box; w,h=target_size; m=np.asarray(matrix,dtype=float)
    if m.shape!=(2,3) or not np.isfinite(m).all() or not x<X or not y<Y:raise ValueError('bad geometry')
    p=np.array([[x,y,1],[X,y,1],[X,Y,1],[x,Y,1]])@m.T
    l,t=np.floor(p.min(0)).astype(int);r,b=np.ceil(p.max(0)).astype(int)
    if not 0<=l<r<=w or not 0<=t<b<=h:return None
    return [int(l),int(t),int(r),int(b)]

def reference_evidence(box, regions, *, registration, provenance_verified=False):
    """Never infer a negative from missing positive annotation, or auto-accept."""
    if not provenance_verified or registration.get('geometry_status')!='CHECKED':
        return dict(status='UNREGISTERED',classes=[],matches=[])
    x,y,X,Y=box
    if not x<X or not y<Y:raise ValueError('invalid target')
    matches=[]; kinds=set()
    for r in regions:
        k=r['kind']; l,t,R,B=r['box']
        if k not in CLASSES or not l<R or not t<B:raise ValueError('invalid region')
        if max(x,l)<min(X,R) and max(y,t)<min(Y,B):
            matches.append(r['id']);kinds.add(k)
    return dict(status='REFERENCE_OVERLAP' if matches else 'UNRESOLVED',classes=sorted(kinds),matches=matches)

"""Experimental native pixel contours and skeleton graphs, no glyph verdict."""
from collections import defaultdict
import numpy as np
from vrs_artifacts import component_labels

POLICY = 'native-grid-vector-v1'
DIRS = ((1,0),(0,1),(-1,0),(0,-1))


def mask_array(mask):
    a = np.asarray(mask)
    if a.ndim != 2 or a.dtype != bool or not a.size:
        raise ValueError('expected nonempty boolean mask')
    return a


def contours(mask):
    """Oriented pixel-edge loops; clockwise outer boundaries in y-down coordinates.

    At diagonal contacts take the rightmost available turn, preserving the
    separate pixel-edge loops. Coordinates are local native pixel corners.
    """
    a = mask_array(mask); p = np.pad(a,1); h,w = a.shape
    sides = (a & ~p[:-2,1:-1], a & ~p[1:-1,2:],
             a & ~p[2:,1:-1], a & ~p[1:-1,:-2])
    offsets = ((0,0),(1,0),(1,1),(0,1)); adj = defaultdict(set)
    for d, side in enumerate(sides):
        dy,dx = np.nonzero(side); ox,oy = offsets[d]
        for y,x in zip(dy,dx):
            adj[(int(x)+ox,int(y)+oy)].add(d)
    loops=[]
    for start in sorted(adj):
        while adj[start]:
            cur=start; d=min(adj[cur]); vertices=[start]
            while True:
                adj[cur].remove(d); dx,dy=DIRS[d]; cur=(cur[0]+dx,cur[1]+dy)
                if cur==start:
                    break
                candidates=adj[cur]
                nd=next((k for k in ((d+1)%4,d,(d-1)%4,(d+2)%4) if k in candidates),None)
                if nd is None: raise RuntimeError('open boundary')
                if nd!=d: vertices.append(cur)
                d=nd
            vertices.append(start); loops.append(vertices)
    if any(adj.values()): raise RuntimeError('unconsumed boundary')
    return loops


def rasterize(loops, shape):
    """Exact even-odd fill at pixel centers, without renderer antialiasing."""
    h,w=shape; crossings=np.zeros((h,w+1),bool)
    for loop in loops:
        if len(loop)<4 or loop[0]!=loop[-1]: raise ValueError('open path')
        for (x,y),(X,Y) in zip(loop,loop[1:]):
            if not (0<=x<=w and 0<=X<=w and 0<=y<=h and 0<=Y<=h) or (x!=X and y!=Y) or (x,y)==(X,Y):
                raise ValueError('invalid grid edge')
            if x==X: crossings[min(y,Y):max(y,Y),x]^=True
    parity=np.logical_xor.accumulate(crossings,axis=1)
    if parity[:,-1].any(): raise ValueError('unbalanced path crossings')
    return parity[:,:w]


def euler8(mask):
    """Digital Euler characteristic for 8-connected foreground / 4-background."""
    a=np.pad(mask_array(mask),1).astype(np.int8)
    u,v,w,z=a[:-1,:-1],a[:-1,1:],a[1:,:-1],a[1:,1:]
    s=u+v+w+z; diag=(s==2)&((u&z)|(v&w)).astype(bool)
    return int((np.count_nonzero(s==1)-np.count_nonzero(s==3)-2*np.count_nonzero(diag))//4)


def skeleton(mask):
    """Zhang-Suen thinning; retain original components if topology check fails.

    No inferred pen order or Euclidean medial axis. Fallbacks are explicit.
    """
    original=mask_array(mask); a=original.copy()
    while True:
        changed=False
        for phase in (0,1):
            p=np.pad(a,1); n=[p[:-2,1:-1],p[:-2,2:],p[1:-1,2:],p[2:,2:],p[2:,1:-1],p[2:,:-2],p[1:-1,:-2],p[:-2,:-2]]
            count=np.sum(n,axis=0,dtype=np.uint8)
            transitions=np.sum([~n[i]&n[(i+1)%8] for i in range(8)],axis=0,dtype=np.uint8)
            if phase==0: guard=~(n[0]&n[2]&n[4])&~(n[2]&n[4]&n[6])
            else: guard=~(n[0]&n[2]&n[6])&~(n[0]&n[4]&n[6])
            delete=a&(count>=2)&(count<=6)&(transitions==1)&guard
            changed|=bool(delete.any()); a[delete]=False
        if not changed: break
    labels,n=component_labels(original); ys,xs=np.nonzero(labels); ids=labels[ys,xs]
    h,w=original.shape; x0=np.full(n+1,w); y0=np.full(n+1,h); x1=np.zeros(n+1,int); y1=np.zeros(n+1,int)
    np.minimum.at(x0,ids,xs); np.minimum.at(y0,ids,ys); np.maximum.at(x1,ids,xs+1); np.maximum.at(y1,ids,ys+1)
    fallback=[]
    for i in range(1,n+1):
        box=np.s_[y0[i]:y1[i],x0[i]:x1[i]]; src=labels[box]==i; dst=a[box]&src
        if not dst.any() or component_labels(dst)[1]!=1 or euler8(src)!=euler8(dst):
            a[box]|=src; fallback.append(i)
    return a,fallback


def graph(mask):
    """Compressed undirected pixel adjacency; suppress diagonal shortcuts.

    All skeleton pixels are represented, including isolated nodes and cycles.
    Graph cycles are not equivalent to manuscript loops or digital holes.
    """
    a=mask_array(mask); points={(int(x),int(y)) for y,x in zip(*np.nonzero(a))}
    adj={p:set() for p in points}
    for x,y in points:
        for dx,dy in ((1,0),(0,1),(1,1),(-1,1)):
            q=(x+dx,y+dy)
            if q in points and not (dx and dy and ((x+dx,y) in points or (x,y+dy) in points)):
                adj[x,y].add(q); adj[q].add((x,y))
    nodes={p for p in points if len(adj[p])!=2}; used=set(); paths=[]
    def edge(p,q): return tuple(sorted((p,q)))
    def trace(p,q):
        path=[p,q]; used.add(edge(p,q))
        while q not in nodes:
            nxt=next(iter(adj[q]-{p})); e=edge(q,nxt)
            if e in used: raise RuntimeError('repeated graph edge')
            used.add(e); path.append(nxt); p,q=q,nxt
        return path
    for p in sorted(nodes):
        for q in sorted(adj[p]):
            if edge(p,q) not in used: paths.append(trace(p,q))
    for p in sorted(points):
        for q in sorted(adj[p]):
            if edge(p,q) not in used:
                nodes.add(p); paths.append(trace(p,q))
    return dict(nodes=[dict(point=p,degree=len(adj[p])) for p in sorted(nodes)],paths=paths,edge_count=len(used),pixel_count=len(points))


def svg(loops, shape, g=None):
    """Local native-pixel SVG; contours exact, optional skeleton overlay."""
    h,w=shape
    d=' '.join('M'+' L'.join(f'{x} {y}' for x,y in loop[:-1])+' Z' for loop in loops)
    out=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}"><path d="{d}" fill="black" fill-rule="evenodd"/>'
    if g is not None:
        for path in g['paths']:
            d='M'+' L'.join(f'{x+.5} {y+.5}' for x,y in path)
            out+=f'<path d="{d}" fill="none" stroke="#ef4444" stroke-width="0.35"/>'
        for node in g['nodes']:
            x,y=node['point']; out+=f'<circle cx="{x+.5}" cy="{y+.5}" r="0.45" fill="#2563eb"/>'
    return out+'</svg>'

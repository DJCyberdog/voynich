"""RC2-02d: non-destructive component evidence on native binary hypotheses."""
from collections import defaultdict
import numpy as np
from PIL import Image, ImageFilter

POLICY = 'native-component-evidence-v1'


def component_labels(mask):
    """Deterministic 8-connected run labeling, row-major component IDs."""
    a = np.asarray(mask)
    if a.ndim != 2 or a.dtype != bool or not a.size:
        raise ValueError('expected nonempty boolean mask')
    parent = [0]
    runs = []
    previous = []
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for y, row in enumerate(a):
        ends = np.flatnonzero(np.diff(np.r_[False, row, False]))
        current = []
        j = 0
        for l, r in zip(ends[::2], ends[1::2]):
            l, r = int(l), int(r)
            i = len(parent); parent.append(i)
            while j < len(previous) and previous[j][1] < l:
                j += 1
            k = j
            while k < len(previous) and previous[k][0] <= r:
                u, v = root(i), root(previous[k][2])
                parent[max(u, v)] = min(u, v)
                k += 1
            current.append((l, r, i)); runs.append((y, l, r, i))
        previous = current
    labels = np.zeros(a.shape, np.int32)
    ids = {}
    for y, l, r, i in runs:
        k = root(i)
        if k not in ids:
            ids[k] = len(ids)+1
        labels[y, l:r] = ids[k]
    return labels, len(ids)


def analyze(rgb, votes, n, *, origin, page_size):
    """Return component IDs and evidence; never classify script or erase pixels.

    Coordinates are native image pixels, half-open boxes. Crop boundaries are
    distinct from image boundaries, which are NOT physical leaf boundaries.
    """
    if not isinstance(rgb, Image.Image) or rgb.mode != 'RGB':
        raise ValueError('expected RGB image')
    v = np.asarray(votes)
    w,h = rgb.size
    if type(n) is not int or not 1 <= n <= 65535 or v.shape != (h,w) or v.dtype.kind not in 'ui' or np.any(v<0) or np.any(v>n):
        raise ValueError('invalid votes')
    ox,oy = origin; pw,ph = page_size
    if any(type(x) is not int for x in (ox,oy,pw,ph)) or not (0<=ox<ox+w<=pw and 0<=oy<oy+h<=ph):
        raise ValueError('invalid native extent')
    labels,count = component_labels(v>0)
    gray = rgb.convert('L')
    residual = np.asarray(gray.filter(ImageFilter.GaussianBlur(16)),dtype=np.int16)-np.asarray(gray,dtype=np.int16)
    ys,xs = np.nonzero(labels); ids = labels[ys,xs]
    area = np.bincount(ids,minlength=count+1)
    sums = np.bincount(ids,weights=v[ys,xs],minlength=count+1)
    contrast = np.bincount(ids,weights=residual[ys,xs],minlength=count+1)
    x0=np.full(count+1,w); y0=np.full(count+1,h); x1=np.zeros(count+1,int); y1=np.zeros(count+1,int)
    np.minimum.at(x0,ids,xs); np.minimum.at(y0,ids,ys); np.maximum.at(x1,ids,xs+1); np.maximum.at(y1,ids,ys+1)
    rows=[]; grid=defaultdict(list)
    for i in range(1,count+1):
        l,t,r,b = map(int,(x0[i],y0[i],x1[i],y1[i])); a=int(area[i]); bw,bh=r-l,b-t
        flags=[]
        if a<=4: flags.append('tiny')
        if max(bw,bh)>=24 and max(bw,bh)>=8*min(bw,bh): flags.append('elongated')
        if min(l+ox,t+oy,pw-r-ox,ph-b-oy)<=8: flags.append('near_image_edge')
        if min(l,t,w-r,h-b)==0: flags.append('touches_window_edge')
        if a>=64 and contrast[i]/a<8: flags.append('broad_low_contrast')
        if 2*sums[i]<n*a: flags.append('low_method_agreement')
        row=dict(id=i,box=[l+ox,t+oy,r+ox,b+oy],area=a,mean_votes=float(sums[i]/a),mean_residual=float(contrast[i]/a),flags=flags,script_status='UNRESOLVED')
        rows.append(row)
        if 6<=a and 3<=bh<=48 and bw<=64 and 'elongated' not in flags:
            grid[((l+r)//64,(t+b)//64)].append(row)
    for row in rows:
        l,t,r,b=row['box']; l-=ox;r-=ox;t-=oy;b-=oy
        gx,gy=(l+r)//64,(t+b)//64
        peers=0
        for yy in range(gy-1,gy+2):
            for xx in range(gx-2,gx+3):
                for p in grid[xx,yy]:
                    if p['id']==row['id']: continue
                    L,T,R,B=p['box'];L-=ox;R-=ox;T-=oy;B-=oy
                    if abs((t+b)-(T+B))<=max(6,b-t,B-T) and max(L-r,l-R,0)<=48:
                        peers+=1
        row['aligned_neighbors']=peers
        if peers>=2: row['flags'].append('line_context_hint')
        if not peers: row['flags'].append('isolated_in_window')
    return labels,rows

"""Experimental RC2-02d/f geometry and source-bound vector alternatives.
Optional SciPy/scikit-image/CairoSVG only for experimental qualification.
"""
import hashlib
import json
import numpy as np
from PIL import Image, ImageFilter
import vrs_vectors as vec
from vrs_artifacts import component_labels

POLICY = 'rc2-native-geometry-v1'


def leaf_hypotheses(rgb):
    """Propose bright material silhouettes, not physical folio identities."""
    if rgb.mode != 'RGB':
        raise ValueError('expected native RGB')
    from scipy import ndimage as ndi
    g = np.asarray(rgb.convert('L').filter(ImageFilter.MedianFilter(5)))
    result = {}
    for threshold in (30, 50, 70):
        labels, n = ndi.label(g >= threshold, structure=np.ones((3, 3)))
        sizes = np.bincount(labels.ravel(), minlength=n+1); sizes[0] = 0
        mask = ndi.binary_fill_holes(labels == sizes.argmax()) if n else np.zeros(g.shape, bool)
        result[str(threshold)] = mask
    stack = np.stack(list(result.values()))
    return result, stack.all(0), stack.any(0) & ~stack.all(0)


def script_zones(rows):
    """Conservative line-context proposals, not script/annotation classifications."""
    eligible = [r for r in rows if 'line_context_hint' in r['flags'] and 'elongated' not in r['flags'] and 'tiny' not in r['flags']]
    zones = []
    for r in sorted(eligible, key=lambda r:(sum(r['box'][1::2]),r['box'][0],r['id'])):
        x,y,X,Y = r['box']; h = Y-y
        options = [z for z in zones if abs((y+Y)/2-z['cy']) <= max(3,h/2,z['height']/2) and max(z['box'][0]-X,x-z['box'][2],0)<=48]
        if not options:
            zones.append(dict(box=[x,y,X,Y],cy=(y+Y)/2,height=h,ids=[r['id']],script_status='UNRESOLVED'))
            continue
        z=min(options,key=lambda z:abs((y+Y)/2-z['cy'])); l,t,R,B=z['box']; k=len(z['ids'])
        z['cy']=(z['cy']*k+(y+Y)/2)/(k+1); z['height']=(z['height']*k+h)/(k+1)
        z['box']=[min(l,x),min(t,y),max(R,X),max(B,Y)]; z['ids'].append(r['id'])
    return [z for z in zones if len(z['ids'])>=3]


def rounded_path(loops, radius=.22):
    """Quadratic Bezier corner alternative; original integer contours retained."""
    if not 0 < radius <= .49: raise ValueError('invalid rounding radius')
    def point(p,q):
        x,y=p; X,Y=q; length=abs(X-x)+abs(Y-y)
        r=min(radius,length/2)
        return x+(X-x)*r/length,y+(Y-y)*r/length
    def fmt(p): return f'{p[0]:.6f} {p[1]:.6f}'
    paths=[]
    for loop in loops:
        a=loop[:-1]; start=point(a[0],a[-1]); parts=['M'+fmt(start)]
        for i,p in enumerate(a):
            before=point(p,a[i-1]); after=point(p,a[(i+1)%len(a)])
            if i: parts.append('L'+fmt(before))
            parts.append('Q'+fmt(p)+' '+fmt(after))
        parts.append('Z'); paths.append(' '.join(parts))
    return ' '.join(paths)


def curve_svg(loops, shape, radius=.22):
    h,w=shape
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}"><path fill="black" fill-rule="evenodd" d="{rounded_path(loops,radius)}"/></svg>'


def digest(data): return hashlib.sha256(data).hexdigest()


def vector_record(mask, *, source_sha256, page, page_rgb_sha256, origin, page_size, px_to_pt, method):
    """Source-bound exact contours plus derived curve, with explicit affine."""
    a=vec.mask_array(mask); h,w=a.shape; ox,oy=origin; pw,ph=page_size
    for s in (source_sha256,page_rgb_sha256):
        if not isinstance(s,str) or len(s)!=64 or any(c not in '0123456789abcdef' for c in s): raise ValueError('invalid SHA-256')
    if type(page) is not int or page<1 or not (0<=ox<ox+w<=pw and 0<=oy<oy+h<=ph) or len(px_to_pt)!=4 or not all(np.isfinite(px_to_pt)) or min(px_to_pt[:2])<=0 or not method:
        raise ValueError('invalid provenance')
    loops=vec.contours(a); exact=vec.svg(loops,a.shape); curved=curve_svg(loops,a.shape)
    record=dict(policy=POLICY,source_sha256=source_sha256,page=page,page_rgb_sha256=page_rgb_sha256,origin=list(origin),page_size=list(page_size),shape=[h,w],px_to_pt=list(px_to_pt),method=method,mask_sha256=digest(a.astype(np.uint8).tobytes()),exact_svg_sha256=digest(exact.encode()),curve_svg_sha256=digest(curved.encode()))
    record['id']=digest(json.dumps(record,sort_keys=True,separators=(',',':')).encode())
    return record,exact,curved


def medial(mask):
    """Independent medial-axis candidate and EDT diameter proxy in native px."""
    from scipy.ndimage import distance_transform_edt
    from skimage.morphology import medial_axis
    a=vec.mask_array(mask); p=np.pad(a,1); candidate=medial_axis(p,rng=0)[1:-1,1:-1]
    dist=distance_transform_edt(p)[1:-1,1:-1]
    labels,n=component_labels(a); fallback=[]
    # Group foreground coordinates once instead of scanning full image per ID.
    ys,xs=np.nonzero(a); ids=labels[ys,xs]; order=np.argsort(ids,kind='stable'); ys,xs,ids=ys[order],xs[order],ids[order]
    cuts=np.searchsorted(ids,np.arange(1,n+2))
    for i in range(n):
        yy=ys[cuts[i]:cuts[i+1]]; xx=xs[cuts[i]:cuts[i+1]]
        l,t,R,B=xx.min(),yy.min(),xx.max()+1,yy.max()+1; box=np.s_[t:B,l:R]
        src=labels[box]==i+1; dst=candidate[box]&src
        if not dst.any() or component_labels(dst)[1]!=1 or vec.euler8(src)!=vec.euler8(dst):
            candidate[box]|=src; fallback.append(i+1)
    return candidate,2*dist,fallback


def simplified_loops(loops, tolerance=.75):
    """Closed RDP alternative; not authoritative until raster/topology audit."""
    if not np.isfinite(tolerance) or tolerance<0: raise ValueError('invalid tolerance')
    def simplify(points):
        if len(points)<=2: return points
        a=np.asarray(points,float); delta=a[-1]-a[0]; norm=float(delta@delta)
        v=a-a[0]; t=np.clip(v@delta/norm,0,1) if norm else np.zeros(len(a))
        distances=np.sum((v-t[:,None]*delta)**2,axis=1); k=int(np.argmax(distances))
        if distances[k]<=tolerance*tolerance: return [points[0],points[-1]]
        return simplify(points[:k+1])[:-1]+simplify(points[k:])
    result=[]
    for loop in loops:
        a=np.asarray(loop[:-1]); k=int(np.argmax(np.sum((a-a[0])**2,axis=1)))
        s=simplify(loop[:k+1])[:-1]+simplify(loop[k:]); result.append(s if len(s)>=4 else loop)
    return result

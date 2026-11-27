"""RC2-02d portable, non-destructive material and script-zone proposals."""
import hashlib
import json
import numpy as np
from PIL import Image

POLICY = 'native-region-evidence-v1'
THRESHOLDS = (30, 50, 70)


def material_hypotheses(rgb):
    """Axis-aligned material envelope hypotheses, not certified leaf boundaries.

    Row/column spans deliberately bridge internal dark marks. A disconnected
    leaf, dark margin or binding can be misrepresented. Never use as a mask
    for discarding ink. Return aligned alternatives and agreement evidence.
    """
    if not isinstance(rgb, Image.Image) or rgb.mode != 'RGB' or not min(rgb.size):
        raise ValueError('expected nonempty RGB')
    gray = np.asarray(rgb.convert('L'))
    def spans(a):
        valid = a.any(1)
        l = a.argmax(1)
        r = a.shape[1] - a[:, ::-1].argmax(1)
        x = np.arange(a.shape[1])[None, :]
        return valid[:, None] & (x >= l[:, None]) & (x < r[:, None])
    def envelope(t):
        bright = gray >= t
        p = np.pad(bright, 1)
        support = sum(p[y:y+bright.shape[0], x:x+bright.shape[1]].astype(np.uint8) for y in range(3) for x in range(3)) >= 5
        return spans(support) & spans(support.T).T
    masks = {str(t): envelope(t) for t in THRESHOLDS}
    stack = np.stack(list(masks.values()))
    union = stack.any(0); core = stack.all(0)
    return dict(masks=masks, core=core, uncertain=union & ~core, outside=~union)


def script_zones(rows):
    """Group component evidence; every zone remains UNRESOLVED as to script."""
    seen = set(); eligible = []
    for row in rows:
        i = row['id']; x,y,X,Y = row['box']
        if type(i) is not int or i < 1 or i in seen or not (0 <= x < X and 0 <= y < Y):
            raise ValueError('invalid component identity or box')
        seen.add(i)
        if 'line_context_hint' in row['flags'] and not {'elongated','tiny'}.intersection(row['flags']):
            eligible.append(row)
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


def region_record(rgb, votes, n, rows, *, source_sha256, page, origin, image_size):
    """Bind evidence to immutable image/window/votes. Never classify or erase.

    Component boxes use native page coordinates, not crop-local coordinates.
    Material envelopes are local and should be computed on full images for
    page-level use. No external reference is needed to generate proposals.
    """
    w,h = rgb.size; ox,oy = origin; pw,ph = image_size
    v = np.asarray(votes)
    if (not isinstance(source_sha256,str) or len(source_sha256)!=64 or any(c not in '0123456789abcdef' for c in source_sha256)
        or type(page) is not int or page<1 or any(type(i) is not int for i in (ox,oy,pw,ph))
        or not (0<=ox<ox+w<=pw and 0<=oy<oy+h<=ph)
        or type(n) is not int or not 1<=n<=65535 or v.shape!=(h,w) or v.dtype.kind not in 'ui' or np.any(v<0) or np.any(v>n)):
        raise ValueError('invalid source, extent or votes')
    rows=list(rows); zones=script_zones(rows)
    for row in rows:
        x,y,X,Y=row['box']
        if not (ox<=x<X<=ox+w and oy<=y<Y<=oy+h): raise ValueError('component outside window')
    material=material_hypotheses(rgb)
    def digest(b): return hashlib.sha256(b).hexdigest()
    record=dict(policy=POLICY,source_sha256=source_sha256,page=page,origin=list(origin),image_size=list(image_size),shape=[h,w],rgb_sha256=digest(rgb.tobytes()),votes_sha256=digest(v.astype('<u2').tobytes()),methods=n,component_ids=sorted(r['id'] for r in rows),components_sha256=digest(json.dumps(sorted(rows,key=lambda r:r['id']),sort_keys=True,separators=(',',':'),allow_nan=False).encode()),zones=zones,material_counts={k:int(material[k].sum()) for k in ('core','uncertain','outside')},material_sha256={k:digest(material[k].astype(np.uint8).tobytes()) for k in ('core','uncertain','outside')},script_status='UNRESOLVED',exclusion_authorized=False)
    record['id']=digest(json.dumps(record,sort_keys=True,separators=(',',':')).encode())
    return record,material

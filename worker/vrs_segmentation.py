"""RC2-02: conservative page-coordinate deduplication of unreviewed ink hypotheses."""
import hashlib
from collections import defaultdict

POLICY='exact-page-rgb-and-line-alternatives-v1'
MAX_RAW=100000  # per-page processing guard; fail closed, never truncate


def require(ok,message):
    if not ok:raise ValueError(message)


def rect(b):
    require(type(b) is list and len(b)==4 and all(type(x) is int and x>=0 for x in b)
            and b[0]<b[2] and b[1]<b[3],'Invalid segmentation rectangle')
    return tuple(b)


def runs(active):
    start=None
    for i,on in enumerate([*active,False]):
        if on and start is None:start=i
        if not on and start is not None:
            yield start,i;start=None


def projections(ink,y0,y1):
    import numpy as np
    band=ink[y0:y1]
    for x0,x1 in runs(band.any(axis=0)):
        ys=np.flatnonzero(band[:,x0:x1].any(axis=1))
        yield (x0,y0+int(ys[0]),x1,y0+int(ys[-1])+1)


def hypotheses(image):
    """Retain every legacy box; add alternatives only at clear blank row gaps.

    A row band is not a proven text line. Detached strokes, illustrations and
    compounds remain unresolved. Method bits: 1 legacy, 2 separated bands.
    """
    import numpy as np
    ink=np.asarray(image.convert('L'))<160
    result={b:1 for b in projections(ink,0,ink.shape[0])}
    bands=list(runs(ink.any(axis=1)))
    # Merge tiny vertical gaps, not individual stroke components.
    merged=[]
    for a,b in bands:
        if merged and a-merged[-1][1]<3:merged[-1]=(merged[-1][0],b)
        else:merged.append((a,b))
    if len(merged)>1:
        for a,b in merged:
            for box in projections(ink,a,b):result[box]=result.get(box,0)|2
    return sorted(result.items())


def absolute(px,b):
    return (px[0]+b[0],px[1]+b[1],px[0]+b[2],px[1]+b[3])


def rank(px,b,rid):
    # Prefer contextual room around exactly equivalent pixels; deterministic tie.
    margin=min(b[0],b[1],px[2]-px[0]-b[2],px[3]-px[1]-b[3])
    return (-margin,-(px[2]-px[0])*(px[3]-px[1]),rid,b)


def assemble(manifest,raw):
    """Pure deterministic projection of complete raw hypotheses into representatives."""
    regions=manifest['regions']
    dimensions=manifest['page_dimensions']
    require(type(dimensions) is dict and len(dimensions)==1,'Segmentation requires one source page')
    page,width_height=next(iter(dimensions.items()))
    require(type(page) is str and page.isdigit() and type(width_height) is list and len(width_height)==2
            and all(type(v) is int and v>0 for v in width_height),'Invalid page dimensions')
    ids=[r['id'] for r in regions]
    require(type(raw) is list and len(raw)==len(regions) and len(set(ids))==len(ids),
            'Segmentation lineage region coverage mismatch')
    groups=defaultdict(list);total=legacy=band=edge=0;coords=defaultdict(set)
    for region,record in zip(regions,raw):
        rid=region['id'];px=rect(region['pixel_box'])
        require(type(region['page']) is int and str(region['page'])==page
                and px[2]<=width_height[0] and px[3]<=width_height[1],'Region outside source page')
        require(type(record) is dict and set(record)=={'id','hypotheses'}
                and record['id']==rid and type(record['hypotheses']) is list,'Invalid raw region lineage')
        seen=set()
        for entry in record['hypotheses']:
            require(type(entry) is list and len(entry)==3,'Invalid raw hypothesis')
            b=rect(entry[0]);method,sha=entry[1:]
            require(b[2]<=px[2]-px[0] and b[3]<=px[3]-px[1] and b not in seen
                    and type(method) is int and method in (1,2,3)
                    and type(sha) is str and len(sha)==64 and all(c in '0123456789abcdef' for c in sha),
                    'Invalid raw hypothesis geometry or identity')
            seen.add(b);total+=1;legacy+=bool(method&1);band+=bool(method&2)
            edge+=min(b[0],b[1],px[2]-px[0]-b[2],px[3]-px[1]-b[3])==0
            require(total<=MAX_RAW,'Segmentation raw hypothesis budget exceeded; no complete page')
            ab=absolute(px,b);coords[ab].add(sha)
            groups[(ab,sha)].append((rank(px,b,rid),rid,b))
    retained=defaultdict(list);aliases=[]
    for key,items in sorted(groups.items()):
        _,rid,b=min(items)
        retained[rid].append(list(b))
        for _,other,ob in sorted(items):
            if (other,ob)!=(rid,b):aliases.append([other,list(ob),rid,list(b)])
    proposals=[dict(id=rid,status='unreviewed',boxes=sorted(retained[rid])) for rid in ids]
    stats=dict(raw=total,legacy=legacy,band=band,retained=len(groups),
               exact_duplicates=total-len(groups),edge_touching_raw=edge,pixel_conflict_coordinates=sum(len(s)>1 for s in coords.values()))
    return proposals,dict(policy=POLICY,raw=raw,aliases=aliases,counts=stats)


def generate(manifest,open_crop,boundary=lambda:None):
    """Read one crop at a time, preserve source-relative boxes and exact RGB hashes."""
    raw=[];total=0
    for region in manifest['regions']:
        boundary()
        px=rect(region['pixel_box']);items=[]
        with open_crop(region) as original:
            image=original.convert('RGB')
            require(image.size==(px[2]-px[0],px[3]-px[1]),'Crop dimensions mismatch')
            for b,method in hypotheses(image):
                total+=1
                require(total<=MAX_RAW,'Segmentation raw hypothesis budget exceeded; no complete page')
                digest=hashlib.sha256(image.crop(b).tobytes()).hexdigest()
                items.append([list(b),method,digest])
        raw.append(dict(id=region['id'],hypotheses=items))
    return assemble(manifest,raw)


def validate(manifest,value,*,required=False):
    """Replay geometry/alias accounting. Actual pixels were hashed at generation.

    Existing immutable legacy artifacts remain readable, not resumable as RC2.
    The page receipt binds this lineage and the source crop hashes.
    """
    if 'dedup' not in value:
        require(not required,'Missing RC2 segmentation lineage')
        return
    d=value['dedup']
    require(type(d) is dict and d.get('policy')==POLICY,'Unknown segmentation policy')
    expected,details=assemble(manifest,d['raw'])
    require(value['regions']==expected and d==details,'Segmentation lineage or denominator mismatch')

import json, hashlib, math, collections, time, sys
from pathlib import Path
from io import BytesIO
import fitz
import numpy as np
from PIL import Image,ImageFilter
from scipy.ndimage import label
import vrs_artifacts as a
import vrs_vectors as vec
from skimage.measure import euler_number

def stats(a,window):
    p=window//2; x=np.pad(a.astype(np.float64),p,mode='edge')
    def mean(y):
        s=np.pad(y.cumsum(0).cumsum(1),((1,0),(1,0)))
        return (s[window:,window:]-s[:-window,window:]-s[window:,:-window]+s[:-window,:-window])/window**2
    m=mean(x);return m,np.sqrt(np.maximum(0,mean(x*x)-m*m))
def adaptive(a,method):
    m,sd=stats(a,31)
    if method=='sauvola':t=m*(1+.25*(sd/128-1))
    else:
        r=sd.max()
        if r<=1e-9:return np.zeros(a.shape,bool)
        t=m+.25*(sd/r-1)*(m-float(a.min()))
    return a<t
def normalize(a):
    bg=np.asarray(Image.fromarray(a).filter(ImageFilter.GaussianBlur(16)),dtype=float)
    return np.clip(np.rint(255*a.astype(float)/np.maximum(bg,1)),0,255).astype(np.uint8)
def votes(im):
    g=np.asarray(im.convert('L')); n=normalize(g)
    return np.sum([adaptive(g,'sauvola'),adaptive(g,'wolf'),adaptive(n,'sauvola'),adaptive(n,'wolf'),adaptive(normalize(np.asarray(im.getchannel('R'))),'sauvola'),adaptive(normalize(np.asarray(im.getchannel('B'))),'sauvola')],axis=0,dtype=np.uint16)
pdf,review=map(Path,sys.argv[1:3]); r=json.loads(review.read_text()); m=r['manifest']
assert hashlib.file_digest(pdf.open('rb'),'sha256').hexdigest()==r['source_sha256']=='d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c'
assert hashlib.sha256(json.dumps({k:v for k,v in m.items() if k!='dataset_sha256'},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()==r['dataset_sha256']==m['dataset_sha256']
assert len(m['items'])==len(r['answers'])==200 and {i['id'] for i in m['items']}==set(r['answers'])
groups=collections.defaultdict(list)
for i in m['items']:
    if not i['stratum'].startswith('wrapper'):groups[i['page']].append(i)
res=collections.defaultdict(collections.Counter); start=time.perf_counter()
def check(mask,counts):
    loops=vec.contours(mask); assert np.array_equal(vec.rasterize(loops,mask.shape),mask)
    sk,fallback=vec.skeleton(mask); assert not (sk&~mask).any()
    n=label(mask,structure=np.ones((3,3)))[1]; ns=label(sk,structure=np.ones((3,3)))[1]; assert n==ns
    e=int(euler_number(mask,connectivity=2)); assert e==euler_number(sk,connectivity=2)==vec.euler8(mask)
    g=vec.graph(sk); points={tuple(x['point']) for x in g['nodes']}|{p for path in g['paths'] for p in path}; assert points=={(int(x),int(y)) for y,x in zip(*np.nonzero(sk))}
    edges=[tuple(sorted((p,q))) for path in g['paths'] for p,q in zip(path,path[1:])]; assert len(edges)==len(set(edges))==g['edge_count']
    expected=set()
    for x,y in points:
        for dx,dy in ((1,0),(0,1),(1,1),(-1,1)):
            q=(x+dx,y+dy)
            if q in points and not (dx and dy and ((x+dx,y) in points or (x,y+dy) in points)): expected.add(tuple(sorted(((x,y),q))))
    assert set(edges)==expected
    counts.update(dict(masks=1,foreground_pixels=int(mask.sum()),skeleton_pixels=int(sk.sum()),components=n,holes=n-e,contour_paths=len(loops),contour_vertices=sum(len(p)-1 for p in loops),fallback_components=len(fallback),graph_nodes=len(g['nodes']),graph_paths=len(g['paths']),graph_edges=g['edge_count']))
    return loops,sk,g
with fitz.open(pdf) as doc:
 for pn,ii in sorted(groups.items()):
    q=[x for x in doc[pn-1].get_text('dict')['blocks'] if x['type']==1][0]; im=Image.open(BytesIO(q['image'])); w,h=im.size; x,y,X,Y=q['bbox']; sx=(X-x)/w;sy=(Y-y)/h
    for i in ii:
        l,t,R,B=i['box'];l,t,R,B=max(0,math.floor((l*.36-x)/sx)),max(0,math.floor((t*.36-y)/sy)),min(w,math.ceil((R*.36-x)/sx)),min(h,math.ceil((B*.36-y)/sy)); assert l<R and t<B
        ox,oy=max(0,l-64),max(0,t-64); crop=im.crop((ox,oy,min(w,R+64),min(h,B+64))); v=votes(crop)
        for name,mask in [('union',v>0),('majority',v>3),('intersection',v==6)]:
            check(mask,res[name])
        if i['id']=='VRS-RC2-012':
            a0,b0=max(0,l-ox-4),max(0,t-oy-4); a1,b1=min(crop.width,R-ox+4),min(crop.height,B-oy+4)
            mask=(v>3)[b0:b1,a0:a1]; loops=vec.contours(mask); sk,_=vec.skeleton(mask)
            Path('example.svg').write_text(vec.svg(loops,mask.shape,vec.graph(sk)))
    if pn%20==0:print('page',pn,flush=True)
out={'pages':len(groups),'cases':sum(map(len,groups.values())),'results':res,'full_majority':[],'elapsed':round(time.perf_counter()-start,2)}
Path('audit-vector-result.json').write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2),flush=True)
full=[]
with fitz.open(pdf) as doc:
 for pn in map(int,sys.argv[3:]):
    q=[x for x in doc[pn-1].get_text('dict')['blocks'] if x['type']==1][0]; im=Image.open(BytesIO(q['image'])); v=votes(im); c=collections.Counter(); check(v>3,c); full.append(dict(page=pn,**c)); print('full page',pn,flush=True)
out={'pages':len(groups),'cases':sum(map(len,groups.values())),'results':res,'full_majority':full,'elapsed':round(time.perf_counter()-start,2)}
Path('audit-vector-result.json').write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

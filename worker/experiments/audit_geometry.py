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
    return np.sum([adaptive(g,"sauvola"),adaptive(g,"wolf"),adaptive(n,"sauvola"),adaptive(n,"wolf"),adaptive(normalize(np.asarray(im.getchannel("R"))),"sauvola"),adaptive(normalize(np.asarray(im.getchannel("B"))),"sauvola")],axis=0,dtype=np.uint16)
import vrs_geometry as geo
import cairosvg
pdf,review=map(Path,sys.argv[1:3]); mode=sys.argv[3]; r=json.loads(review.read_text()); m=r['manifest']
assert hashlib.file_digest(pdf.open('rb'),'sha256').hexdigest()==r['source_sha256']=='d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c'
assert hashlib.sha256(json.dumps({k:v for k,v in m.items() if k!='dataset_sha256'},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()==r['dataset_sha256']==m['dataset_sha256']
assert len(m['items'])==len(r['answers'])==200 and {i['id'] for i in m['items']}==set(r['answers'])
groups=collections.defaultdict(list)
for i in m['items']:
    if not i['stratum'].startswith('wrapper'):groups[i['page']].append(i)
def render(svg):
    return np.asarray(Image.open(BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('RGBA'))[:,:,3]>=128

def verify(mask,out,external=False):
    tick=time.perf_counter();loops=vec.contours(mask);exact=vec.svg(loops,mask.shape);out['contour_seconds']+=time.perf_counter()-tick
    n=label(mask,structure=np.ones((3,3)))[1];e=euler_number(mask,connectivity=2)
    assert np.array_equal(vec.rasterize(loops,mask.shape),mask)
    if external:
        reduced=geo.simplified_loops(loops)
        for name,ls,svg in [('exact',loops,exact),('rounded',loops,geo.curve_svg(loops,mask.shape)),('reduced',reduced,geo.curve_svg(reduced,mask.shape))]:
            raster=render(svg);delta=int(np.count_nonzero(raster^mask));out[name+'_different_pixels']+=delta;out[name+'_exact_masks']+=not delta;out[name+'_vertices']+=sum(len(p)-1 for p in ls)
            out[name+'_topology_equal']+=(label(raster,structure=np.ones((3,3)))[1]==n and euler_number(raster,connectivity=2)==e)
            if name=='exact':assert not delta
        out['external_masks']+=1
    tick=time.perf_counter();medial,width,fallback=geo.medial(mask);out['medial_seconds']+=time.perf_counter()-tick
    tick=time.perf_counter();zs,zf=vec.skeleton(mask);out['zhang_seconds']+=time.perf_counter()-tick
    for name,s,f in [('medial',medial,fallback),('zhang',zs,zf)]:
        assert not (s&~mask).any();assert label(s,structure=np.ones((3,3)))[1]==n;assert euler_number(s,connectivity=2)==e
        out[name+'_fallback']+=len(f);out[name+'_pixels']+=int(s.sum());out[name+'_diameter_sum']+=float(width[s].sum())
    out['masks']+=1;out['foreground']+=int(mask.sum())
start=time.perf_counter();counts=collections.Counter();records=[];classes=collections.defaultdict(collections.Counter)
with fitz.open(pdf) as doc:
 for pn in (list(map(int,sys.argv[4:])) if mode in ('full','leaves') else sorted(groups)):
    q=[x for x in doc[pn-1].get_text('dict')['blocks'] if x['type']==1][0];im=Image.open(BytesIO(q['image']));w,h=im.size;x,y,X,Y=q['bbox'];sx=(X-x)/w;sy=(Y-y)/h
    if mode=='leaves':
        masks,core,unc=geo.leaf_hypotheses(im);counts['pages']+=1;counts['empty_core']+=not core.any();counts['uncertain_pixels']+=int(unc.sum());counts['core_pixels']+=int(core.sum());counts['image_pixels']+=w*h;continue
    if mode=='full':
        v=votes(im);c=collections.Counter();verify(v>3,c);records.append(dict(page=pn,**c));print(records[-1],flush=True);continue
    for i in groups[pn]:
        l,t,R,B=i['box'];l,t,R,B=max(0,math.floor((l*.36-x)/sx)),max(0,math.floor((t*.36-y)/sy)),min(w,math.ceil((R*.36-x)/sx)),min(h,math.ceil((B*.36-y)/sy));assert l<R and t<B
        ox,oy=max(0,l-64),max(0,t-64);crop=im.crop((ox,oy,min(w,R+64),min(h,B+64)));v=votes(crop);mask=v>3
        verify(mask,counts,external=counts['masks']%5==0)
        record,exact,curved=geo.vector_record(mask,source_sha256=r['source_sha256'],page=pn,page_rgb_sha256=geo.digest(im.tobytes()),origin=(ox,oy),page_size=im.size,px_to_pt=(sx,sy,x,y),method='ensemble-majority-context64');assert record['exact_svg_sha256']==geo.digest(exact.encode());records.append(record['id'])
        lab,rows=a.analyze(crop,v,6,origin=(ox,oy),page_size=im.size);zones=geo.script_zones(rows);k=r['answers'][i['id']]['content'];group='candidate' if i['stratum'].startswith('candidate') else 'random';cls='nontext' if k in ('blank','non_script') else k;c=classes[group+'/'+cls];c['n']+=1;c['zone_overlap']+=any(max(l,z['box'][0])<min(R,z['box'][2]) and max(t,z['box'][1])<min(B,z['box'][3]) for z in zones)
result=dict(mode=mode,counts=counts,records=records if mode=='full' else len(set(records)),classes=classes,seconds=round(time.perf_counter()-start,2));Path('geometry-'+mode+'-result.json').write_text(json.dumps(result,indent=2,default=lambda x:x.item()));print(json.dumps(result,indent=2,default=lambda x:x.item()))

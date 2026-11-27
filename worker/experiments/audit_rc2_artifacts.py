import json, hashlib, math, collections, time, sys
from pathlib import Path
from io import BytesIO
import fitz
import numpy as np
from PIL import Image,ImageFilter
from scipy.ndimage import label
import vrs_artifacts as a

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
# randomized independent component check
rng=np.random.default_rng(20261127)
for j in range(300):
    m=rng.random((int(rng.integers(1,50)),int(rng.integers(1,50))))<rng.random()
    ours,n=a.component_labels(m); ref,k=label(m,structure=np.ones((3,3)))
    assert n==k and np.array_equal(ours>0,m)
    assert len(set(zip(ours[m],ref[m])))==n
print('300 randomized 8-connected partitions match SciPy')
pdf,review=map(Path,sys.argv[1:]); r=json.loads(review.read_text()); m=r['manifest']; assert hashlib.file_digest(pdf.open('rb'),'sha256').hexdigest()==r['source_sha256']=='d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c'; assert hashlib.sha256(json.dumps({k:v for k,v in m.items() if k!='dataset_sha256'},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()==r['dataset_sha256']==m['dataset_sha256']; assert len(m['items'])==len(r['answers'])==200 and {i['id'] for i in m['items']}==set(r['answers'])
groups=collections.defaultdict(list)
for i in m['items']:
    if not i['stratum'].startswith('wrapper'):groups[i['page']].append(i)
res=collections.defaultdict(collections.Counter); start=time.perf_counter(); examples={}; total=0
with fitz.open(pdf) as doc:
 for pn,ii in sorted(groups.items()):
    q=[x for x in doc[pn-1].get_text('dict')['blocks'] if x['type']==1][0]; im=Image.open(BytesIO(q['image'])); w,h=im.size; x,y,X,Y=q['bbox']; sx=(X-x)/w;sy=(Y-y)/h
    for i in ii:
        l,t,R,B=i['box'];l,t,R,B=max(0,math.floor((l*.36-x)/sx)),max(0,math.floor((t*.36-y)/sy)),min(w,math.ceil((R*.36-x)/sx)),min(h,math.ceil((B*.36-y)/sy)); assert l<R and t<B
        ox,oy=max(0,l-64),max(0,t-64); crop=im.crop((ox,oy,min(w,R+64),min(h,B+64))); v=votes(crop); lab,rows=a.analyze(crop,v,6,origin=(ox,oy),page_size=(w,h)); assert np.array_equal(lab>0,v>0); assert sum(j['area'] for j in rows)==int((v>0).sum()); total+=len(rows)
        target=lab[t-oy:B-oy,l-ox:R-ox]; ids=set(np.unique(target))-{0}; hit=[j for j in rows if j['id'] in ids]; flags=set(f for j in hit for f in j['flags']); content=r['answers'][i['id']]['content']; group='candidate' if i['stratum'].startswith('candidate') else 'random'; cls='nontext' if content in ('blank','non_script') else content; c=res[group+'/'+cls]; c['n']+=1;c['foreground']+=bool(hit);c['intersecting_components']+=len(hit)
        for f in flags:c[f]+=1
        if hit and all('tiny' in j['flags'] for j in hit):c['tiny_only']+=1
        if i['id'] in ('VRS-RC2-001','VRS-RC2-013','VRS-RC2-014','VRS-RC2-160'):examples[i['id']]={'n':len(hit),'flags':sorted(flags)}
# Full-image smoke test; not equivalent to context-window thresholds.
full=[]
with fitz.open(pdf) as doc:
 for pn in (4,50,127,214):
    q=[x for x in doc[pn-1].get_text('dict')['blocks'] if x['type']==1][0]; im=Image.open(BytesIO(q['image'])); v=votes(im); lab,rows=a.analyze(im,v,6,origin=(0,0),page_size=im.size); assert np.array_equal(lab>0,v>0); assert sum(j['area'] for j in rows)==int((v>0).sum()); ref,k=label(v>0,structure=np.ones((3,3))); assert len(rows)==k and len(set(zip(lab[v>0],ref[v>0])))==k; full.append({'page':pn,'components':k,'pixels':int((v>0).sum())})
out={'full_smoke':full,'pages':len(groups),'cases':sum(map(len,groups.values())),'components_all_windows':total,'results':res,'examples':examples,'elapsed':round(time.perf_counter()-start,2)}
Path('audit-result.json').write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

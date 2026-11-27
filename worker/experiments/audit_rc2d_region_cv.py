"""Exploratory grouped development CV; never a production model or independent holdout."""
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
    return np.sum([adaptive(g,"sauvola"),adaptive(g,"wolf"),adaptive(n,"sauvola"),adaptive(n,"wolf"),adaptive(normalize(np.asarray(im.getchannel("R"))),"sauvola"),adaptive(normalize(np.asarray(im.getchannel("B"))),"sauvola")],axis=0,dtype=np.uint16)
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, balanced_accuracy_score, roc_auc_score
import re
pdf,review=map(Path,sys.argv[1:3]);r=json.loads(review.read_text());m=r['manifest']
assert hashlib.file_digest(pdf.open('rb'),'sha256').hexdigest()==r['source_sha256']=='d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c'
assert hashlib.sha256(json.dumps({k:v for k,v in m.items() if k!='dataset_sha256'},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()==r['dataset_sha256']==m['dataset_sha256']
assert len(m['items'])==len(r['answers'])==200 and {i['id'] for i in m['items']}==set(r['answers'])
X=[];Y=[];G=[];T=[]
with fitz.open(pdf) as doc:
 for i in m['items']:
  typ=r['answers'][i['id']]['content'];stratum=i['stratum'];pn=i['page']
  if stratum.startswith('wrapper') or typ not in ('handwriting','blank','non_script'):continue
  page=doc[pn-1];folio=page.get_text().splitlines()[2];mat=re.match(r'^(\d+)[rv]',folio);group=mat.group(1) if mat else 'other'
  q=[x for x in page.get_text('dict')['blocks'] if x['type']==1][0];im=Image.open(BytesIO(q['image']));w,h=im.size;x,y,P,Q=q['bbox'];sx=(P-x)/w;sy=(Q-y)/h
  l,t,R,B=i['box'];l,t,R,B=max(0,math.floor((l*.36-x)/sx)),max(0,math.floor((t*.36-y)/sy)),min(w,math.ceil((R*.36-x)/sx)),min(h,math.ceil((B*.36-y)/sy));assert l<R and t<B
  ox,oy=max(0,l-64),max(0,t-64);crop=im.crop((ox,oy,min(w,R+64),min(h,B+64)));v=votes(crop);lab,rows=a.analyze(crop,v,6,origin=(ox,oy),page_size=im.size)
  box=np.s_[t-oy:B-oy,l-ox:R-ox]; vv=v[box];ids=set(np.unique(lab[box]))-{0};hit=[z for z in rows if z['id'] in ids];maxa=max((z['area'] for z in hit),default=0);pix=np.asarray(crop)[box].astype(float); gray=np.asarray(crop.convert('L'))[box].astype(float)
  features=[np.log1p(R-l),np.log1p(B-t),np.log1p(vv.size),min(l,t,w-R,h-B)/max(w,h),np.mean(vv>0),np.mean(vv>3),np.mean(vv==6),np.mean(vv)/6,np.log1p(len(hit)),np.log1p(maxa),float(gray.std()),float(gray.mean()),float((pix[:,:,0]-pix[:,:,2]).mean()),float((pix[:,:,1]-pix[:,:,2]).mean())]
  for f in ['tiny','elongated','near_image_edge','touches_window_edge','broad_low_contrast','low_method_agreement','line_context_hint','isolated_in_window']:
   features.append(sum(f in z['flags'] for z in hit)/max(1,len(hit)))
  X.append(features);Y.append(int(typ=='handwriting'));G.append(group);T.append(stratum.startswith('candidate'))
X,Y,G,T=map(np.array,(X,Y,G,T));Xc,Yc,Gc=X[T],Y[T],G[T];print('candidates',len(Yc),'groups',len(set(Gc)),'labels',np.bincount(Yc),'random',len(Y[~T]),flush=True)
cv=list(StratifiedGroupKFold(5,shuffle=True,random_state=271126).split(Xc,Yc,Gc))
assert all(not (set(Gc[train])&set(Gc[test])) for train,test in cv)
for name,model in [('logistic',make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=1000,random_state=271126))),('forest',RandomForestClassifier(n_estimators=300,min_samples_leaf=4,max_features='sqrt',random_state=271126,n_jobs=1))]:
  prob=cross_val_predict(model,Xc,Yc,groups=Gc,cv=cv,method='predict_proba')[:,1]
  print(name,'auc',round(roc_auc_score(Yc,prob),4),'confusion',confusion_matrix(Yc,prob>=.5).tolist(),flush=True)
  for cutoff in [.2,.35,.5,.65,.8]:print('  cutoff',cutoff,'cm',confusion_matrix(Yc,prob>=cutoff).tolist(),flush=True)

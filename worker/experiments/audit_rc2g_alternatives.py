import hashlib,io,time,json,sys
from pathlib import Path
from collections import defaultdict
import fitz,numpy as np
from PIL import Image,ImageFilter
from scipy.ndimage import label,find_objects
import vrs_hybrid_alternatives as a

def norm(g):
 b=np.asarray(Image.fromarray(g).filter(ImageFilter.GaussianBlur(16)),float)
 return np.clip(np.rint(255*g.astype(float)/np.maximum(b,1)),0,255).astype(np.uint8)
def adaptive(g,method):
 x=np.pad(g.astype(float),15,mode='edge')
 def mean(y):
  s=np.pad(y.cumsum(0).cumsum(1),((1,0),(1,0)));return (s[31:,31:]-s[:-31,31:]-s[31:,:-31]+s[:-31,:-31])/961
 m=mean(x);sd=np.sqrt(np.maximum(0,mean(x*x)-m*m))
 if method=='s':t=m*(1+.25*(sd/128-1))
 elif sd.max()<=1e-9:return np.zeros(g.shape,bool)
 else:t=m+.25*(sd/sd.max()-1)*(m-float(g.min()))
 return g<t

def make(mask,name):
 lab,n=label(mask,structure=np.ones((3,3))); rows=[]; pairs=[];grid=defaultdict(list)
 for i,(ys,xs) in enumerate(find_objects(lab),1):
  l,t,r,b=xs.start,ys.start,xs.stop,ys.stop; rid=f'{name}-{i}';rows.append(dict(id=rid,box=[l,t,r,b],area=int((lab[ys,xs]==i).sum())))
  if max(r-l,b-t)>64:continue
  near=set()
  for gy in range((t-4)//16,(b+4)//16+1):
   for gx in range((l-4)//16,(r+4)//16+1):near.update(grid[gx,gy])
  for j in sorted(near):
   L,T,R,B=rows[j]['box'];dx,dy=max(l-R,L-r,0),max(t-B,T-b,0);xo,yo=min(r,R)-max(l,L),min(b,B)-max(t,T)
   if max(dx,dy)<=4 and (xo>0 or yo>0):pairs.append(dict(members=[rid,rows[j]['id']]))
  for gy in range(t//16,(b-1)//16+1):
   for gx in range(l//16,(r-1)//16+1):grid[gx,gy].append(i-1)
 return lab,dict(components=rows,pairs=pairs,pixels=int(mask.sum()))
pdf=Path(sys.argv[1]); assert hashlib.file_digest(pdf.open('rb'),'sha256').hexdigest()=='d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c'
with fitz.open(pdf) as doc:
 for pn in (4,50,127,214):
  start=time.perf_counter();q=[b for b in doc[pn-1].get_text('dict')['blocks'] if b['type']==1];assert len(q)==1
  im=Image.open(io.BytesIO(q[0]['image']));g=np.asarray(im.convert('L'));ng=norm(g);v=np.sum([adaptive(g,'s'),adaptive(g,'w'),adaptive(ng,'s'),adaptive(ng,'w'),adaptive(norm(np.asarray(im.getchannel('R'))),'s'),adaptive(norm(np.asarray(im.getchannel('B'))),'s')],axis=0,dtype=np.uint16)
  labs={};o={}
  for name,mask in zip(a.MASKS,(v>0,v>3,v==6)):labs[name],o[name]=make(mask,name)
  r=a.build(o,labs,(0,0));assert r==a.build(o,labs,(0,0))
  for name in a.MASKS:
   for s in r['by_mask'][name]['splits']:assert sum(p['area'] for p in s['parts'])==next(x['area'] for x in o[name]['components'] if x['id']==s['parent'])
  print(json.dumps(dict(page=pn,components={k:len(o[k]['components']) for k in a.MASKS},splits={k:len(r['by_mask'][k]['splits']) for k in a.MASKS},compounds={k:len(r['by_mask'][k]['compounds']) for k in a.MASKS},links={k:len(x['links']) for k,x in r['lineage'].items()},seconds=round(time.perf_counter()-start,2))),flush=True)

import json, hashlib, math, collections, time, sys
from pathlib import Path
from io import BytesIO
import fitz
import numpy as np
from PIL import Image
from scipy.ndimage import label
import vrs_binarize as b
pdf,review=map(Path,sys.argv[1:]); start=time.perf_counter()
assert hashlib.file_digest(pdf.open('rb'),'sha256').hexdigest()=='d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c'
r=json.loads(review.read_text()); m=r['manifest']; items=m['items']; expected=m['dataset_sha256']; assert expected==r['dataset_sha256']; assert hashlib.sha256(json.dumps({k:v for k,v in m.items() if k!='dataset_sha256'},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()==expected
assert len(items)==len(r['answers'])==200 and {i['id'] for i in items}==set(r['answers'])
groups=collections.defaultdict(list); result=collections.defaultdict(lambda:collections.defaultdict(collections.Counter))
for i in items:
 if not i['stratum'].startswith('wrapper'): groups[i['page']].append(i)
with fitz.open(pdf) as doc:
 for pn, ii in sorted(groups.items()):
  page=doc[pn-1]; block=[x for x in page.get_text('dict')['blocks'] if x['type']==1]; assert len(block)==1
  q=block[0]; im=Image.open(BytesIO(q['image'])); assert im.mode=='RGB'; w,h=im.size
  x,y,X,Y=q['bbox']; sx=(X-x)/w; sy=(Y-y)/h
  for i in ii:
   a,c,d,e=i['box']; a,c,d,e= max(0,math.floor((a*.36-x)/sx)),max(0,math.floor((c*.36-y)/sy)),min(w,math.ceil((d*.36-x)/sx)),min(h,math.ceil((e*.36-y)/sy)); assert a<d and c<e
   l,t=max(0,a-64),max(0,c-64); crop=im.crop((l,t,min(w,d+64),min(h,e+64))); masks=b.hypotheses(crop); ag=b.agreement([masks[k] for k in b.ENSEMBLE]); masks.update({f'ensemble_{k}':ag[k] for k in ('union','intersection','majority')})
   typ=r['answers'][i['id']]['content']; group='candidate' if i['stratum'].startswith('candidate') else 'random'
   for name,mask in masks.items():
    v=mask[c-t:e-t,a-l:d-l]; st=result[group][name]; st[typ+'_n']+=1; st[typ+'_present']+=int(v.any()); st[typ+'_pixels']+=int(v.sum()); st[typ+'_area']+=v.size
    if typ=='handwriting': st['handwriting_components']+=label(v,structure=np.ones((3,3)))[1]
   unc=ag['uncertain'][c-t:e-t,a-l:d-l]; st=result[group]['disagreement']; st[typ+'_n']+=1; st[typ+'_present']+=int(unc.any()); st[typ+'_pixels']+=int(unc.sum()); st[typ+'_area']+=unc.size
out={'source_sha256':r['source_sha256'],'dataset_sha256':expected,'pages':len(groups),'cases':sum(map(len,groups.values())),'context_margin_native_px':64,'elapsed_seconds':round(time.perf_counter()-start,2),'results':result}
Path('audit-result.json').write_text(json.dumps(out,indent=2)); print('pages/cases/sec',out['pages'],out['cases'],out['elapsed_seconds']);
for k,v in sorted(result['candidate'].items(),key=lambda kv:(-kv[1]['handwriting_present'],kv[1]['non_script_present']+kv[1]['blank_present'])):
 print(k, v['handwriting_present'],92-v['non_script_present']-v['blank_present'], v['handwriting_components'])

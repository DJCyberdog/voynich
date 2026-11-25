import csv, hashlib, json, sys
import cv2, fitz, numpy as np
from pathlib import Path
cv2.setNumThreads(1)
PDF='d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c'
def mask(gray,method):
    if method=='otsu': raw=cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV|cv2.THRESH_OTSU)[1]
    else: raw=cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,12)
    h,w=gray.shape; n,labels,stats,_=cv2.connectedComponentsWithStats(raw,8)
    keep=[]; out=np.zeros_like(raw)
    for i,(x,y,bw,bh,a) in enumerate(stats[1:],1):
        if 4<=a<=.2*h*w and 3<=bh<=.9*h and bw<=.85*w and x>0 and y>0 and x+bw<w and y+bh<h: keep.append(i);out[labels==i]=255
    return out,len(keep)
def measure(gray):
    a,n=mask(gray,'otsu');b,m=mask(gray,'adaptive'); h,w=gray.shape
    union=np.count_nonzero((a>0)|(b>0)); iou=np.count_nonzero((a>0)&(b>0))/union if union else 0
    ys,xs=np.where(a>0); box=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)] if n else None
    off=[abs((box[0]+box[2])/w-1),abs((box[1]+box[3])/h-1)] if box else None
    frac=np.count_nonzero(a)/(h*w)
    gates={'components':n>=2 and m>=2,'fraction':.015<=frac<=.35,'iou':iou>=.45,'center':off is not None and max(off)<=.45}
    return dict(components=[n,m],fraction=round(frac,8),iou=round(iou,8),bbox=box,offset=off,gates=gates,passed=all(gates.values()))
def summarize(rows):
    return {'n':len(rows),'passed':sum(r['passed'] for r in rows),'gates':{k:sum(r['gates'][k] for r in rows) for k in rows[0]['gates']}}
def run(pdf,review):
    assert hashlib.sha256(Path(pdf).read_bytes()).hexdigest()==PDF
    rows=list(csv.DictReader(open(review,encoding='utf-8-sig')));assert len(rows)==len({r['review_id'] for r in rows})==74
    blank=np.full((100,160),255,np.uint8); strokes=blank.copy();strokes[35:65,60:65]=0;strokes[35:65,90:95]=0;edge=blank.copy();edge[35:65,:5]=0
    controls={'blank':not measure(blank)['passed'],'strokes':measure(strokes)['passed'],'edge_rejected':mask(edge,'otsu')[1]==0 and mask(edge,'adaptive')[1]==0};assert all(controls.values()),controls
    doc=fitz.open(pdf); cache={};results=[];shifted=[]
    for r in rows:
        p=int(r['page']);x=float(r['text_x']);y=float(r['text_y'])
        if p not in cache:
            pix=doc[p-1].get_pixmap(dpi=200,colorspace=fitz.csRGB,alpha=False);cache[p]=cv2.cvtColor(np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3),cv2.COLOR_RGB2GRAY)
        gray=cache[p];h,w=gray.shape
        for shift,target in [(0,results),(.05,shifted)]:
            x0,x1=round((x-.045)*w),round((x+.045)*w);y0,y1=round((y+shift-.018)*h),round((y+shift+.018)*h)
            assert 0<=x0<x1<=w and 0<=y0<y1<=h
            target.append(dict(id=r['review_id'],page=p,crop=[x0,y0,x1,y1],**measure(gray[y0:y1,x0:x1])))
    summary=summarize(results)
    return dict(experiment='EXP-0038g',pdf_sha256=PDF,review_sha256=hashlib.sha256(Path(review).read_bytes()).hexdigest(),opencv=cv2.__version__,pymupdf=fitz.VersionBind,numpy=np.__version__,controls=controls,summary=summary,shifted_summary=summarize(shifted),pages={str(p):summarize([r for r in results if r['page']==p]) for p in sorted(cache)},readiness=summary['passed']/len(results)>=.8,results=results,shifted=shifted)
if __name__=='__main__':
    Path(sys.argv[3]).write_text(json.dumps(run(*sys.argv[1:3]),sort_keys=True,indent=2,default=lambda x:x.item())+'\n')

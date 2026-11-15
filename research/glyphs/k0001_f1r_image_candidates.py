#!/usr/bin/env python3
"""K-0001 f1r exploratory image component detector. NO GLYPH IDENTIFICATION.
Requires owner-held source PDF and locally installed fitz, cv2, numpy.
Writes derived candidate coordinates, not manuscript pixels or transcription.
python k0001_f1r_image_candidates.py voynich.pdf output-directory
"""
import collections
import hashlib
import json
import sys
from pathlib import Path
import fitz
import cv2
import numpy as np

PDF_SHA="d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c"
RGB_SHA="cbd95103a136471df3a27933f881fa4de7664c1d1075c4930c5e9e24234daf10"
CENTERS=[390,431,473,513,553,601,644,685,725,762,844,884,928,966,1004,1037,1072,1115,1151,1186,1215,1312,1355,1393,1432,1473,1501,1541]
BOUNDS=[348]+[round((a+b)/2) for a,b in zip(CENTERS,CENTERS[1:])]+[1568]

def file_hash(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1048576),b""):
            h.update(block)
    return h.hexdigest()

def main(source,output):
    if file_hash(source)!=PDF_SHA:
        raise ValueError("Wrong original PDF: SHA-256 mismatch")
    doc=fitz.open(source)
    if len(doc)!=214 or "1r" not in doc[3].get_text():
        raise ValueError("Wrong page index")
    pix=doc[3].get_pixmap(matrix=fitz.Matrix(2.5,2.5),alpha=False)
    if (pix.width,pix.height,pix.n)!=(1489,2105,3):
        raise ValueError("Wrong render geometry")
    if hashlib.sha256(pix.samples).hexdigest()!=RGB_SHA:
        raise ValueError("RGB source render mismatch: do not reuse coordinates")
    im=np.frombuffer(pix.samples,dtype=np.uint8).reshape(2105,1489,3)
    light=cv2.cvtColor(im,cv2.COLOR_RGB2LAB)[:,:,0]
    light=cv2.GaussianBlur(light,(3,3),0.7)
    blackhat=cv2.morphologyEx(light,cv2.MORPH_BLACKHAT,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(35,35)))
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    totals={}
    for t in (14,18,22,26):
        bitmap=(blackhat>=t).astype("uint8")
        n,labels,stats,centroids=cv2.connectedComponentsWithStats(bitmap,connectivity=8)
        counts=collections.Counter()
        records=[]
        for k in range(1,n):
            x,y,w,h,area=(int(v) for v in stats[k])
            cx,cy=(float(v) for v in centroids[k])
            if not(270<=cx<=1280 and 348<=cy<1568 and 5<=area<=5000):
                continue
            j=min(range(28),key=lambda z:abs(CENTERS[z]-cy))
            if not BOUNDS[j]<=cy<BOUNDS[j+1]:
                continue
            counts[j+1]+=1
            if t==18:
                records.append({"id":f"K0001-F1R-T18-CC{k:05d}",
                    "bbox_xyxy":[x,y,x+w,y+h],"foreground_pixels":area,
                    "provisional_line":f"f1r.{j+1}",
                    "source_rgb_sha256":RGB_SHA,"kind":"DARK_PIXEL_COMPONENT_CANDIDATE",
                    "grapheme_id":None,"noise_join_split_unresolved":True})
        totals[str(t)]={"candidate_components":sum(counts.values()),
            "per_provisional_line":{str(i):counts[i] for i in range(1,29)}}
        if t==18:
            with (output/"f1r_t18_component_candidates.jsonl").open("w") as f:
                for record in records:
                    f.write(json.dumps(record,sort_keys=True)+"\n")
    hsv=cv2.cvtColor(im,cv2.COLOR_RGB2HSV)
    rois=[("red1",(290,585,425,674)),("blank1",(380,1660,515,1749)),
          ("red2",(285,810,370,860)),("blank2",(1000,1680,1085,1730))]
    controls=[]
    for name,(x0,y0,x1,y1) in rois:
        p=hsv[y0:y1,x0:x1]
        red=(p[:,:,0]<=9)&(p[:,:,1]>=75)&(p[:,:,2]<=200)
        controls.append({"name":name,"bbox":[x0,y0,x1,y1],
                         "area":int(red.size),"red_threshold_pixels":int(red.sum())})
    result={"pdf_sha256":PDF_SHA,"raster_sha256":RGB_SHA,"raster_px":[1489,2105],
            "threshold_sensitivity":totals,"red_controls":controls,
            "warning":"Connected components are NOT manuscript glyphs; no independent annotation, second image witness or full pixelwise segmentation."}
    (output/"f1r_image_candidate_summary.json").write_text(
        json.dumps(result,indent=2)+"\n")
    print(json.dumps({"thresholds":{k:v["candidate_components"] for k,v in totals.items()},
                       "red_controls":controls}))
if __name__=="__main__":
    if len(sys.argv)!=3:
        raise SystemExit("Usage: script.py original.pdf output_dir")
    main(*sys.argv[1:])

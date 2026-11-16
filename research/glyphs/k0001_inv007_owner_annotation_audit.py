"""Reproducible source-only INV-007 metrics; inputs remain owner-local. NOT glyph decoding."""
import argparse,hashlib,json
from pathlib import Path
import cv2,fitz,numpy as np
from PIL import Image
PDF="d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c"
RASTER="cbd95103a136471df3a27933f881fa4de7664c1d1075c4930c5e9e24234daf10"
MARK="c980e9fa87520e29b276e468bfd49b68c2c8423061b72c65edd1ef534b6d4190"
POSHASH="52741a707b175fef5629129d25168fa666d04445087c1dcaac67aec354f485a8"
NEGHASH="271190883ca64508bbd8f7e0d83fdfdfd8fb3a7e565ff3c7adf43b31f0a9685e"
MAIN=(760,337,1050,414)
NEXT=(280,405,740,485)
POS=(465,340,495,395)
NEG=(720,275,790,315)
def sha(b):return hashlib.sha256(b).hexdigest()
def crop(a,r):
 x0,y0,x1,y1=r
 return a[y0:y1,x0:x1]
def components(a,r,t):
 z=(crop(a,r)>t).astype("uint8")
 n,_,s,_=cv2.connectedComponentsWithStats(z,8)
 good=[s[i] for i in range(1,n) if int(s[i,4])>=3]
 w,h=r[2]-r[0],r[3]-r[1]
 edge=sum(int(v[0]==0 or v[1]==0 or v[0]+v[2]>=w or v[1]+v[3]>=h) for v in good)
 return dict(dark_pixels=int(z.sum()),all_components=n-1,components_ge3=len(good),components_ge3_touching_border=edge)
def run(pdf,marked):
 assert sha(pdf.read_bytes())==PDF
 assert sha(marked.read_bytes())==MARK
 d=fitz.open(str(pdf));p=d[3].get_pixmap(matrix=fitz.Matrix(2.5,2.5),alpha=False,colorspace=fitz.csRGB)
 a=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)
 assert a.shape==(2105,1489,3) and sha(a.tobytes())==RASTER
 assert sha(crop(a,POS).tobytes())==POSHASH
 assert sha(crop(a,NEG).tobytes())==NEGHASH
 gray=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY)
 bg=cv2.morphologyEx(gray,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(23,23)))
 residual=np.maximum(0,bg.astype("int16")-gray.astype("int16")).astype("uint8")
 ts=[int(np.ceil(np.percentile(crop(residual,NEG),u))) for u in (99,99.5,99.9)]
 machine={k:{str(t):components(residual,r,t) for t in ts} for k,r in (("f1r1",MAIN),("f1r2_left",NEXT))}
 marked_rgb=np.asarray(Image.open(marked).convert("RGB"))
 assert marked_rgb.shape==(255,960,3)
 source=np.asarray(Image.fromarray(crop(a,MAIN)).resize((960,255),Image.Resampling.LANCZOS))
 mask=(np.max(marked_rgb,axis=2)<45)&(np.min(source,axis=2)>70)
 n,_,_,_=cv2.connectedComponentsWithStats(mask.astype("uint8"),8)
 m,_,st,_=cv2.connectedComponentsWithStats((~mask).astype("uint8"),4)
 closed=sum(1 for i in range(1,m) if st[i,4]>=100 and st[i,0]>0 and st[i,1]>0 and st[i,0]+st[i,2]<960 and st[i,1]+st[i,3]<255)
 return {"id":"K-0001-INV-007","date":"2026-11-16","method_phase":"EXPLORATORY_NOT_CONFIRMATORY",
 "source_pdf_sha256":PDF,"raster_rgb_sha256":RASTER,"owner_marked_png_sha256":MARK,
 "roi_xyxy":list(MAIN),"f1r2_exploratory_xyxy":list(NEXT),
 "control_positive_rgb_sha256":POSHASH,"control_negative_rgb_sha256":NEGHASH,
 "negative_hash_erratum":"Previous INV-006 negative hash had 62 hex digits; corrected from raw 70x40 RGB pixels.",
 "human_areas_reported_by_owner":8,"machine_closed_partitions_ge100px":closed,
 "overlay_line_components_8connected":n-1,"drawn_mask_pixels":int(mask.sum()),
 "thresholds_negative_control_percentiles_99_99p5_99p9":ts,
 "method":"f1r grayscale morphological close ellipse 23x23 minus source; 8-connected dark components area>=3; two other topological measures on owner overlay; no editorial text used",
 "machine":machine,
 "conclusion":"human areas are not ink-stroke polygons or glyphs; no INV-005 IoU or second-reader agreement",
 "validated_grapheme_classes":0,"verified_eva_mappings":0,
 "independent_second_annotator":False,"image_witness_count":1}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--pdf",required=True,type=Path);p.add_argument("--marked",required=True,type=Path);p.add_argument("--out",required=True,type=Path)
 a=p.parse_args();data=run(a.pdf,a.marked)
 a.out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(data["human_areas_reported_by_owner"],data["machine_closed_partitions_ge100px"],data["thresholds_negative_control_percentiles_99_99p5_99p9"])

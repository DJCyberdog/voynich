"""K-0001 f1r S01/S02 exploratory pigment connectivity; NOT glyph classification.
Usage: python k0001_f1r_red_topology.py voynich.pdf ZL3b-n.txt
Requires locally available PyMuPDF 1.26.7, numpy, opencv-python.
Outputs only derived JSON; NEVER manuscript pixels or source transcription.
"""
import hashlib, json, re, sys
from pathlib import Path
import cv2, fitz, numpy as np

PDF_SHA="d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c"
TEXT_SHA="bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc"
RGB_SHA="cbd95103a136471df3a27933f881fa4de7664c1d1075c4930c5e9e24234daf10"
ROIS={"S01":(289,581,424,674),"S02":(285,807,371,867),
      "BLANK01":(380,1660,515,1749),"BLANK02":(1000,1680,1085,1730)}
EDITORIAL={"S01":"f1r.7","S02":"f1r.11"}

def digest(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1048576),b""):h.update(block)
    return h.hexdigest()

def areas(mask):
    n, labels, stats, ctr = cv2.connectedComponentsWithStats(mask.astype(np.uint8),connectivity=8)
    return sorted([int(s[4]) for s in stats[1:] if int(s[4])>=4],reverse=True)

def analyze(pdf_path, transcript_path):
    if digest(pdf_path)!=PDF_SHA or digest(transcript_path)!=TEXT_SHA:
        raise ValueError("Wrong source bytes")
    doc=fitz.open(pdf_path)
    if len(doc)!=214 or "1r" not in doc[3].get_text():raise ValueError("Unexpected page")
    p=doc[3].get_pixmap(matrix=fitz.Matrix(2.5,2.5),alpha=False)
    if (p.width,p.height,p.n)!=(1489,2105,3) or hashlib.sha256(p.samples).hexdigest()!=RGB_SHA:
        raise ValueError("Unexpected image raster")
    rgb=np.frombuffer(p.samples,dtype=np.uint8).reshape((2105,1489,3))
    transcript=Path(transcript_path).read_text(encoding="utf-8")
    result={}
    for name,(x0,y0,x1,y1) in ROIS.items():
        hsv=cv2.cvtColor(rgb[y0:y1,x0:x1],cv2.COLOR_RGB2HSV)
        m=np.uint8((hsv[:,:,0]<=9)&(hsv[:,:,1]>=75)&(hsv[:,:,2]<=200))
        close={}
        for width in [1,3,5,7,9,11,15]:
            mm=m if width==1 else cv2.morphologyEx(m,cv2.MORPH_CLOSE,
                cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(width,width)))
            close[str(width)]=areas(mm)
        tags=[]
        if name in EDITORIAL:
            hit=re.search(r"^<"+re.escape(EDITORIAL[name])+r",[^>]*>\s*(.*)$",transcript,re.M)
            if hit is None:raise ValueError("Missing editorial line")
            tags=re.findall(r"<!@([0-9]+);>",hit.group(1))
        result[name]={"bbox_xyxy":[x0,y0,x1,y1],"red_mask_pixels":int(m.sum()),
                      "component_areas_min4_by_closing_kernel":close,
                      "editorial_line":EDITORIAL.get(name),
                      "editorial_markup_ids_not_graphemes":tags}
    assert result["S01"]["red_mask_pixels"]==1713 and result["S02"]["red_mask_pixels"]==470
    assert result["S01"]["component_areas_min4_by_closing_kernel"]["1"]==[1713]
    assert result["S02"]["component_areas_min4_by_closing_kernel"]["1"]==[254,125,83,8]
    assert result["S02"]["component_areas_min4_by_closing_kernel"]["15"]==[651]
    assert result["S01"]["editorial_markup_ids_not_graphemes"]==["252"]
    assert result["S02"]["editorial_markup_ids_not_graphemes"]==["253"]
    assert result["BLANK01"]["red_mask_pixels"]==result["BLANK02"]["red_mask_pixels"]==0
    return {"source_pdf_sha256":PDF_SHA,"source_transcript_sha256":TEXT_SHA,
            "source_f1r_raster_sha256":RGB_SHA,"raster_size":[1489,2105],
            "hsv_rule":"H<=9, S>=75, V<=200 (OpenCV)", "roi_results":result,
            "interpretation":"Exploratory image masks and editor tags only; 0 physical glyph identities established"}

if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("Usage: script.py voynich.pdf ZL3b-n.txt")
    print(json.dumps(analyze(*sys.argv[1:]),indent=2))

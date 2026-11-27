"""Frozen synthetic specificity stress test for EXP-0038g, no manuscript images."""
import hashlib
import json
import sys
from pathlib import Path
import cv2
import numpy as np
import exp0038g_segmentation as parent

PARENT_SHA = "388208b3b93778d79de333f3222de04898adfabc5ced745b3bc25a50cee2dfce"

def run():
    assert hashlib.sha256(Path(parent.__file__).read_bytes()).hexdigest() == PARENT_SHA
    def blank():
        return np.full((100,160),255,np.uint8)
    cases = []
    def add(name,kind,img):
        cases.append((name,kind,img))
    add("blank","sanity_negative",blank())
    img=blank(); img[35:65,:5]=0; add("edge","sanity_negative",img)
    img=blank(); img[35:65,60:65]=0; img[35:65,90:95]=0; add("parent_strokes","sanity_positive",img)
    for i,t in enumerate((2,3,4,5)):
        img=blank()
        cv2.putText(img,"AB",(48,65),cv2.FONT_HERSHEY_SIMPLEX,1.2,0,t,cv2.LINE_8)
        add(f"text_{i}","synthetic_text",img)
        img=blank()
        for x in (58,102):
            cv2.circle(img,(x,50),12,0,t,cv2.LINE_8)
        add(f"rings_{i}","nontext_rings",img)
        img=blank()
        for x in (58,102):
            cv2.ellipse(img,(x,50),(9,17),30,0,360,0,t,cv2.LINE_8)
            cv2.line(img,(x-7,61),(x+7,39),0,t,cv2.LINE_8)
        add(f"leaves_{i}","nontext_leaves",img)
        img=blank()
        for x in (58,102):
            cv2.rectangle(img,(x-10,40),(x+10,60),0,t,cv2.LINE_8)
        add(f"squares_{i}","nontext_squares",img)
    rows=[]
    for name,kind,img in cases:
        m=parent.measure(img)
        rows.append(dict(id=name,kind=kind,passed=bool(m["passed"]),iou=m["iou"],fraction=m["fraction"],gates={k:bool(v) for k,v in m["gates"].items()}))
    counts={}
    for r in rows:
        c=counts.setdefault(r["kind"],dict(n=0,passed=0));c["n"]+=1;c["passed"]+=r["passed"]
    neg=[r for r in rows if r["kind"].startswith("nontext_")]
    sanity=(not rows[0]["passed"] and not rows[1]["passed"] and rows[2]["passed"])
    return dict(experiment="EXP-0038g1",parent_sha256=PARENT_SHA,opencv=cv2.__version__,numpy=np.__version__,sanity=bool(sanity),counts=counts,nontext_total=len(neg),nontext_passed=sum(r["passed"] for r in neg),decision=("CONTRADICTED" if sanity and any(r["passed"] for r in neg) else "NOT_FALSIFIED" if sanity else "INCONCLUSIVE"),rows=rows)
if __name__=="__main__":
    Path(sys.argv[1]).write_text(json.dumps(run(),sort_keys=True,indent=2)+"\n")

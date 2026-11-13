#!/usr/bin/env python3
"""EXP-0024: all-pair immediate EVA context-cosine matrix, Python stdlib only.
Requires exact owner-held ZL3b-n v3b; does not rehost original text.
ASCII and greedy-EVA-composite conventions are separately labeled.
"""
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import argparse,csv,hashlib,json,math,re

SOURCE_SHA="bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc"
LINE=re.compile(r"^<(f\d+[rv](?:\d+)?)\.(\d+),([^>]+)>\s*(.*)$")
LIGATURES=("cth","ckh","cph","cfh","ch","sh")
EXCLUDE={"f57v","f49v","f66r"}

def get_words(raw):
    folios=set()
    words=[]
    for line in raw.decode("utf-8-sig").splitlines():
        m=LINE.match(line)
        if not m or not m[3].endswith("P0") or m[1] in EXCLUDE:continue
        folios.add(m[1])
        body=re.sub(r"<!.*?>","",m[4]).replace("<%>","").replace("<$>","").replace("<->",".")
        for word in re.split(r"[.\s]+",body):
            if "," in word or not re.fullmatch(r"[a-z]{2,}",word):continue
            words.append(word)
    return words,len(folios)

def tokenize(word,mode):
    if mode=="ascii":return list(word)
    units=[];i=0
    while i<len(word):
        lig=next((s for s in LIGATURES if word.startswith(s,i)),None)
        if lig: units.append(lig);i+=len(lig)
        else:units.append(word[i]);i+=1
    return units

def calc(words,mode):
    freq=Counter()
    ctx=defaultdict(Counter)
    for w in words:
        unit=tokenize(w,mode)
        freq.update(unit)
        for i,g in enumerate(unit):
            left=unit[i-1] if i else "^"
            right=unit[i+1] if i+1<len(unit) else "$"
            ctx[g][(left,right)]+=1
    names=sorted(freq)
    norm={g:math.sqrt(sum(n*n for n in ctx[g].values())) for g in names}
    def cos(x,y):
        return sum(n*ctx[y].get(k,0) for k,n in ctx[x].items())/(norm[x]*norm[y])
    matrix=[[1.0 if a==b else cos(a,b) for b in names] for a in names]
    pairs=sorted(((a,b,cos(a,b),freq[a],freq[b]) for a,b in combinations(names,2)),key=lambda v:-v[2])
    return names,matrix,pairs,freq

def output(path,mode,names,matrix,pairs,freq):
    path.mkdir(parents=True,exist_ok=True)
    with (path/f"{mode}_matrix.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f);w.writerow(["glyph"]+names)
        for a,row in zip(names,matrix):w.writerow([a]+[f"{x:.9f}" for x in row])
    with (path/f"{mode}_pairs.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f);w.writerow(["rank","a","b","cosine","n_a","n_b","min_n","both_ge_100"])
        for i,(a,b,v,na,nb) in enumerate(pairs,1):w.writerow([i,a,b,f"{v:.9f}",na,nb,min(na,nb),int(min(na,nb)>=100)])
    return dict(units=len(names),pairs=len(pairs),unit_counts=dict(freq),
      top_stable=[dict(a=a,b=b,cosine=round(v,9),min_count=min(na,nb))
          for a,b,v,na,nb in pairs if min(na,nb)>=100][:25])

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    raw=a.input.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:raise SystemExit("Input SHA-256 mismatch")
    words,folios=get_words(raw)
    res=dict(input_sha256=SOURCE_SHA,word_instances=len(words),folio_count=folios,
             context="ordered immediate left/right neighbor, boundaries ^/$",
             evidence_scope="descriptive within one tagged IVTFF transcription; not images or semantics")
    for mode in ("ascii","glyph"):
        names,matrix,pairs,freq=calc(words,mode)
        res[mode]=output(a.output,mode,names,matrix,pairs,freq)
    (a.output/"exp0024_summary.json").write_text(json.dumps(res,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:res[k] for k in ("input_sha256","word_instances","folio_count")}))
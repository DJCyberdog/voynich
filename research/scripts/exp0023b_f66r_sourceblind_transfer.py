#!/usr/bin/env python3
"""EXP-0023B frozen f66r prospective list-transfer probe.

Only the program inspects candidate target symbols; output contains summaries
and folio/locus identifiers, never target transcription strings.
The rule/eligibility were committed at 26a031e396d781c713abc97be993332bb7128e4e.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import random
import re

SOURCE_SHA = "bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc"
FOLIOS = ("f66r","f66v","f67r","f67v")
SYMBOL = re.compile(r"(?:[a-z]+|@[0-9]+;)\Z")
L0 = re.compile(r"^<(f[0-9]+[rv])\.(\d+),([@*+]L0)>\s+(\S+)\s*$")
CC = re.compile(r"^<(f[0-9]+[rv])\.(\d+),\+Cc>\s*(.*)$")
LEFT49 = re.compile(r"^<f49v\.(\d+),([@*]L0)>\s+(\S+)\s*$")

def train_sequences(text):
    line = next(s for s in text.splitlines() if s.startswith("<f57v.3,+Cc>"))
    body = re.sub(r"^<f57v\.3,\+Cc>\s*<![^>]*>", "", line).strip()
    ring = body.split(".")
    if ring[-1] == "":
        ring.pop()
    margin = []
    for line in text.splitlines():
        m = LEFT49.match(line)
        if m:
            margin.append(m[3])
    if len(ring) != 68 or len(margin) != 26:
        raise ValueError("Original training witness no longer matches 68/26 units")
    if any(ring[i] != "o" for i in (0,17,34,51)):
        raise ValueError("Training ring boundaries differ")
    return ring, margin

def eligible_targets(text):
    lines = text.splitlines()
    result=[]
    for folio in FOLIOS:
        left=[]
        circles=[]
        for line in lines:
            m=L0.fullmatch(line)
            if m and m[1]==folio and SYMBOL.fullmatch(m[4]):
                left.append((int(m[2]), m[4]))
            m=CC.fullmatch(line)
            if m and m[1]==folio:
                body=re.sub(r"^<![^>]*>", "", m[3]).strip()
                arr=body.split(".")
                if arr and arr[-1]=="":
                    arr.pop()
                if len(arr)>=12 and all(SYMBOL.fullmatch(s) for s in arr):
                    circles.append((int(m[2]),arr))
        left.sort()
        left_unique=len({n for n,_ in left})==len(left)
        chosen=None
        if left_unique and len(left)>=12:
            chosen={"folio":folio,"type":"L0","n":len(left),"loci":[n for n,_ in left],"units":[x for _,x in left]}
        elif circles:
            i,a=min(circles,key=lambda x:x[0])
            chosen={"folio":folio,"type":"Cc","n":len(a),"loci":[i],"units":a}
        result.append({"folio":folio,"L0_valid_count":len(left),"L0_line_numbers_unique":left_unique,"Cc_eligible_count":len(circles),"chosen":chosen})
        if chosen:
            break
    return result

def motif_train(margin):
    first=margin[:14]
    cand=[]
    for width in range(3,9):
        for i in range(len(first)-width+1):
            for j in range(i+width,len(first)-width+1):
                a=first[i:i+width]
                b=first[j:j+width]
                mismatches=sum(x!=y for x,y in zip(a,b))
                if a[0]==b[0] and mismatches<=1:
                    cand.append((width,-mismatches,j,i))
    if not cand:
        raise ValueError("No qualifying training-only motif")
    width,negerr,j,i=max(cand)
    return first[j:j+width],{"length":width,"train_pair_positions_1based":[i+1,j+1],"train_mismatches":-negerr}

def copy_previous(t):
    return [None]+t[:-1]

def exact_fixed_score(pred,target,mode,seed,n=10000):
    rng=random.Random(seed)
    hits=sum(x==y for x,y in zip(pred,target))
    samples=list(target)
    vals=[]
    for _ in range(n):
        rng.shuffle(samples)
        vals.append(sum(x==y for x,y in zip(pred,samples)))
    return {"hits":hits,"null_draws":n,"null_mean":sum(vals)/n,
            "null_max":max(vals),"null_exceedances":sum(v>=hits for v in vals),
            "permutation_p":(1+sum(v>=hits for v in vals))/(n+1)}

def evaluate(ring,margin,target):
    n=len(target)
    assert n>=12
    template=ring[17:34]
    r17=[template[i%17] for i in range(n)]
    prev=copy_previous(target)
    training=ring+margin
    counts=Counter(training)
    freq=max(counts.values())
    mode=next(x for x in training if counts[x]==freq)
    constant=[mode]*n
    all17=exact_fixed_score(r17,target,mode,66013)
    r17_common=sum(r17[i]==target[i] for i in range(1,n))
    cp_common=sum(prev[i]==target[i] for i in range(1,n))
    mode_common=sum(constant[i]==target[i] for i in range(1,n))
    gate=(r17_common/(n-1)>=.70 and r17_common>=cp_common+3 and
          r17_common>=mode_common+3 and all17["permutation_p"]<=.05)
    m5,metainfo=motif_train(margin)
    seen=set()
    anchor_indices=[]
    forecasts={}
    for h in range(0,n-len(m5)+1):
        if target[h]!=m5[0]:
            continue
        anchor_indices.append(h)
        for j in range(1,len(m5)):
            dest=h+j
            if dest not in seen:
                seen.add(dest)
                forecasts[dest]=m5[j]
    mhits=sum(target[i]==v for i,v in forecasts.items())
    mcopy=sum(prev[i]==target[i] for i in forecasts)
    anchors=set(anchor_indices)
    pool_indexes=[i for i in range(n) if i not in anchors]
    pool=[target[i] for i in pool_indexes]
    rng=random.Random(66014)
    vals=[]
    for _ in range(10000):
        rng.shuffle(pool)
        shuffled=dict(zip(pool_indexes,pool))
        vals.append(sum(shuffled.get(i,target[i])==v for i,v in forecasts.items()))
    p=(1+sum(v>=mhits for v in vals))/10001
    supported=(len(forecasts)>=8 and mhits/len(forecasts)>=.75 and mhits>=mcopy+2 and p<=.05)
    return {
      "R17":{"n":n,**all17,"common_n":n-1,
             "common_hits":r17_common,"copy_previous_hits":cp_common,
             "global_mode_hits":mode_common,
             "verdict":"R17_TRANSFER_PASS" if gate else "R17_NOT_SUPPORTED"},
      "M5":{"motif_training":metainfo,"anchors_observed":len(anchor_indices),
            "forecast_positions":len(forecasts),"correct":mhits,
            "copy_previous_correct_on_same_positions":mcopy,
            "null_draws":10000,"null_mean":sum(vals)/10000,"null_max":max(vals),
            "null_exceedances":sum(v>=mhits for v in vals),
            "conditional_permutation_p":p,
            "verdict":("M5_NOT_EVALUABLE" if len(forecasts)<8 else
                       "M5_TRANSFER_PASS" if supported else "M5_NOT_SUPPORTED")}
    }

def controls(ring,margin):
    tpl=ring[17:34]
    assert sum(a==b for a,b in zip(tpl*2,tpl*2))==34
    _,meta=motif_train(margin)
    model,_=motif_train(margin)
    synthetic=["zzxx"]+[model[0]]+model[1:]+["zzxx"]+[model[0]]+model[1:]
    result=evaluate_no_null_motif(model,synthetic)
    assert result>=2*(len(model)-1)
    noanchor=["zzxx"]*40
    assert evaluate_no_null_motif(model,noanchor)==0
    return {"synthetic_periodic_copy":"PASS","synthetic_anchor_copy":"PASS","synthetic_noanchor":"PASS"}

def evaluate_no_null_motif(m,t):
    seen=set()
    for h in range(0,len(t)-len(m)+1):
        if t[h]==m[0]:
            seen.update(range(h+1,h+len(m)))
    return len(seen)

def run(path):
    raw=Path(path).read_bytes()
    digest=sha256(raw).hexdigest()
    if digest!=SOURCE_SHA:
        raise ValueError("Unexpected owner source SHA-256: "+digest)
    txt=raw.decode("utf-8-sig")
    ring,margin=train_sequences(txt)
    control=controls(ring,margin)
    inventory=eligible_targets(txt)
    selected=inventory[-1]["chosen"]
    out={
        "protocol_commit":"26a031e396d781c713abc97be993332bb7128e4e",
        "source_sha256":digest,
        "target_preselected":list(FOLIOS),
        "eligibility":[{k:v for k,v in x.items() if k!="chosen"} for x in inventory],
        "synthetic_controls":control,
    }
    if selected is None:
        out["status"]="NO_ELIGIBLE_TARGET"
        out["interpretation"]="Predeclared list form absent; no model fit, score or source-fishing."
    else:
        out["status"]="SCORED"
        out["selected"]={k:v for k,v in selected.items() if k!="units"}
        out["predictions"]=evaluate(ring,margin,selected["units"])
    return out

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True)
    args=parser.parse_args()
    print(json.dumps(run(args.input),sort_keys=True,indent=2))

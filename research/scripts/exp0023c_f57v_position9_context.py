#!/usr/bin/env python3
"""EXP-0023C: descriptive f/p alternatives and folio-heldout context.

No meanings, cipher mappings, fonts or transcript bytes distributed.
Exactly input SHA-pinned ZL3b-n v3b; Python 3 stdlib only.
Retrospective exploratory test, NOT a blind source preregistration.
"""
import argparse
from collections import Counter,defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
import random
import re

SOURCE="bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc"
LINE=re.compile(r"^<(f\d+[rv](?:\d+)?)\.(\d+),([^>]+)>\s*(.*)$")

def fold(folio):
    return int.from_bytes(sha256((folio+"exp0023c-v1").encode()).digest()[:4],"big")%5

def cosine(a,b):
    dot=sum(v*b.get(k,0) for k,v in a.items())
    na=math.sqrt(sum(v*v for v in a.values()))
    nb=math.sqrt(sum(v*v for v in b.values()))
    return dot/(na*nb) if na and nb else None

def run(path):
    raw=Path(path).read_bytes()
    digest=sha256(raw).hexdigest()
    if digest!=SOURCE:raise ValueError("Owner-pinned ZL3b-n v3b digest differs: "+digest)
    txt=raw.decode("utf-8-sig")
    ringline=next(x for x in txt.splitlines() if x.startswith("<f57v.3,+Cc>"))
    ringbody=re.sub(r"^<f57v\.3,\+Cc>\s*<![^>]*>","",ringline).strip(". ")
    sequence=ringbody.split(".")
    if len(sequence)!=68:raise ValueError("Not 68 editorial ring units")
    cycles=[sequence[k*17:(k+1)*17] for k in range(4)]
    variants=[dict(slot=i+1,values=[c[i] for c in cycles]) for i in range(17)
              if len({c[i] for c in cycles})>1]
    expected={3:["[d:j]","d","d","d"],9:["f","f","p","p"],16:["I","c","c","c"]}
    if {x["slot"]:x["values"] for x in variants}!=expected:
        raise ValueError("Unexpected source ring or editorial ambiguity")
    allwords=[]
    observations=[]
    contexts=defaultdict(Counter)
    byfolio=defaultdict(Counter)
    for row in txt.splitlines():
        m=LINE.match(row)
        if not m or not m[3].endswith("P0") or m[1] in ("f57v","f49v","f66r"):
            continue
        body=re.sub(r"<!.*?>","",m[4]).replace("<%>","").replace("<$>","").replace("<->",".")
        for word in re.split(r"[.\s]+",body):
            if "," in word or not re.fullmatch(r"[a-z]{2,}",word):
                continue
            allwords.append(word)
            for j,ch in enumerate(word):
                if ch not in ("f","p","t","k"):continue
                left=word[j-1] if j else "^"
                right=word[j+1] if j+1<len(word) else "$"
                pos="initial" if j==0 else "final" if j+1==len(word) else "internal"
                contexts[ch][(left,right)]+=1
                byfolio[m[1]][ch]+=1
                if ch in ("f","p"):
                    observations.append((m[1],int(ch=="p"),pos,left,right))
    wordtypes=Counter(allwords)
    substitution={}
    for a,b in (("f","p"),("k","t"),("f","k"),("p","t")):
        pairs=set()
        for word in wordtypes:
            for j,char in enumerate(word):
                if char==a and word[:j]+b+word[j+1:] in wordtypes:
                    pairs.add((word,word[:j]+b+word[j+1:]))
        substitution[a+"/"+b]=len(pairs)
    folds=[]
    by_folio_loss=defaultdict(lambda:[0,0.0,0.0])
    for f in range(5):
        train=[x for x in observations if fold(x[0])!=f]
        test=[x for x in observations if fold(x[0])==f]
        prior=(sum(y for _,y,_,_,_ in train)+0.5)/(len(train)+1)
        bypos=defaultdict(lambda:[0,0])
        byctx=defaultdict(lambda:[0,0])
        for folio,y,pos,left,right in train:
            bypos[pos][0]+=y;bypos[pos][1]+=1
            byctx[(pos,left,right)][0]+=y;byctx[(pos,left,right)][1]+=1
        gain=0.0;conditional=0.0;positiongain=0.0
        for folio,y,pos,left,right in test:
            a,b=bypos[pos]
            pp=(a+20*prior)/(b+20)
            a,b=byctx[(pos,left,right)]
            pc=(a+20*pp)/(b+20)
            log=lambda p:math.log(p if y else 1-p)
            g=log(pc)-log(prior)
            h=log(pc)-log(pp)
            gain+=g;conditional+=h;positiongain+=log(pp)-log(prior)
            bucket=by_folio_loss[folio]
            bucket[0]+=1;bucket[1]+=g;bucket[2]+=h
        folds.append(dict(fold=f,heldout=len(test),
            context_minus_global_nats=gain/len(test),
            context_minus_position_nats=conditional/len(test),
            position_minus_global_nats=positiongain/len(test)))
    N=sum(x["heldout"] for x in folds)
    bs=[]
    r=random.Random(57009)
    vals=list(by_folio_loss.values())
    for _ in range(2000):
        sample=[vals[r.randrange(len(vals))] for _ in vals]
        bs.append((sum(x[1] for x in sample)/sum(x[0] for x in sample),
                   sum(x[2] for x in sample)/sum(x[0] for x in sample)))
    a=sorted(x[0] for x in bs)
    b=sorted(x[1] for x in bs)
    counts=Counter({"f":sum(v["f"] for v in byfolio.values()),"p":sum(v["p"] for v in byfolio.values())})
    return {
      "version":"EXP-0023C-2026-11-13","source_sha256":digest,
      "status":"EXPLORATORY_RETROSPECTIVE_IVTFF_ONLY",
      "ring_4x17_variants":variants,
      "adjacent_quadrant_agreement":{str(k+1)+"-"+str(k+2):sum(u==v for u,v in zip(cycles[k],cycles[k+1])) for k in range(3)},
      "p0_words_excluding_special_folios":len(allwords),
      "f_p_instances":len(observations),
      "folios_with_f_p":len(set(x[0] for x in observations)),
      "folios_with_both_f_p":sum(v["f"]>0 and v["p"]>0 for v in byfolio.values()),
      "glyph_counts":dict(counts),
      "substitution_word_type_pairs":substitution,
      "pair_context_cosine":{a+"/"+b:cosine(contexts[a],contexts[b]) for a,b in (("f","p"),("k","t"),("f","k"),("p","t"))},
      "fixed_fivefold_cv":folds,
      "cv_weighted_context_vs_global":sum(x["context_minus_global_nats"]*x["heldout"] for x in folds)/N,
      "cv_weighted_context_vs_position":sum(x["context_minus_position_nats"]*x["heldout"] for x in folds)/N,
      "folio_bootstrap_draws":2000,
      "folio_bootstrap_95_context_vs_global":[a[49],a[1949]],
      "folio_bootstrap_95_context_vs_position":[b[49],b[1949]],
      "note":"Context similarity supports structural f/p relation, does NOT identify its semantic or cryptographic role; null CI includes 0."
    }

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    args=ap.parse_args()
    print(json.dumps(run(args.input),indent=2,sort_keys=True))

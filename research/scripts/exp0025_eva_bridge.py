#!/usr/bin/env python3
"""EXP-0025 pre-registered within-word EVA bridge prediction; Python stdlib only."""
import argparse
import collections as co
import hashlib
import json
import math
import random
import re

SHA="bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc"
ABC="abcdefghijklmnopqrstuvwxyz"
LINE=re.compile(r"^<(f[0-9]+[rv][0-9]?)\.([0-9]+),([^>]*)>\s*(.*)$")
TAG=re.compile(r"<[^>]*>")
VALID=re.compile(r"[a-z]{4,}")

def h(s):
    return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8],"big")

def held(f):
    return h("EXP0025-split-v1|"+f)%5==0

def slot(i,n):
    return "NEAR_START" if i==1 else ("NEAR_END" if i==n-2 else "MIDDLE")

def read(data):
    assert hashlib.sha256(data).hexdigest()==SHA,"wrong source bytes"
    text=data.decode("ascii")
    assert text.startswith("#=IVTFF Eva- 2.0 M 5\n")
    assert "# Version 3b of 13/05/2025" in text[:220]
    pages=co.defaultdict(list); counts=co.Counter()
    for line in text.splitlines():
        m=LINE.match(line)
        if not m: continue
        folio,num,kind,body=m.groups()
        if re.search(r"P0\b",kind) is None: continue
        counts["p0_loci"]+=1
        body=TAG.sub(".",body.replace("<->",".").replace("<~>","."))
        for ordinal,t in enumerate(body.split(".")):
            if not t: continue
            counts["candidate_segments"]+=1
            if not VALID.fullmatch(t):
                counts["rejected_segments"]+=1; continue
            pages[folio].append((num,ordinal,t))
            counts["accepted_tokens"]+=1
    return dict(pages),dict(counts)

class Model:
    def __init__(self,train,pages):
        self.zero=co.Counter();self.left=co.Counter();self.nl=co.Counter()
        self.pair=co.Counter();self.npair=co.Counter()
        self.triple=co.Counter();self.ntriple=co.Counter()
        self.lex=co.Counter();self.nlex=co.Counter();self.cache={}
        for l,x,r,s in train:
            self.zero[x]+=1;self.left[l,x]+=1;self.nl[l]+=1
            self.pair[l,r,x]+=1;self.npair[l,r]+=1
            self.triple[l,r,s,x]+=1;self.ntriple[l,r,s]+=1
        self.N=sum(self.zero.values())
        for f,items in pages.items():
            if held(f):continue
            for _,_,w in items:
                for i in range(1,len(w)-1):
                    key=w[:i]+"_"+w[i+1:]
                    self.lex[key,w[i]]+=1;self.nlex[key]+=1
    def probs(self,l,r,s,key):
        k=(l,r,s,key)
        if k in self.cache:return self.cache[k]
        p0=[(self.zero[x]+.5)/(self.N+13) for x in ABC]
        p1=[(self.left[l,x]+10*p0[j])/(self.nl[l]+10) for j,x in enumerate(ABC)]
        p2=[(self.pair[l,r,x]+15*p1[j])/(self.npair[l,r]+15) for j,x in enumerate(ABC)]
        p3=[(self.triple[l,r,s,x]+30*p2[j])/(self.ntriple[l,r,s]+30) for j,x in enumerate(ABC)]
        p4=[(self.lex[key,x]+5*p1[j])/(self.nlex[key]+5) for j,x in enumerate(ABC)]
        self.cache[k]=(p0,p1,p2,p3,p4)
        return self.cache[k]

def controls():
    out={}
    for trial in ("positive","negative"):
        rng=random.Random(250125 if trial=="positive" else 250126)
        train=[];test=[]
        for n in range(15000):
            l=rng.choice("abcd");r=rng.choice("wxyz")
            target=("abcd"[(ord(l)-97+ord(r)-119)%4]
                    if trial=="positive" else l)
            x=target if rng.random()<.9 else rng.choice("abcd")
            (test if n%5==0 else train).append((l,x,r,"MIDDLE"))
        model=Model(train,{})
        gain=sum(math.log(model.probs(l,r,s,"_")[2][ord(x)-97]/
                          model.probs(l,r,s,"_")[1][ord(x)-97]) for l,x,r,s in test)/len(test)
        out[trial+"_gain"]=gain
        if trial=="positive":assert gain>.12
        else:assert gain<.04
    out["passed"]=True
    return out

def top(p):
    return ABC[max(range(26),key=lambda j:(p[j],-j))]

def evaluate(pages):
    train=[];test=[];vocab=set()
    for f in sorted(pages):
        for line,ordinal,w in pages[f]:
            if held(f):
                i=1+h("EXP0025-mask-v1|"+f+"|"+line+"|"+str(ordinal))%(len(w)-2)
                test.append((f,w,i,w[i-1],w[i],w[i+1],slot(i,len(w))))
            else:
                vocab.add(w)
                for i in range(1,len(w)-1):
                    train.append((w[i-1],w[i],w[i+1],slot(i,len(w))))
    model=Model(train,pages)
    rows=[]
    for f,w,i,l,x,r,s in test:
        key=w[:i]+"_"+w[i+1:]
        probs=model.probs(l,r,s,key)
        idx=ord(x)-97
        rows.append({"folio":f,"l":l,"r":r,"s":s,"x":x,"oov":w not in vocab,
                     "lp":[math.log(p[idx]) for p in probs],
                     "guess":[top(p) for p in probs]})
    def summary(sub):
        if not sub:return {"n":0}
        n=len(sub)
        av=[sum(z["lp"][i] for z in sub)/n for i in range(5)]
        acc=[sum(z["guess"][i]==z["x"] for z in sub)/n for i in range(5)]
        labels=("P0","B1_LEFT","M2_BRIDGE","M3_SLOT","B4_COPY")
        return {"n":n,"folios":len({z["folio"] for z in sub}),
                "mean_loglikelihood":dict(zip(labels,av)),
                "top1_accuracy":dict(zip(labels,acc)),
                "bridge_gain_over_left_nats":av[2]-av[1],
                "bridge_gain_over_copy_nats":av[2]-av[4],
                "bridge_top1_lift_pp":100*(acc[2]-acc[1]),
                "bridge_vs_copy_top1_lift_pp":100*(acc[2]-acc[4])}
    oov=[z for z in rows if z["oov"]]
    per_folio=co.defaultdict(list)
    for z in oov:per_folio[z["folio"]].append(z["lp"][2]-z["lp"][1])
    rng=random.Random(250125)
    fs=sorted(per_folio); bootstrap=[]
    if fs:
        for _ in range(400):
            blocks=[per_folio[fs[rng.randrange(len(fs))]] for i in range(len(fs))]
            bootstrap.append(sum(sum(b) for b in blocks)/sum(map(len,blocks)))
    bootstrap.sort()
    strata=co.defaultdict(list)
    for j,z in enumerate(oov):strata[z["folio"],z["l"],z["s"]].append(j)
    movable=sum(len(a) for a in strata.values() if len(a)>1)
    observed=sum(z["lp"][2]-z["lp"][1] for z in oov)/len(oov) if oov else None
    nulls=[]
    for _ in range(199):
        rights=[z["r"] for z in oov]
        for group in strata.values():
            if len(group)>1:
                vals=[rights[j] for j in group];rng.shuffle(vals)
                for j,v in zip(group,vals):rights[j]=v
        delta=0
        for z,new_r in zip(oov,rights):
            j=ord(z["x"])-97
            a=model.probs(z["l"],new_r,z["s"],"_")
            b=model.probs(z["l"],z["r"],z["s"],"_")
            delta+=math.log(a[2][j])-math.log(b[1][j])
        nulls.append(delta/len(oov))
    exceed=sum(v>=observed for v in nulls) if observed is not None else None
    p=(1+exceed)/200 if exceed is not None else None
    rules=[]
    for (l,r),n in model.npair.items():
        if n<80:continue
        count,x=sorted(((model.pair[l,r,g],g) for g in ABC),key=lambda e:(-e[0],e[1]))[0]
        majority=count/n
        if majority<.65:continue
        p1=model.probs(l,r,"MIDDLE","_")[1][ord(x)-97]
        rules.append((-n*(majority-p1),l,r,x,n,majority))
    rules.sort()
    selected_rules=[]
    for _,l,r,x,n,majority in rules[:8]:
        cases=[z for z in oov if z["l"]==l and z["r"]==r]
        selected_rules.append({"rule":l+"_ "+r+" -> "+x,
                               "train_count":n,"train_majority_share":majority,
                               "heldout_oov_count":len(cases),
                               "heldout_oov_precision":sum(z["x"]==x for z in cases)/len(cases) if cases else None,
                               "left_model_top1_precision_on_same_rows":sum(z["guess"][1]==z["x"] for z in cases)/len(cases) if cases else None})
    move_frac=movable/len(oov) if oov else 0
    gates={"enough_oov_folios_and_movable_contexts":len(oov)>=100 and len(fs)>=5 and move_frac>=.5,
           "gain_ge_0p020":observed is not None and observed>=.020,
           "folio_bootstrap_lower_gt_zero":bool(bootstrap and bootstrap[9]>0),
           "permutation_p_le_0p01":p is not None and p<=.01}
    return {"experiment":"EXP-0025","source_sha256":SHA,
            "train_folios":sum(not held(f) for f in pages),
            "heldout_folios":sum(held(f) for f in pages),
            "test_folio_ids":sorted(f for f in pages if held(f)),
            "n_train_interior_positions":len(train),"train_wordtypes":len(vocab),
            "test_accepted_words":len(test),"all_test":summary(rows),"oov_test":summary(oov),
            "oov_bootstrap_95_percentile":[bootstrap[9],bootstrap[389]] if bootstrap else None,
            "oov_null":{"n_draws":199,"movable_fraction":move_frac,
                        "mean":sum(nulls)/len(nulls),"max":max(nulls),
                        "n_exceed":exceed,"p_one_sided":p},
            "prespecified_gates":gates,"passes_all":all(gates.values()),
            "train_only_rules":selected_rules}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input")
    ap.add_argument("--output")
    ap.add_argument("--selftest",action="store_true")
    args=ap.parse_args()
    sanity=controls()
    if args.selftest:
        print(json.dumps(sanity,indent=2));return
    if not args.input or not args.output:
        ap.error("--input and --output required")
    from pathlib import Path
    pages,counts=read(Path(args.input).read_bytes())
    result=evaluate(pages)
    result["parser_counts"]=counts;result["synthetic_controls"]=sanity
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True,indent=2))

if __name__=="__main__":
    main()

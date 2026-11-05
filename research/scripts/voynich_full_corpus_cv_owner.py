#!/usr/bin/env python3
"""Whole-transcription, folio-held-out baseline comparison.
No claim of reproducing VGM-377's exact tokenization or folds.
Python 3.9+, standard library only.
"""
import argparse, collections, hashlib, json, math, random, re, urllib.request
from pathlib import Path

URL = "https://www.voynich.nu/data/ZL3b-n.txt"
CLASSES = ("OTHER", "EDY", "OL", "ORY")
ALPHA = 0.5
HEADER = re.compile(r"^<(?P<folio>f\d+[rv]\d?)>\s")
LINE = re.compile(r"^<(?P<folio>f\d+[rv]\d?)\.(?P<num>\d+),[^>]*>\s*(?P<body>.*)$")

def klass(token):
    for suffix, category in (("ory","ORY"),("edy","EDY"),("ol","OL")):
        if token.endswith(suffix):
            return category
    return "OTHER"

def clean_body(body):
    # Strip IVTFF comments/metadata; uncertain and alternate glyphs are
    # excluded by conservative token acceptance below.
    body = re.sub(r"<!.*?>", "", body)
    body = body.replace("<%>", "").replace("<$>", "")
    return body

def parse_tokens(body, policy):
    body=clean_body(body)
    out=[]
    for chunk in re.split(r"\.|<->",body):
        chunks=[chunk]
        if "," in chunk:
            if policy=="exclude":
                continue
            if policy=="join":
                chunks=[chunk.replace(",","")]
            elif policy=="split":
                chunks=chunk.split(",")
        for token in chunks:
            if re.fullmatch(r"[a-z]+",token):
                out.append(klass(token))
    return out

def load(text, policy):
    folios=collections.defaultdict(list)
    skipped=0
    matched=0
    for row in text.splitlines():
        m=LINE.match(row)
        if not m:
            continue
        matched+=1
        tokens=parse_tokens(m["body"],policy)
        if not tokens: skipped+=1
        folios[m["folio"]].append(tokens)
    return dict(folios),matched,skipped

def model(train):
    uni=collections.Counter()
    bi=collections.Counter()
    prev=collections.Counter()
    for lines in train.values():
        for line in lines:
            uni.update(line)
            bi.update(zip(line,line[1:]))
            prev.update(a for a,b in zip(line,line[1:]))
    return uni,bi,prev

def losses(test, fitted):
    uni,bi,prev=fitted
    total=sum(uni.values())
    u=m=n=0.0
    for line in test:
        for a,b in zip(line,line[1:]):
            u-=math.log((uni[b]+ALPHA)/(total+4*ALPHA))
            m-=math.log((bi[a,b]+ALPHA)/(prev[a]+4*ALPHA))
            n+=1
    return u,m,n

def evaluate(folios,seed,folds):
    keys=sorted(folios)
    rng=random.Random(seed)
    rng.shuffle(keys)
    groups=[keys[i::folds] for i in range(folds)]
    results=[]
    for i,held in enumerate(groups):
        heldset=set(held)
        training={k:v for k,v in folios.items() if k not in heldset}
        fitted=model(training)
        u=m=n=0.0
        for k in held:
            a,b,c=losses(folios[k],fitted)
            u+=a;m+=b;n+=c
        if n:
            results.append({"fold":i+1,"held_out_folios":len(held),"transitions":n,
                            "unigram_loss":u/n,"markov_loss":m/n,
                            "markov_advantage_nats":(u-m)/n})
    N=sum(x["transitions"] for x in results)
    U=sum(x["unigram_loss"]*x["transitions"] for x in results)/N
    M=sum(x["markov_loss"]*x["transitions"] for x in results)/N
    return {"folios":len(folios),"lines":sum(map(len,folios.values())),
            "tokens":sum(len(s) for v in folios.values() for s in v),
            "transitions":N,"unigram_loss":U,"markov_loss":M,
            "markov_advantage_nats":U-M,"folds":results}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,help="Local ZL3b-n.txt (preferred for reproducibility)")
    parser.add_argument("--download",action="store_true",help="Fetch origin file and save alongside output")
    parser.add_argument("--output",type=Path,default=Path("voynich_full_corpus_results.json"))
    parser.add_argument("--seed",type=int,default=377)
    parser.add_argument("--folds",type=int,default=5)
    args=parser.parse_args()
    if args.input:
        data=args.input.read_bytes()
    elif args.download:
        with urllib.request.urlopen(URL,timeout=30) as response:
            data=response.read()
        Path("ZL3b-n.txt").write_bytes(data)
    else:
        parser.error("Provide --input ZL3b-n.txt or --download")
    text=data.decode("utf-8-sig")
    if not text.startswith("#=IVTFF") or "Version 3b" not in text[:300]:
        raise ValueError("Unexpected transcription header/version; refusing to score")
    out={"source":URL,"sha256":hashlib.sha256(data).hexdigest(),
         "version_header":text.splitlines()[:3],"seed":args.seed,
         "alpha":ALPHA,"folds":args.folds,"policy_results":{}}
    for policy in ("exclude","join","split"):
        folios,matched,skipped=load(text,policy)
        out["policy_results"][policy]={
            "matched_transcription_lines":matched,
            "lines_with_no_accepted_tokens":skipped,
            **evaluate(folios,args.seed,args.folds)}
    args.output.write_text(json.dumps(out,indent=2),encoding="utf-8")
    print(json.dumps(out,indent=2))
if __name__=="__main__":
    main()

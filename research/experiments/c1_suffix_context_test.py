#!/usr/bin/env python3
"""Prefix-controlled, folio-heldout suffix/context test for C1 (stdlib only).

Designed and preregistered before any new suffix/context analysis. Neither a
Voynich translation nor an execution of another author's decoder.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import re
import sys
from c1_context_model import extract_ivtff

SOURCE_SHA = 'bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'
LABELS = ('DY','EY','OL','IN','OTHER')
SEED = 131126

def suffix_label(word):
    for ending in LABELS[:4]:
        if word.endswith(ending.lower()):
            return ending
    return 'OTHER'

def fold(folio):
    raw = hashlib.sha256((folio + 'C1suffix-v1').encode('utf-8')).digest()
    return int.from_bytes(raw, 'big') % 5

def words_to_records(lines, folio):
    records = []
    for line in lines:
        for j,word in enumerate(line):
            if len(word) < 4 or len(line) < 2:
                continue
            lb = 0 if len(word)<=4 else (1 if len(word)<=6 else 2)
            position = 'first' if j == 0 else ('last' if j == len(line)-1 else 'middle')
            prev = suffix_label(line[j-1]) if j > 0 else 'BOUNDARY'
            nxt = suffix_label(line[j+1]) if j+1 < len(line) else 'BOUNDARY'
            records.append((folio,word[:3],lb,position,prev,nxt,suffix_label(word)))
    return records

def build_corpus(path):
    raw = Path(path).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != SOURCE_SHA:
        raise ValueError('Unexpected source checksum: '+sha)
    txt = raw.decode('utf-8')
    if not (txt.startswith('#=IVTFF Eva- 2.0') and 'Version 3b of 13/05/2025' in txt[:300]):
        raise ValueError('Unexpected IVTFF header')
    folios = sorted(set(re.findall(r'^<(f\d+[rv](?:\d+)?)\.\d+,[^>]*>',txt,re.M)))
    records = []
    by_fold = [0]*5
    nonempty_lines = 0
    for folio in folios:
        lines = extract_ivtff(txt, folio)
        nonempty_lines += len(lines)
        rows = words_to_records(lines,folio)
        records.extend(rows)
        by_fold[fold(folio)]+=len(rows)
    return records,{'source_sha256':sha,'folio_identifiers':len(folios),
                    'parsed_nonempty_lines':nonempty_lines,
                    'eligible_tokens':len(records),'fold_eligible_counts':by_fold}

def mkmodel(training):
    global_counts=Counter(); pcounts=defaultdict(Counter)
    bcounts=defaultdict(Counter); ccounts=defaultdict(Counter)
    for _folio,prefix,lb,pos,prev,nxt,y in training:
        b=(prefix,lb,pos)
        c=(prefix,lb,pos,prev,nxt)
        global_counts[y]+=1; pcounts[prefix][y]+=1
        bcounts[b][y]+=1; ccounts[c][y]+=1
    n=sum(global_counts.values())
    glob={y:(global_counts[y]+0.5)/(n+2.5) for y in LABELS}
    p_cache={}
    b_cache={}
    c_cache={}
    def pb(prefix):
        if prefix not in p_cache:
            d=pcounts[prefix];tot=sum(d.values())
            p_cache[prefix]={y:(d[y]+20*glob[y])/(tot+20) for y in LABELS}
        return p_cache[prefix]
    def baseline(prefix,lb,pos):
        key=(prefix,lb,pos)
        if key not in b_cache:
            d=bcounts[key];tot=sum(d.values());prior=pb(prefix)
            b_cache[key]={y:(d[y]+20*prior[y])/(tot+20) for y in LABELS}
        return b_cache[key]
    def contextual(prefix,lb,pos,prev,nxt):
        key=(prefix,lb,pos,prev,nxt)
        if key not in c_cache:
            d=ccounts[key];tot=sum(d.values());prior=baseline(prefix,lb,pos)
            c_cache[key]={y:(d[y]+30*prior[y])/(tot+30) for y in LABELS}
        return c_cache[key]
    return baseline,contextual

def evaluate(rows, do_shuffle=False, num_shuffles=199, seed=SEED, bootstrap=500, bseed=131127):
    obs_by_folio=defaultdict(lambda:[0.0,0])
    folds=[]; scored=[]; null_cache=[]
    for k in range(5):
        train=[row for row in rows if fold(row[0])!=k]
        test=[row for row in rows if fold(row[0])==k]
        base,context=mkmodel(train)
        gains=[]
        for row in test:
            folio,prefix,lb,pos,prev,nxt,y = row
            gain=math.log(context(prefix,lb,pos,prev,nxt)[y] / base(prefix,lb,pos)[y])
            obs_by_folio[folio][0] += gain
            obs_by_folio[folio][1] += 1
            gains.append(gain)
        folds.append({'fold':k,'train_n':len(train),'heldout_n':len(test),
                      'gain_nats_token':sum(gains)/len(gains) if gains else None})
        if do_shuffle:
            baselog=[]
            for row in test:
                _,prefix,lb,pos,prev,nxt,y=row
                baselog.append(math.log(base(prefix,lb,pos)[y]))
            groups=defaultdict(list)
            for i,row in enumerate(test):
                f,prefix,lb,pos,prev,nxt,y=row
                groups[(f,lb,pos)].append(i)
            null_cache.append((test,context,baselog,groups))
    total=sum(x[1] for x in obs_by_folio.values())
    gain=sum(x[0] for x in obs_by_folio.values())/total
    rng=random.Random(bseed)
    folios=sorted(obs_by_folio)
    bootstrap_vals=[]
    for _ in range(bootstrap):
        draw=[obs_by_folio[folios[rng.randrange(len(folios))]] for i in range(len(folios))]
        bootstrap_vals.append(sum(a for a,n in draw)/sum(n for a,n in draw))
    bootstrap_vals.sort()
    result={'n':total,'folios':len(folios),'heldout_gain_nats_per_token':gain,
            'folds':folds,'bootstrap_n':bootstrap,
            'bootstrap_95pct':[bootstrap_vals[int(.025*(bootstrap-1))],bootstrap_vals[int(.975*(bootstrap-1))]]}
    if do_shuffle:
        rng=random.Random(seed)
        null_vals=[]
        mobile_count=0
        for test,context,baselog,groups in null_cache:
            mobile_count+=sum(len(v) for v in groups.values() if len(v)>1)
        for rep in range(num_shuffles):
            score=0.0;n=0
            for test,context,baselog,groups in null_cache:
                perm=list(range(len(test)))
                for members in groups.values():
                    copy=members.copy();rng.shuffle(copy)
                    for i,source_i in zip(members,copy):
                        perm[i]=source_i
                for i,row in enumerate(test):
                    folio,prefix,lb,pos,prev,nxt,y=row
                    cctx=test[perm[i]]
                    score+=math.log(context(prefix,lb,pos,cctx[4],cctx[5])[y])-baselog[i]
                    n+=1
            null_vals.append(score/n)
        null_vals.sort()
        result['negative_null']={'seed':seed,'num_shuffles':num_shuffles,
                                 'mobile_context_targets':mobile_count,
                                 'mobile_fraction':mobile_count/total,
                                 'mean':sum(null_vals)/len(null_vals),
                                 'p95':null_vals[int(.95*(len(null_vals)-1))],
                                 'max':null_vals[-1],
                                 'empirical_upper_tail_p':(1+sum(x>=gain for x in null_vals))/(len(null_vals)+1)}
    bmin=result['bootstrap_95pct'][0]
    fpos=sum(x['gain_nats_token']>0 for x in folds)
    p95=(result.get('negative_null') or {}).get('p95',float('-inf'))
    result['prespecified_threshold_pass']=gain>0.01 and fpos>=4 and bmin>0 and gain>p95
    return result

def positive_control():
    rng=random.Random(131128)
    rows=[]
    for f in range(50):
        for i in range(110):
            folio=f'synthetic_{f:03}'
            prefix=f'{rng.randrange(25):03}'
            prev=rng.choice(LABELS)
            nxt=rng.choice(LABELS)
            y='DY' if prev in ('DY','EY') else 'OL'
            if rng.random()<0.10: y='OL' if y=='DY' else 'DY'
            rows.append((folio,prefix,1,'middle',prev,nxt,y))
    r=evaluate(rows,do_shuffle=False,bootstrap=100)
    return {'rows':len(rows),'gain_nats_per_token':r['heldout_gain_nats_per_token'],
            'all_5_folds_positive':all(x['gain_nats_token']>0 for x in r['folds'])}

def self_test():
    assert fold('f1r')==fold('f1r')
    assert suffix_label('qokedy')=='DY'
    assert suffix_label('shol')=='OL'
    assert suffix_label('qokeey')=='EY'
    assert suffix_label('dain')=='IN'
    assert suffix_label('dainx')=='OTHER'
    x=words_to_records([['qokedy','shol','daiin']], 'f1r')
    assert len(x)==3 and x[0][3]=='first' and x[2][3]=='last'
    return {'self_test':'PASS'}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',required=True)
    ap.add_argument('--shuffles',type=int,default=199)
    args=ap.parse_args()
    records,metadata=build_corpus(args.input)
    result={'version':'C1suffix-v1','source':metadata,
            'self_test':self_test(),
            'positive_control':positive_control(),
            'real':evaluate(records,do_shuffle=True,num_shuffles=args.shuffles)}
    print(json.dumps(result,sort_keys=True,indent=2))

if __name__=='__main__':
    main()

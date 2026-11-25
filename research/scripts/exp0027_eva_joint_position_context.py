#!/usr/bin/env python3
"""EXP-0027 frozen exploratory EVA model comparison. Python stdlib only.
Input is Owner-held ZL3b-n v3b SHA-pinned text; no transcript data in output.
Prereg: research/experiments/2026-11-22_EXP-0027_prereg.md.
"""
import hashlib
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SOURCE_SHA='bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'
ROW=re.compile(r'^<(f\d+[rv](?:\d+)?)\.(\d+),([^>]+)>\s*(.*)$')
HEADER=re.compile(r'^<(f\d+[rv](?:\d+)?)>\s*<!([^>]*)>')
META_L=re.compile(r'\$L=([^\s]+)')
CERTAIN=re.compile(r'[a-z]+\Z')
COMMENT=re.compile(r'<![^>]*>')
MARKUP=re.compile(r'<[^>]*>')
TAU=25.0
SEED=20261122
N_SHUFFLES=99
N_BOOT=2000
EPS=1e-12

def root_fold(root):
    return int.from_bytes(hashlib.sha256(('EXP0027-root-v1|'+root).encode('ascii')).digest()[:8],'big')%5

def lbin(n): return 0 if n<=3 else 1 if n<=6 else 2
def nbin(n): return 0 if n<=4 else 1 if n<=8 else 2

def target(token):
    end={'y':0,'n':1,'l':2}.get(token[-1],3)
    return (4 if token.startswith('q') else 0)+end

def parse(data):
    if hashlib.sha256(data).hexdigest()!=SOURCE_SHA: raise ValueError('SOURCE_SHA_MISMATCH')
    src=data.decode('utf-8-sig')
    if not src.startswith('#=IVTFF Eva- 2.0 M 5\n') or 'Version 3b of 13/05/2025' not in src[:200]:
        raise ValueError('UNEXPECTED_SOURCE_HEADER')
    metadata={};count=Counter();rows=[]
    for line in src.splitlines():
        h=HEADER.match(line)
        if h:
            m=META_L.search(h.group(2))
            metadata[h.group(1)]=m.group(1) if m and m.group(1) in ('A','B') else 'U'
    for line in src.splitlines():
        m=ROW.match(line)
        if not m: continue
        folio,number,tag,body=m.groups();count['all_rows']+=1
        if tag!='+P0':count['not_+P0']+=1;continue
        root=re.match(r'^(f\d+)[rv]',folio).group(1)
        if root in ('f3','f8'):count['excluded_f3_f8']+=1;continue
        body=COMMENT.sub('',body).replace('<->','.').replace('<~>','.')
        body=MARKUP.sub('',body)
        words=body.split('.')
        if len(words)<3 or not all(CERTAIN.fullmatch(t) for t in words):
            count['uncertain_or_short_line']+=1;continue
        group=metadata.get(folio,'U')
        rows.append((root,group,tuple((target(t),lbin(len(t))) for t in words)))
        count['accepted_lines']+=1
        count['accepted_tokens']+=len(words)
    if not rows:raise ValueError('EMPTY_ACCEPTED_LINES')
    return rows,dict(count)

def shuffled(rows,rng):
    out=[];possible=0;moved=0
    for root,g,seq in rows:
        v=list(seq)
        for b in (0,1,2):
            idx=[i for i,(cls,lb) in enumerate(v) if lb==b]
            if len(idx)<2:continue
            possible+=len(idx)
            values=[v[i][0] for i in idx]
            rng.shuffle(values)
            for i,val in zip(idx,values):
                if v[i][0]!=val:moved+=1
                v[i]=(val,b)
        out.append((root,g,tuple(v)))
    return out,{'eligible_tokens_in_len_bin_groups_ge2':possible,'changed_target_positions':moved}

def synthetic(rows,kind,seed):
    rng=random.Random(seed);out=[]
    for root,g,seq in rows:
        v=[];prev=None
        for i,(orig,lb) in enumerate(seq):
            if kind=='uniform': cls=rng.randrange(8)
            elif kind=='joint':
                x=rng.random()
                if i==0: cls=0 if x<0.87 else rng.randrange(8)
                elif i==len(seq)-1: cls=7 if x<0.77 else (prev if x<0.92 else rng.randrange(8))
                else: cls=prev if x<0.77 else rng.randrange(8)
            else: raise ValueError(kind)
            v.append((cls,lb));prev=cls
        out.append((root,g,tuple(v)))
    return out

def events(lines):
    for root,g,words in lines:
        linebin=nbin(len(words))
        for i,(cls,lb) in enumerate(words):
            position=0 if i==0 else 2 if i==len(words)-1 else 1
            prev=8 if i==0 else words[i-1][0]
            yield root,g,lb,linebin,position,prev,cls

def train_events(train):
    glob=Counter();gc=defaultdict(Counter);bc=defaultdict(Counter);pc=defaultdict(Counter);cc=defaultdict(Counter);hc=defaultdict(Counter)
    for root,g,lb,ln,pos,prev,cls in events(train):
        base=(g,lb,ln)
        glob[cls]+=1;gc[g][cls]+=1;bc[base][cls]+=1
        pc[(base,pos)][cls]+=1;cc[(base,prev)][cls]+=1;hc[(base,pos,prev)][cls]+=1
    N=sum(glob.values());global_p=tuple((glob[j]+.5)/(N+4.0) for j in range(8))
    cache={}
    def shrink(cnt,par):
        d=sum(cnt.values())+TAU
        return tuple((cnt[i]+TAU*par[i])/d for i in range(8))
    def pred(g,lb,ln,pos,prev):
        k=(g,lb,ln,pos,prev)
        if k not in cache:
            gp=shrink(gc[g],global_p)
            bk=(g,lb,ln);base=shrink(bc[bk],gp)
            pp=shrink(pc[(bk,pos)],base)
            cp=shrink(cc[(bk,prev)],base)
            mix=tuple((pp[j]+cp[j])*.5 for j in range(8))
            hp=shrink(hc[(bk,pos,prev)],mix)
            cache[k]=(base,pp,cp,hp)
        return cache[k]
    return pred

def cv(rows):
    byroot={};folds=[]
    for fold in range(5):
        train=[r for r in rows if root_fold(r[0])!=fold]
        test=[r for r in rows if root_fold(r[0])==fold]
        if not train or not test:raise ValueError('EMPTY_TRAIN_OR_TEST_FOLD')
        pred=train_events(train)
        n=0;losses=[0.0]*4
        for root,g,lb,ln,pos,prev,cls in events(test):
            entry=byroot.setdefault(root,{'group':g,'n':0,'loss':[0.0]*4})
            if entry['group']!=g:entry['group']='U'
            probs=pred(g,lb,ln,pos,prev)
            for j in range(4):
                value=-math.log(max(EPS,probs[j][cls]));entry['loss'][j]+=value;losses[j]+=value
            entry['n']+=1;n+=1
        folds.append({'fold':fold,'train_roots':len(set(r[0] for r in train)),'test_roots':len(set(r[0] for r in test)),
                      'test_lines':len(test),'tokens':n,'nll_nats_per_token':[x/n for x in losses]})
    return byroot,folds

def summary(byroot):
    n=sum(x['n'] for x in byroot.values())
    losses=[sum(x['loss'][j] for x in byroot.values())/n for j in range(4)]
    b,p,c,h=losses
    return {'roots':len(byroot),'tokens':n,'loss_nats_per_token':dict(zip(['B0','P','C','H'],losses)),
            'delta_h_vs_best_single':min(p,c)-h,
            'P_gain_over_B0':b-p,'C_gain_over_B0':b-c,'H_gain_over_B0':b-h}

def strata(byroot):
    return {g:summary({k:v for k,v in byroot.items() if v['group']==g})
            for g in ('A','B','U') if any(v['group']==g for v in byroot.values())}

def bootstrap(byroot):
    roots=list(sorted(byroot));rng=random.Random(SEED+600)
    ds=[]
    for _ in range(N_BOOT):
        sampled=[byroot[roots[rng.randrange(len(roots))]] for __ in roots]
        n=sum(x['n'] for x in sampled)
        p=sum(x['loss'][1] for x in sampled)/n
        c=sum(x['loss'][2] for x in sampled)/n
        h=sum(x['loss'][3] for x in sampled)/n
        ds.append(min(p,c)-h)
    ds.sort()
    def quant(q):
        at=(len(ds)-1)*q;lo=int(at)
        return ds[lo]*(1-(at-lo))+ds[min(lo+1,len(ds)-1)]*(at-lo)
    return [quant(.025),quant(.975)]

def run(data):
    rows,exclusions=parse(data)
    byroot,folds=cv(rows)
    obs=summary(byroot)
    gs=strata(byroot)
    null=[];exchange=[]
    for k in range(N_SHUFFLES):
        rr,diag=shuffled(rows,random.Random(SEED+1000+k))
        db,_=cv(rr)
        null.append(summary(db)['delta_h_vs_best_single'])
        exchange.append(diag)
    upper=(1+sum(d>=obs['delta_h_vs_best_single']-1e-14 for d in null))/(N_SHUFFLES+1)
    syn={}
    for kind,seed in (('joint',SEED+1),('uniform',SEED+2)):
        d,_=cv(synthetic(rows,kind,seed))
        syn[kind]=summary(d)
    status=(obs['delta_h_vs_best_single']>=.005 and all(gs[g]['delta_h_vs_best_single']>0 for g in ('A','B')) and upper<=.05)
    classcounts=Counter(cls for _,_,_,_,_,_,cls in events(rows))
    return {'experiment':'EXP-0027','status':'EXPLORATORY_ALREADY_EXPOSED_SINGLE_EVA_WITNESS',
            'source_sha256':SOURCE_SHA,'source_version':'ZL3b-n IVTFF Eva- 2.0 M 5, v3b 2025-05-13',
            'fixed_models':'B0 group+wordlen+linelen; P adds position; C adds preceding state; H adds both with equal-mixture prior, tau25, global alpha0.5',
            'target':'8 states: ASCII-q initial yes/no x word-final y/n/l/other',
            'data_scope':exclusions,'folio_root_groups':len(set(r[0] for r in rows)),
            'target_state_counts':{str(i):classcounts[i] for i in range(8)},'observed':obs,
            'folds':folds,'currier_metadata_strata':gs,
            'root_cluster_descriptive_bootstrap_95_delta':bootstrap(byroot),
            'null':{'name':'within-line within-wordlength-bin 99 class permutation refits',
                    'iterations':N_SHUFFLES,'delta_min':min(null),'delta_max':max(null),
                    'delta_mean':sum(null)/len(null),
                    'delta_ge_observed':sum(d>=obs['delta_h_vs_best_single']-1e-14 for d in null),
                    'upper_tail_empirical_p':upper,
                    'median_target_positions_changed':sorted(d['changed_target_positions'] for d in exchange)[len(exchange)//2],
                    'median_eligible_targets_to_shuffle':sorted(d['eligible_tokens_in_len_bin_groups_ge2'] for d in exchange)[len(exchange)//2]},
            'synthetic_controls':syn,'preregistered_criterion_passed':status,
            'interpretation_guardrail':'No independent source or physical-leaf heldout. This discriminates conditional class predictors within one exposed editorial EVA witness; cannot identify natural language, cipher, copy-edit generator or hybrid, or validate glyphs/semantics.'}

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: exp0027.py ZL3b-n.txt')
    print(json.dumps(run(Path(sys.argv[1]).read_bytes()),indent=2,sort_keys=True,ensure_ascii=False))

#!/usr/bin/env python3
"""A-05 EXP-0026 exploratory root-cluster sensitivity diagnostic.
Only owner-pinned IVTFF v3b input; Python stdlib; output aggregate-only JSON.
This reuses a prior exposed TEST set: NOT a new prospective confirmation.
"""
import hashlib, json, random, re, sys
from collections import defaultdict
from pathlib import Path
SOURCE_SHA='bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'
ROW=re.compile(r'^<(f\d+[rv](?:\d+)?)\.(\d+),([^>]+)>\s*(.*)$')
ROOT=re.compile(r'^(f\d+)[rv](?:\d+)?$')
CERTAIN=re.compile(r'[a-z]+\Z')
COMMENT=re.compile(r'<![^>]*>')
MARKUP=re.compile(r'<[^>]*>')
HEADER=re.compile(r'^<(f\d+[rv](?:\d+)?)>\s*<!([^>]*)>')
META_L=re.compile(r'\$L=([^\s]+)')
META_H=re.compile(r'\$H=([^\s]+)')
SEED=260521
BOOT_REPS=20000

def is_test(root):
    d=hashlib.sha256(('EXP0026-A05-ROOT-v1|'+root).encode('ascii')).digest()
    return int.from_bytes(d[:8], 'big')%5==0

def tokenize(body):
    body=COMMENT.sub('',body).replace('<->','.').replace('<~>','.')
    body=MARKUP.sub('',body)
    parts=body.split('.')
    if not parts or not CERTAIN.fullmatch(parts[0]):
        return None
    return [t for t in parts if CERTAIN.fullmatch(t)]

def percentile(v,p):
    v=sorted(v);z=(len(v)-1)*p;i=int(z);f=z-i
    return v[i]*(1-f)+v[min(i+1,len(v)-1)]*f

def roots_summary(byroot):
    keys=sorted(byroot,key=lambda x:int(x[1:]))
    vals=[byroot[k] for k in keys]
    n=sum(x['n'] for x in vals);obs=sum(x['o'] for x in vals);exp=sum(x['e'] for x in vals)
    gaps=[x['e']-x['o'] for x in vals]
    pos=sum(x>1e-9 for x in gaps);neg=sum(x< -1e-9 for x in gaps);ties=len(gaps)-pos-neg
    loo=[]
    for k,x in zip(keys,vals):
        loo.append({'root':k,'depletion_pp':100*((exp-x['e'])-(obs-x['o']))/(n-x['n'])})
    r=random.Random(SEED)
    bp=[]
    for _ in range(BOOT_REPS):
        draw=[vals[r.randrange(len(vals))] for __ in vals]
        nn=sum(x['n'] for x in draw)
        bp.append((sum(x['e']-x['o'] for x in draw)/nn)*100)
    return {'roots':len(vals),'n_lines':n,'observed':obs,'expected':exp,
            'depletion_pp':100*(exp-obs)/n,'positive_roots':pos,'negative_roots':neg,'tied_roots':ties,
            'leave_one_root_out_depletion_pp_min':min(x['depletion_pp'] for x in loo),
            'leave_one_root_out_depletion_pp_max':max(x['depletion_pp'] for x in loo),
            'leave_one_root_out_min_at':min(loo,key=lambda x:x['depletion_pp'])['root'],
            'leave_one_root_out_max_at':max(loo,key=lambda x:x['depletion_pp'])['root'],
            'exploratory_root_cluster_bootstrap_percentile_95_pp': [percentile(bp,.025),percentile(bp,.975)],
            'per_root':[{'root':k,'lines':x['n'],'observed':x['o'],'expected':x['e'],
                         'depletion_pp':100*(x['e']-x['o'])/x['n'],
                         'currier_labels':sorted(x['currier']), 'hand_labels':sorted(x['hands'])}
                        for k,x in zip(keys,vals)]}

def run(data):
    if hashlib.sha256(data).hexdigest()!=SOURCE_SHA: raise ValueError('SHA mismatch')
    src=data.decode('utf-8-sig')
    if not src.startswith('#=IVTFF Eva- 2.0 M 5\n') or 'Version 3b of 13/05/2025' not in src[:200]:
        raise ValueError('header mismatch')
    meta={}
    for line in src.splitlines():
        h=HEADER.match(line)
        if h:
            m=META_L.search(h.group(2));hand=META_H.search(h.group(2))
            meta[h.group(1)]=(m.group(1) if m else 'UNKNOWN',hand.group(1) if hand else 'UNKNOWN')
    buckets=defaultdict(lambda:defaultdict(lambda:{'n':0,'o':0,'e':0.0,'currier':set(),'hands':set()}))
    excluded=defaultdict(int)
    for line in src.splitlines():
        m=ROW.match(line)
        if not m:continue
        folio,_,tag,body=m.groups()
        if tag!='+P0':excluded['not_plus_P0']+=1;continue
        root=ROOT.match(folio).group(1)
        if root in ('f3','f8'):excluded['prior_f3_f8_roots']+=1;continue
        tokens=tokenize(body)
        if tokens is None:excluded['ambiguous_first']+=1;continue
        if len(tokens)<2:excluded['single_word']+=1;continue
        x=buckets['test' if is_test(root) else 'train'][root]
        peers=[t for t in tokens if len(t)==len(tokens[0])]
        x['n']+=1;x['o']+=int(tokens[0].startswith('q'));x['e']+=sum(t.startswith('q') for t in peers)/len(peers)
        l,h=meta.get(folio,('UNKNOWN','UNKNOWN'))
        x['currier'].add(l);x['hands'].add(h)
    test=roots_summary(buckets['test']);train=roots_summary(buckets['train'])
    strata={}
    for label in ('A','B','UNKNOWN','MIXED'):
        selected={root:x for root,x in buckets['test'].items() if ((next(iter(x['currier'])) if len(x['currier'])==1 else 'MIXED')==label)}
        if selected:
            result=roots_summary(selected)
            strata[label]={k:v for k,v in result.items() if k!='per_root'}
    assert (test['roots'],test['n_lines'],test['observed'])==(20,677,69)
    assert abs(test['expected']-99.78571428571429)<1e-7
    assert (train['roots'],train['n_lines'],train['observed'])==(76,2429,372)
    assert abs(train['expected']-437.48333333333335)<1e-7
    positive={f'f{i+1}':{'n':10,'o':0,'e':5.,'currier':set(),'hands':set()} for i in range(20)}
    balanced={f'f{i+1}':{'n':10,'o':(4 if i<10 else 6),'e':5.,'currier':set(),'hands':set()} for i in range(20)}
    pos=roots_summary(positive); neg=roots_summary(balanced)
    assert pos['depletion_pp']>0 and pos['positive_roots']==20 and pos['exploratory_root_cluster_bootstrap_percentile_95_pp'][0]>0
    assert abs(neg['depletion_pp'])<1e-10 and neg['positive_roots']==10 and neg['negative_roots']==10
    assert neg['exploratory_root_cluster_bootstrap_percentile_95_pp'][0]<0<neg['exploratory_root_cluster_bootstrap_percentile_95_pp'][1]
    return {'experiment':'EXP-0026','audit':'A05_ROOT_CLUSTER_EXPLORATORY_REUSE','source_sha256':SOURCE_SHA,
      'tested_object':'EVA ASCII q at first certain word of +P0 continuation line',
      'statistic':'(sum linewise same-length q-peer probabilities - observed q-onset)/number of lines, pp',
      'status':'EXPLORATORY_REUSE_NOT_NEW_HELDOUT','controls':{'positive_depletion':'PASS','balanced_null':'PASS'},
      'excluded':dict(excluded),'test':test,'test_currier_strata_descriptive':strata,
      'train_descriptive':{k:v for k,v in train.items() if k!='per_root'},
      'assumptions':'Bootstrap roots treated as exchangeable clusters. Historical physical leaves, section, scribes and other transcript witnesses NOT independently confirmed. Percentile intervals are descriptive; no confirmatory p-value.',
      'sources':'Owner-held local ZL3b-n v3b; unchanged EXP-0026 selection/tokenization; no transcript content emitted.'}

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: script ZL3b-n.txt')
    print(json.dumps(run(Path(sys.argv[1]).read_bytes()),ensure_ascii=False,indent=2,sort_keys=True))

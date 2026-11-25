#!/usr/bin/env python3
"""EXP-0028: deterministic stdlib EVA generative comparison, aggregate-only output.
Pre-run protocol: research/experiments/2026-11-22_EXP-0028_prereg.md
"""
import hashlib, json, math, random, re, string, sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

SHA='bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'
ROW=re.compile(r'^<(f\d+[rv](?:\d+)?)\.(\d+),([^>]+)>\s*(.*)$')
HEADER=re.compile(r'^<(f\d+[rv](?:\d+)?)>\s*<!([^>]*)>')
ML=re.compile(r'\$L=([^\s]+)');COMMENT=re.compile(r'<![^>]*>')
MARKUP=re.compile(r'<[^>]*>');WORD=re.compile(r'[a-z]+\Z')
ABC=string.ascii_lowercase;SEED=282800;TAU=.5

def fold(root):
    return int.from_bytes(hashlib.sha256(('EXP0027-root-v1|'+root).encode()).digest()[:8],'big')%5

def parse(data):
    if len(data)!=411671 or hashlib.sha256(data).hexdigest()!=SHA:raise ValueError('BAD_SOURCE_HASH')
    src=data.decode('utf-8-sig')
    if not src.startswith('#=IVTFF Eva- 2.0 M 5\n') or 'Version 3b of 13/05/2025' not in src[:200]:raise ValueError('BAD_HEADER')
    meta={};stat=Counter();rows=[]
    for l in src.splitlines():
        m=HEADER.match(l)
        if m:
            z=ML.search(m.group(2));meta[m.group(1)]=z.group(1) if z and z.group(1) in ('A','B') else 'U'
    for l in src.splitlines():
        m=ROW.match(l)
        if not m:continue
        folio,number,tag,body=m.groups();stat['all_rows']+=1
        if tag!='+P0':stat['not_+P0']+=1;continue
        root=re.match(r'^(f\d+)[rv]',folio).group(1)
        if root in ('f3','f8'):stat['excluded_f3_f8']+=1;continue
        body=MARKUP.sub('',COMMENT.sub('',body).replace('<->','.').replace('<~>','.'))
        words=body.split('.')
        if len(words)<3 or not all(WORD.fullmatch(w) for w in words):
            stat['uncertain_or_short_line']+=1;continue
        rows.append((root,meta.get(folio,'U'),tuple(words)))
        stat['accepted_lines']+=1;stat['accepted_tokens']+=len(words)
    if (len(rows),stat['accepted_tokens'],len(set(x[0] for x in rows)))!=(1537,12167,94):raise ValueError('EXP27_SCOPE_MISMATCH')
    return rows,dict(stat)

def bigram(lines):
    count=defaultdict(Counter)
    for _,_,words in lines:
        for w in words:
            prev='^'
            for c in w:count[prev][c]+=1;prev=c
            count[prev]['$']+=1
    logp={}
    for prev in '^'+ABC:
        opts=ABC if prev=='^' else ABC+'$'
        z=sum(count[prev].values())+TAU*len(opts)
        logp[prev]={c:math.log((count[prev][c]+TAU)/z) for c in opts}
    cache={}
    def score(w):
        if w not in cache:
            prev='^';v=0.
            for c in w:v+=logp[prev][c];prev=c
            cache[w]=v+logp[prev]['$']
        return cache[w]
    return score

@lru_cache(maxsize=150000)
def edit(prev,w):
    if prev is None:return 0.
    n=len(prev);z=.85 if n==1 else 1.
    if w==prev:return .25/z
    if len(w)==n:
        return (.4/z)/(n*25) if sum(a!=b for a,b in zip(prev,w))==1 else 0.
    if len(w)==n+1:
        paths=sum(prev[:i]+w[i]+prev[i:]==w for i in range(n+1))
        return paths*(.2/z)/((n+1)*26)
    if n>1 and len(w)==n-1:
        paths=sum(prev[:i]+prev[i+1:]==w for i in range(n))
        return paths*.15/n
    return 0.

def edit_control():
    for prev in ('a','ab','aa'):
        n=len(prev);z=.85 if n==1 else 1.;o=Counter();o[prev]+=.25/z
        for i in range(n):
            for c in ABC:
                if c!=prev[i]:o[prev[:i]+c+prev[i+1:]]+=(.4/z)/(n*25)
        for i in range(n+1):
            for c in ABC:o[prev[:i]+c+prev[i:]]+=(.2/z)/((n+1)*26)
        if n>1:
            for i in range(n):o[prev[:i]+prev[i+1:]]+=.15/n
        assert abs(sum(o.values())-1)<1e-11
        for w,p in o.items():assert abs(edit(prev,w)-p)<1e-11
    return 'PASS'

def events(lines,score):
    for root,g,words in lines:
        for i,w in enumerate(words):
            b=score(w)
            if i==0:yield root,g,'FIRST',b,0.
            else:
                e=edit(words[i-1],w)
                ratio=math.exp(math.log(e)-b) if e else 0.
                yield root,g,'LAST' if i==len(words)-1 else 'INTERIOR',b,ratio

def lr(r,lmb):return math.log1p(lmb*(r-1.))

def fit(ev):
    vals=[x[4] for x in ev if x[2]!='FIRST']
    if not vals:return 0.
    n0=sum(x==0. for x in vals);positive=[x for x in vals if x>0.]
    def objective(l):return n0*math.log1p(-l)+sum(lr(r,l) for r in positive)
    lo=0.;hi=.8;phi=(math.sqrt(5)-1)/2
    c=hi-phi*(hi-lo);d=lo+phi*(hi-lo);sc=objective(c);sd=objective(d)
    for _ in range(60):
        if sc>sd:hi=d;d=c;sd=sc;c=hi-phi*(hi-lo);sc=objective(c)
        else:lo=c;c=d;sc=sd;d=lo+phi*(hi-lo);sd=objective(d)
    return max((0.,(lo+hi)/2,.8),key=objective)

def rot(w):return ''.join(ABC[(ord(c)-97+13)%26] for c in w)

def cv(lines,check_cipher=True):
    roots={};fs=[];rates=[]
    for fi in range(5):
        train=[x for x in lines if fold(x[0])!=fi];test=[x for x in lines if fold(x[0])==fi]
        if not train or not test:raise ValueError('EMPTY_FOLD')
        b=bigram(train);et=list(events(train,b))
        glob=fit(et);interior=fit([x for x in et if x[2]=='INTERIOR']);last=fit([x for x in et if x[2]=='LAST'])
        cipher=bigram([(r,g,tuple(rot(w) for w in words)) for r,g,words in train]) if check_cipher else None
        loss=[0.]*4;n=0;foldroots=set()
        for root,g,pos,lb,ratio in events(test,b):
            L=-lb;M=-(lb+(lr(ratio,glob) if pos!='FIRST' else 0.))
            H=-(lb+(lr(ratio,interior if pos=='INTERIOR' else last) if pos!='FIRST' else 0.))
            vec=(L,L,M,H)
            item=roots.setdefault(root,{'n':0,'losses':[0.]*4,'group':{}})
            item['n']+=1
            cell=item['group'].setdefault(g,{'n':0,'losses':[0.]*4});cell['n']+=1
            for j,v in enumerate(vec):item['losses'][j]+=v;cell['losses'][j]+=v;loss[j]+=v
            foldroots.add(root);n+=1
        if check_cipher:
            C=-sum(cipher(rot(w)) for _,_,words in test for w in words)
            assert abs(C-loss[0])<1e-7,('ROT13_RELABEL_NOT_EQUAL',fi,C,loss[0])
        fs.append({'fold':fi,'test_roots':len(foldroots),'test_lines':len(test),'tokens':n,
                   'nll_nats_per_word':[v/n for v in loss]})
        rates.append({'fold':fi,'global':glob,'interior':interior,'last':last})
    return roots,fs,rates

def summarize(rows):
    n=sum(x['n'] for x in rows.values())
    losses=[sum(x['losses'][j] for x in rows.values())/n for j in range(4)]
    return {'roots':len(rows),'tokens':n,
       'loss_nats_per_word':dict(zip(('L_char_bigram','K_rot13_relabel','M_copy_global','H_copy_position'),losses)),
       'gain_M_over_L':losses[0]-losses[2],'gain_H_over_M':losses[2]-losses[3]}

def group_summary(rows):
    out={}
    for g in ('A','B','U'):
        sub={root:row['group'][g] for root,row in rows.items() if g in row['group']}
        if sub:out[g]=summarize(sub)
    return out

def boot(rows):
    ids=sorted(rows,key=lambda z:int(z[1:]));rng=random.Random(SEED+60);a=[];b=[]
    for _ in range(2000):
        r=[rows[ids[rng.randrange(len(ids))]] for i in ids];n=sum(x['n'] for x in r)
        v=[sum(x['losses'][j] for x in r)/n for j in (0,2,3)]
        a.append(v[0]-v[1]);b.append(v[1]-v[2])
    def q(x,p):
        s=sorted(x);z=(len(s)-1)*p;i=int(z);t=z-i
        return s[i]*(1-t)+s[min(i+1,len(s)-1)]*t
    return {'gain_M_over_L':[q(a,.025),q(a,.975)],'gain_H_over_M':[q(b,.025),q(b,.975)]}

def permute(lines,seed):
    rng=random.Random(seed);out=[];mov=0;changed=0
    for root,g,words in lines:
        seq=list(words)
        for k in sorted(set(map(len,seq))):
            ix=[i for i,w in enumerate(seq) if len(w)==k]
            if len(ix)<2:continue
            mov+=len(ix);old=[seq[i] for i in ix];new=old[:];rng.shuffle(new)
            changed+=sum(a!=b for a,b in zip(old,new))
            for i,w in zip(ix,new):seq[i]=w
        out.append((root,g,tuple(seq)))
    return out,{'eligible_positions':mov,'changed_words':changed}

def synth_pos(lines):
    rng=random.Random(282801);out=[];stats=Counter()
    for root,g,words in lines:
        val=[words[0]]
        for word in words[1:]:
            if rng.random()<.3:
                prev=val[-1]
                if rng.random()<.5:word=prev;stats['exact_copy']+=1
                else:
                    k=rng.randrange(len(prev));c=ABC[(ABC.index(prev[k])+rng.randrange(1,26))%26]
                    word=prev[:k]+c+prev[k+1:];stats['substitute_one']+=1
            val.append(word)
        out.append((root,g,tuple(val)))
    return out,dict(stats)

def synth_neg(lines):
    rng=random.Random(282802);pools=defaultdict(list);ix=Counter();out=[]
    for _,g,w in lines:pools[g].extend(w)
    for g in pools:rng.shuffle(pools[g])
    for r,g,words in lines:
        n=len(words);i=ix[g];out.append((r,g,tuple(pools[g][i:i+n])));ix[g]+=n
    return out

def run(data):
    lines,stats=parse(data);edit_test=edit_control()
    rows,fs,rates=cv(lines);obs=summarize(rows);groups=group_summary(rows)
    null=[];diagnostic=[]
    for i in range(49):
        sample,diag=permute(lines,SEED+i);v,_,_=cv(sample,False)
        null.append(summarize(v)['gain_M_over_L']);diagnostic.append(diag)
    ge=sum(x>=obs['gain_M_over_L']-1e-12 for x in null);p=(1+ge)/50
    positive,syn_counts=synth_pos(lines);neg=synth_neg(lines)
    pos=summarize(cv(positive,False)[0]);neg_score=summarize(cv(neg,False)[0])
    assert pos['gain_M_over_L']>.01,'POSITIVE_SYNTH_CONTROL_FAILED'
    return {'experiment':'EXP-0028',
      'classification':'EXPLORATORY_SCOPED_NOT_INDEPENDENT_MANUSCRIPT_TEST',
      'source_version':'ZL3b-n v3b 2025-05-13, 411671 bytes, single previously exposed IVTFF EVA witness',
      'source_sha256':SHA,'row_scope':stats,'folio_number_roots':94,
      'edit_normalization_control':edit_test,
      'models':{'L':'trained character bigram B(word), alpha 0.5, START+END, same training roots',
                'K':'ROT13 bijective relabel of L, trained on rotated TRAIN, mathematically indistinguishable',
                'M':'same B, plus trained single global copy/edit weight; resets from B',
                'H':'same B, but separate trained INTERIOR and LAST copy weights; first uses B'},
      'observed':obs,'per_currier_metadata':groups,'folds':fs,
      'training_copy_rates':rates,'root_cluster_bootstrap_95_descriptive':boot(rows),
      'permutation_null':{'n':49,'preserves':'within-line original word multiset and exact wordlength-position buckets',
           'gain_min':min(null),'gain_mean':sum(null)/len(null),'gain_max':max(null),
           'ge_observed':ge,'one_sided_empirical_p':p,
           'median_movable':sorted(x['eligible_positions'] for x in diagnostic)[24],
           'median_changed_words':sorted(x['changed_words'] for x in diagnostic)[24]},
      'synthetic_positive':{'replacements':syn_counts,'gain_M_over_L':pos['gain_M_over_L'],
                            'pass':pos['gain_M_over_L']>.01},
      'synthetic_negative':{'gain_M_over_L':neg_score['gain_M_over_L'],
                            'pass':neg_score['gain_M_over_L']<=.01},
      'primary_success_criteria_passed':(obs['gain_M_over_L']>=.01 and
                   all(groups[g]['gain_M_over_L']>0 for g in ('A','B')) and p<=.05),
      'secondary_context_gate_passed':(obs['gain_H_over_M']>=.005 and
                   all(groups[g]['gain_H_over_M']>0 for g in ('A','B'))),
      'interpretation_guardrail':'One-exposed-source predictive fit only. Same B innovation in L/M/H, ROT13 K identical. No actual language, decipherment, semantic cipher or unique historical mechanical production identified.'}

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: python exp0028.py ZL3b-n.txt')
    print(json.dumps(run(Path(sys.argv[1]).read_bytes()),ensure_ascii=False,indent=2,sort_keys=True))

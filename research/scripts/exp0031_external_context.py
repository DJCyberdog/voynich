import argparse, collections as C, hashlib, json, random, re
from pathlib import Path
SHA='bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'
PAIRS=(('ch','sh'),('k','t'),('f','p'),('l','r'),('cph','cth'))
COMPS=('cph','cfh','ckh','cth','ch','sh')
def segment(w):
    out=[];i=0
    while i<len(w):
        s=next((c for c in COMPS if w.startswith(c,i)),w[i]);out.append(s);i+=len(s)
    return tuple(out)
def held(r):return int.from_bytes(hashlib.sha256(('EXP0029-root-v1|'+r).encode()).digest()[:8],'big')%5==0
def pieces(body):return re.sub(r'<[^>]*>','.!.' ,body).split('.')
def certain(w):return re.fullmatch(r'[a-z]+',w) is not None
def neighbors(p,i):return 0<i<len(p)-1 and certain(p[i-1]) and certain(p[i+1])
def features(l,r):
    out=[]
    for side,w in enumerate((l,r)):
        u=segment(w);out.extend(((side,'first',u[0]),(side,'last',u[-1]),(side,'length',min(5,len(u)))))
    return tuple(out)
def read(b):
    assert len(b)==411671 and hashlib.sha256(b).hexdigest()==SHA
    s=b.decode('ascii');assert s.startswith('#=IVTFF Eva- 2.0 M 5\n') and '# Version 3b of 13/05/2025' in s[:220]
    train=C.defaultdict(list);test=C.defaultdict(list);counts=C.Counter();roots=set()
    for line in s.splitlines():
        m=re.match(r'^<(f[0-9]+[rv][0-9]?)\.([0-9]+),([^>]*)>\s*(.*)$',line)
        if not m:continue
        f,n,k,body=m.groups()
        if not re.search(r'P0\b',k):continue
        root=re.match(r'f\d+',f)[0];roots.add(root);counts['p0_loci']+=1;p=pieces(body)
        for i,w in enumerate(p):
            if not re.fullmatch(r'[a-z]{4,}',w):continue
            counts['certain_target_words']+=1
            if not neighbors(p,i):continue
            counts['targets_with_two_certain_neighbors']+=1
            u=segment(w);feat=features(p[i-1],p[i+1]);dest=test if held(root) else train
            for pair in PAIRS:
                ix=[j for j,x in enumerate(u) if x in pair]
                if len(ix)!=1:continue
                j=ix[0];key=(pair,root,u[:j]+('_',)+u[j+1:],int(2*i>=len(p)))
                dest[key].append((int(u[j]==pair[1]),feat));counts['pair_rows']+=1
    assert not ({k[1] for k in train}&{k[1] for k in test})
    return train,test,dict(counts),roots
def mixed(groups):return {k:v for k,v in groups.items() if 0<sum(y for y,_ in v)<len(v)}
def fit(groups):
    num=C.Counter();den=C.Counter()
    for k,v in mixed(groups).items():
        p=sum(y for y,_ in v)/len(v)
        for y,fs in v:
            for f in fs:num[k[0],f]+=y-p;den[k[0],f]+=1
    return {k:num[k]/(10+n) for k,n in den.items()}
def score(groups,w):return {k:[(y,sum(w.get((k[0],f),0.) for f in fs)) for y,fs in v] for k,v in mixed(groups).items()}
def wins(v):
    a=[s for y,s in v if y==0];b=[s for y,s in v if y==1]
    return sum(1 if x>z else .5 if x==z else 0 for x in b for z in a),len(a)*len(b)
def aggregate(gs):
    t=[wins(v) for v in gs.values()];return sum(x for x,_ in t),sum(n for _,n in t)
def ratio(x,n):return x/n if n else None
def controls():
    pair=PAIRS[0];out={}
    for pos in (True,False):
        def make(n,prefix):
            return {(pair,prefix+str(i),('_',),0):[(y,tuple((s,'x',y if pos else 0) for s in range(6))) for y in (0,0,1,1)] for i in range(n)}
        tr=make(24,'tr');te=make(12,'te');a=ratio(*aggregate(score(te,fit(tr))));assert a==(1. if pos else .5);out['positive_auc' if pos else 'negative_auc']=a
    for body in ('aaaa.<abc>.bbbb.cccc','aaaa.?.bbbb.cccc','aaaa..bbbb.cccc','aaaa.<->.bbbb.cccc'):
        p=pieces(body);assert not neighbors(p,p.index('bbbb'))
    assert neighbors(pieces('aaaa.bbbb.cccc'),1);out['parser_barrier_pass']=True
    return out
def run(b):
    ctl=controls();tr,te,counts,roots=read(b);mtr=mixed(tr);sc=score(te,fit(tr));w,n=aggregate(sc);obs=ratio(w,n);per=[]
    for pair in PAIRS:
        gs={k:v for k,v in sc.items() if k[0]==pair};ww,nn=aggregate(gs)
        def ct(g):return [sum(y==i for k,v in g.items() if k[0]==pair for y,_ in v) for i in (0,1)]
        per.append({'pair':list(pair),'train_counts':ct(tr),'test_counts':ct(te),'train_mixed_counts':ct(mtr),'test_mixed_counts':ct(gs),'train_mixed_strata':sum(k[0]==pair for k in mtr),'test_mixed_strata':len(gs),'test_mixed_roots':len({k[1] for k in gs}),'comparisons':nn,'wins':ww,'auc':ratio(ww,nn)})
    rng=random.Random(310031);null=[]
    if n:
        for _ in range(999):
            total=0
            for v in sc.values():
                labels=[y for y,_ in v];scores=[s for _,s in v];rng.shuffle(scores);total+=wins(list(zip(labels,scores)))[0]
            null.append(total/n)
    p=(1+sum(x>=obs for x in null))/1000 if null else None
    by=C.defaultdict(list)
    for k,v in sc.items():by[k[1]].append(wins(v))
    blocks=[(sum(w for w,_ in by[r]),sum(n for _,n in by[r])) for r in sorted(by)];rng=random.Random(310032);boot=[]
    if blocks:
        for _ in range(400):
            bb=rng.choices(blocks,k=len(blocks));boot.append(sum(w for w,_ in bb)/sum(n for _,n in bb))
    boot.sort();qual=sum(x['test_mixed_strata']>=3 and x['train_mixed_strata']>=1 for x in per)
    gates={'strata_ge20':len(sc)>=20,'roots_ge8':len(by)>=8,'pairs_ge2':qual>=2,'comparisons_ge50':n>=50,'auc_ge055':obs is not None and obs>=.55,'p_le005':p is not None and p<=.05}
    sufficient=all(gates[k] for k in ('strata_ge20','roots_ge8','pairs_ge2','comparisons_ge50'))
    return {'experiment':'EXP-0031','source_sha256':SHA,'parser_counts':counts,'all_p0_roots':len(roots),'train_pair_roots':len({k[1] for k in tr}),'test_pair_roots':len({k[1] for k in te}),'train_mixed_strata':len(mtr),'test_mixed_strata':len(sc),'test_mixed_roots':len(by),'qualifying_pairs':qual,'comparisons':n,'wins':w,'auc':obs,'null_mean':sum(null)/len(null) if null else None,'null_max':max(null) if null else None,'null_exceedances':sum(x>=obs for x in null) if null else None,'p_empirical':p,'bootstrap_auc':[boot[9],boot[389]] if boot else None,'pair_results':per,'gates':gates,'decision':'PASS' if all(gates.values()) else 'INCONCLUSIVE' if not sufficient else 'NOT_MET','controls':ctl}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('output');a=ap.parse_args();Path(a.output).write_text(json.dumps(run(Path(a.input).read_bytes()),sort_keys=True,indent=2)+'\n')

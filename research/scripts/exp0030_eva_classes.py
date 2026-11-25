import argparse, collections as C, hashlib, itertools, json, math, random, re
from pathlib import Path
SHA='bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'
COMPS=('cph','cfh','ckh','cth','ch','sh')
def segment(w):
    out=[];i=0
    while i<len(w):
        s=next((c for c in COMPS if w.startswith(c,i)),w[i]);out.append(s);i+=len(s)
    return tuple(out)
def held(r):return int.from_bytes(hashlib.sha256(('EXP0029-root-v1|'+r).encode()).digest()[:8],'big')%5==0
def read(b):
    assert len(b)==411671 and hashlib.sha256(b).hexdigest()==SHA
    s=b.decode('ascii');assert s.startswith('#=IVTFF Eva- 2.0 M 5\n') and '# Version 3b of 13/05/2025' in s[:220]
    rows=[];c=C.Counter()
    for line in s.splitlines():
        m=re.match(r'^<(f[0-9]+[rv][0-9]?)\.([0-9]+),([^>]*)>\s*(.*)$',line)
        if not m:continue
        f,n,k,body=m.groups()
        if not re.search(r'P0\b',k):continue
        c['p0_loci']+=1
        for w in re.sub(r'<[^>]*>','.',body.replace('<->','.').replace('<~>','.')).split('.'):
            if not w:continue
            c['candidate_segments']+=1
            if not re.fullmatch(r'[a-z]{4,}',w):c['rejected_segments']+=1;continue
            c['accepted_tokens']+=1;rows.append((re.match(r'f\d+',f)[0],segment(w)))
    return rows,dict(c)
def collect(rows):
    counts=C.Counter();v=C.defaultdict(C.Counter);f=C.defaultdict(set)
    for _,w in rows:
        for i,x in enumerate(w):
            counts[x]+=1;v[x][w[i-1] if i else '^',w[i+1] if i+1<len(w) else '$']+=1;f[x].add(w[:i]+('_',)+w[i+1:])
    return counts,v,f
def cos(a,b):
    d=math.sqrt(sum(x*x for x in a.values())*sum(x*x for x in b.values()))
    return sum(v*b.get(k,0) for k,v in a.items())/d if d else 0.
def jac(a,b):return len(a&b)/len(a|b) if a or b else 0.
def choose(pairs,v):
    out=[];used=set()
    for a,b in sorted(pairs,key=lambda p:(-cos(v[p[0]],v[p[1]]),p)):
        if cos(v[a],v[b])<.85:break
        if a in used or b in used:continue
        out.append((a,b));used.update((a,b))
        if len(out)==5:break
    return out
def controls():
    # Each letter has 20 distinct frames, all same-frequency; the target pairs differ only in frame/context overlap.
    rows=[]
    for i in range(20):
        for x,l,r in [('a','L','R'),('b','L','R'),('c','M','N'),('d','O','P'),('e','Q','S'),('f','T','U')]:rows.append(('synthetic',(str(i),l,x,r)))
    n,v,f=collect(rows);pair=choose(list(itertools.combinations('abcdef',2)),v)
    assert all(n[x]==20 for x in 'abcdef') and ('a','b') in pair
    out={'ab_jaccard':jac(f['a'],f['b']),'ab_cosine':cos(v['a'],v['b']),'cd_jaccard':jac(f['c'],f['d']),'ef_jaccard':jac(f['e'],f['f']),'ef_cosine':cos(v['e'],v['f'])}
    assert out=={'ab_jaccard':1.,'ab_cosine':1.,'cd_jaccard':0.,'ef_jaccard':0.,'ef_cosine':0.};return out

def run(b):
    ctl=controls();rows,parser=read(b);train=[z for z in rows if not held(z[0])];test=[z for z in rows if held(z[0])]
    nt,vt,ft=collect(train);ne,ve,fe=collect(test);eligible=sorted(x for x in nt if nt[x]>=100);pairs=list(itertools.combinations(eligible,2));learn=choose(pairs,vt)
    def distance(p,q):return math.dist(sorted(math.log(nt[x]) for x in p),sorted(math.log(nt[x]) for x in q))
    pools=[sorted((q for q in pairs if q not in learn),key=lambda q:(distance(p,q),q))[:10] for p in learn]
    def metric(p):a,b=p;return {'pair':list(p),'train_counts':[nt[a],nt[b]],'test_counts':[ne[a],ne[b]],'train_cosine':cos(vt[a],vt[b]),'test_cosine':cos(ve[a],ve[b]),'test_frames':[len(fe[a]),len(fe[b])],'test_intersection':len(fe[a]&fe[b]),'test_jaccard':jac(fe[a],fe[b])}
    def mean(a):return sum(a)/len(a) if a else 0.
    met=[metric(p) for p in learn];poolmet=[[dict(metric(q),log_count_distance=distance(p,q)) for q in pool] for p,pool in zip(learn,pools)]
    obs=mean([x['test_jaccard'] for x in met]);co=mean([x['test_cosine'] for x in met]);rng=random.Random(300030);null=[];nullco=[]
    for i in range(999):
        z=[rng.choice(pool) for pool in poolmet];null.append(mean([x['test_jaccard'] for x in z]));nullco.append(mean([x['test_cosine'] for x in z]))
    pval=(1+sum(x>=obs for x in null))/1000
    # Bootstrap union of sets over sampled roots; repeats have no further effect on presence.
    by=C.defaultdict(list)
    for row in test:by[row[0]].append(row)
    roots=sorted(by);per={r:collect(by[r])[2] for r in roots};rng=random.Random(300031);boot=[];used=sorted(set(x for p in learn for x in p)|set(x for pool in pools for p in pool for x in p))
    for _ in range(400):
        sampled=set(rng.choices(roots,k=len(roots)));sets={x:set().union(*(per[r].get(x,set()) for r in sampled)) for x in used}
        def j(p):return jac(sets[p[0]],sets[p[1]])
        boot.append(mean([j(p) for p in learn])-mean([mean([j(q) for q in pool]) for pool in pools]))
    boot.sort();support=len(learn)>=3 and all(min(x['test_counts'])>=20 and min(x['test_frames'])>=10 for x in met);gates={'support':support,'delta_ge_0p02':obs-mean(null)>=.02,'p_le_0p05':pval<=.05,'cosine_ge_0p70':co>=.70}
    return {'experiment':'EXP-0030','source_sha256':SHA,'parser':parser,'train_words':len(train),'test_words':len(test),'train_roots':len(set(r for r,_ in train)),'test_roots':len(roots),'eligible_units':eligible,'eligible_pairs':len(pairs),'learned':met,'control_pools':poolmet,'observed_jaccard':obs,'observed_cosine':co,'null_mean_jaccard':mean(null),'null_mean_cosine':mean(nullco),'null_max_jaccard':max(null),'null_exceedances':sum(x>=obs for x in null),'p_empirical':pval,'delta_jaccard':obs-mean(null),'bootstrap_delta':[boot[9],boot[389]],'gates':gates,'decision':'PASS' if all(gates.values()) else 'INCONCLUSIVE' if not support else 'NOT_MET','synthetic_controls':ctl}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('output');a=ap.parse_args();Path(a.output).write_text(json.dumps(run(Path(a.input).read_bytes()),sort_keys=True,indent=2)+'\n')

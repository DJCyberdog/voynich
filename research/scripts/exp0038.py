import collections as C, hashlib, json, math, random, re, sys
from pathlib import Path
PIN=['8438ba1c45f47fe1d06b5262cbcdf60ce69158a0edbd4dd802612896f3217e2a','0c0d1eea4b5ab87f8a65fb7f4346864cd90758ad993812b4f2122b3899d4ac88']
DOM=[('Lc','Lf'),('Ln','Lt')]
def parse(raw,i):
    assert hashlib.sha256(raw).hexdigest()==PIN[i]
    d={}
    for line in raw.decode('ascii').splitlines():
        m=re.match(r'^<(f\d+[rv]\d?)\.(\d+),([^>]*)>\s*(.*)$',line)
        if not m or m[3][-2:] not in sum(DOM,()):continue
        loc=(m[1],m[2]);assert loc not in d
        s=re.sub(r'<![^>]*>','',m[4]).strip();w=tuple(re.findall(r'[A-Z][0-9a-z]',s)) if re.fullmatch(r'(?:[A-Z][0-9a-z]){2,}',s) else None
        d[loc]=(m[3][-2:],w)
    return d
def feats(w):return frozenset([('first',w[0]),('last',w[-1])]+[('uni',x) for x in w]+[('bi',x,y) for x,y in zip(w,w[1:])])
def weights(rows,labels,i,root):
    cnt=[C.Counter(),C.Counter()];N=[0,0]
    for j,x in enumerate(rows):
        if x[0]==root:continue
        y=labels[j];N[y]+=1;cnt[y].update(x[3+i])
    assert min(N)>0
    return {k:math.log((cnt[1][k]+.5)/(N[1]+1))-math.log((cnt[0][k]+.5)/(N[0]+1)) for k in cnt[0].keys()|cnt[1].keys()}
def rank(a,b):return 1. if a>b+1e-12 else 0. if b>a+1e-12 else .5
def evaluate(rows,labels,strata):
    out=[]
    for i in range(2):
        scores={};block=C.defaultdict(list)
        for root in sorted({x[0] for x in rows}):
            w=weights(rows,labels,i,root)
            for j,x in enumerate(rows):
                if x[0]==root:scores[j]=sum(w.get(f,0.) for f in sorted(x[4-i]))
        for ix in strata.values():
            a=[j for j in ix if labels[j]==1];b=[j for j in ix if labels[j]==0]
            for j in a:
                for k in b:
                    assert rows[j][:2]==rows[k][:2]
                    block[rows[j][0]].append(rank(scores[j],scores[k]))
        N=sum(map(len,block.values()));auc=sum(map(sum,block.values()))/N
        out.append(dict(auc=auc,pairs=N,roots=len(block),positive_roots=sum(sum(v)/len(v)>.5 for v in block.values()),root_mean=sum(sum(v)/len(v) for v in block.values())/len(block),per_root={r:dict(N=len(v),auc=sum(v)/len(v)) for r,v in sorted(block.items())}))
    return out
def run(z,g):
    a,b=parse(z,0),parse(g,1);assert all(a[k][0]==b[k][0] for k in a.keys()&b.keys())
    # Synthetic class-specific rank and exact tie.
    toy=[('f1','f1r',(2,2),feats(('A1','A1')),feats(('A1','A1'))),('f1','f1r',(2,2),feats(('B1','B1')),feats(('B1','B1')))]*20
    w=weights(toy,[1,0]*20,0,'f2');assert sum(w.get(f,0) for f in toy[0][3])>sum(w.get(f,0) for f in toy[1][3]);assert rank(1.,1.)==.5
    result={}
    for di,ts in enumerate(DOM):
        rows=[];labels=[];strata=C.defaultdict(list)
        for k in sorted(a.keys()&b.keys()):
            t,x=a[k];_,y=b[k]
            if t not in ts or x is None or y is None:continue
            root=re.match(r'f\d+',k[0])[0];ls=(len(x),len(y));j=len(rows);rows.append((root,k[0],ls,feats(x),feats(y)));labels.append(int(t==ts[0]));strata[(k[0],*ls)].append(j)
        obs=evaluate(rows,labels,strata);null=[[],[]];rng=random.Random(380801+di)
        for _ in range(399):
            p=labels.copy()
            for ids in strata.values():
                v=[p[j] for j in ids];rng.shuffle(v)
                for j,y in zip(ids,v):p[j]=y
            for i,x in enumerate(evaluate(rows,p,strata)):null[i].append(x['auc'])
        for i,x in enumerate(obs):
            p=(1+sum(v>=x['auc']-1e-12 for v in null[i]))/400
            gates=dict(support=x['pairs']>=30 and x['roots']>=4,auc=x['auc']>=.65,root_consistency=x['positive_roots']>=3,permutation=p<=.05)
            x.update(p=p,null_mean=sum(null[i])/399,gates=gates,decision='PASS' if all(gates.values()) else 'NOT_MET' if gates['support'] else 'INCONCLUSIVE')
        ds=[x['decision'] for x in obs];result['/'.join(ts)]=dict(eligible=len(rows),class_counts={ts[0]:sum(labels),ts[1]:len(labels)-sum(labels)},mixed_strata=sum(len({labels[j] for j in ids})==2 for ids in strata.values()),ZL_to_GC=obs[0],GC_to_ZL=obs[1],decision='NOT_MET' if 'NOT_MET' in ds else 'INCONCLUSIVE' if 'INCONCLUSIVE' in ds else 'PASS')
    ds=[x['decision'] for x in result.values()]
    return dict(experiment='EXP-0038',decision='NOT_MET' if 'NOT_MET' in ds else 'INCONCLUSIVE' if 'INCONCLUSIVE' in ds else 'PASS',semantic_validation='BLOCKED',source_hashes=PIN,source_label_counts=[dict(C.Counter(t for t,w in x.values())) for x in (a,b)],unmatched_loci=[len(a.keys()-b.keys()),len(b.keys()-a.keys())],results=result,controls=dict(hashes=True,unique_loci=True,subtype_agreement=True,root_excluded=True,synthetic_positive=True,ties=True))
if __name__=='__main__':Path(sys.argv[3]).write_text(json.dumps(run(Path(sys.argv[1]).read_bytes(),Path(sys.argv[2]).read_bytes()),sort_keys=True,indent=2)+'\n')

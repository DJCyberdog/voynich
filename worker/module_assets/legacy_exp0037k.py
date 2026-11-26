import collections as C, hashlib, json, math, random, re, sys
from pathlib import Path
PIN=['8438ba1c45f47fe1d06b5262cbcdf60ce69158a0edbd4dd802612896f3217e2a','0c0d1eea4b5ab87f8a65fb7f4346864cd90758ad993812b4f2122b3899d4ac88']
NAME=['ZL','GC']
def held(r):return int.from_bytes(hashlib.sha256(('EXP0029-root-v1|'+r).encode()).digest()[:8],'big')%5==0
def parse(raw,i):
    assert hashlib.sha256(raw).hexdigest()==PIN[i]
    rows=[];meta={};loci=set()
    for line in raw.decode('ascii').splitlines():
        h=re.match(r'^<(f\d+[rv]\d?)>\s*<!([^>]*)>',line)
        if h:meta[h[1]]=dict(re.findall(r'\$([A-Z])=([^\s>]+)',h[2]));continue
        m=re.match(r'^<(f[0-9]+[rv][0-9]?)\.([0-9]+),([^>]*)>\s*(.*)$',line)
        if not m or not re.search(r'P0\b',m[3]):continue
        fol=m[1];root=re.match(r'f\d+',fol)[0];domain=meta.get(fol,{}).get('L','?');domain=domain if domain in ('A','B') else '?';loc=(fol,m[2]);assert loc not in loci;loci.add(loc)
        pieces=[w for w in re.sub(r'<[^>]*>','.!.' ,m[4]).split('.') if w];idx=[j for j,w in enumerate(pieces) if w!='!'];hist=[]
        for j,w in enumerate(pieces):
            if not re.fullmatch(r'(?:[A-Z][0-9a-z]){2,}',w):hist=[];continue
            pos='single' if len(idx)==1 else 'first' if j==idx[0] else 'last' if j==idx[-1] else 'middle'
            rows.append((root,w,len(w)//2,domain,pos,tuple(hist[-3:])))
            hist.append(w)
    assert len(rows)==[28464,30691][i]
    return rows,len(loci)
def encode(rows,vocab):
    def cat(w):return w if w in vocab else 'UNK:'+str(len(w)//2)
    return [(r,cat(w),n,d,p,len(h[-1])//2,tuple(map(cat,h))) for r,w,n,d,p,h in rows if h]
class Model:
    def __init__(self,rows,support):
        self.support=support;self.count=[C.Counter() for _ in range(7)];self.total=[C.Counter() for _ in range(7)]
        for x in rows:
            for i,k in enumerate(self.keys(x)):
                self.count[i][k,x[1]]+=1;self.total[i][k]+=1
    @staticmethod
    def keys(x):
        r,w,n,d,p,pl,h=x
        return [(n,),(n,d),(n,d,p),(n,d,p,pl)]+[(n,h[-k:]) for k in range(1,len(h)+1)]
    def predict(self,x):
        y=x[1];p=1/len(self.support[x[2]]);out=[]
        for i,k in enumerate(self.keys(x)):
            a=1 if i==0 else 20;p=(self.count[i][k,y]+a*p)/(self.total[i][k]+a)
            if i>=3:out.append(p)
        assert all(0<v<=1 for v in out);return out
    def bigram(self,x,ctx,b):
        k=(x[2],(ctx,));return (self.count[4][k,x[1]]+20*b)/(self.total[4][k]+20)
def controls():
    support=C.defaultdict(lambda:('UNK:2','A1A1','B1B1'));rows=[('r',w,2,'A','middle',2,(prev,)) for w,prev in [('A1A1','B1B1'),('B1B1','A1A1')]*100];m=Model(rows,support)
    gain=sum(math.log(m.predict(x)[1]/m.predict(x)[0]) for x in rows)/len(rows);assert gain>0
    for x in [rows[0],('r','A1A1',2,'B','first',3,('UNK:3','UNK:2','UNK:2'))]:
        p=[m.predict((x[0],w,*x[2:])) for w in support[2]];assert all(abs(sum(v)-1)<1e-12 for v in zip(*p))
    x=('r','A1A1',2,'A','middle',2,('UNK:2',));assert m.predict(x)[0]==m.predict(x)[1]
    return dict(synthetic_gain=gain,normalization=True,zero_count=True)
def stats(model,rows):
    N=len(rows);assert N;ps=[model.predict(x) for x in rows];k=min(map(len,ps));loss=[-sum(math.log(p[j]) for p in ps)/N for j in range(k)]
    return dict(N=N,roots=len({x[0] for x in rows}),nll=loss,bits=[x/math.log(2) for x in loss],gains=[loss[0]-v for v in loss[1:]])
def assess(model,rows,i):
    blocks=C.defaultdict(list);groups=C.defaultdict(list);bs=[];gains=[]
    for j,x in enumerate(rows):
        p=model.predict(x);b=p[0];v=math.log(p[1]/b);bs.append(b);gains.append(v);blocks[x[0]].append(v);groups[(x[0],x[3],x[4],x[2],x[5])].append(j)
    N=len(rows);rr=[(sum(v),len(v)) for _,v in sorted(blocks.items())];obs=sum(gains)/N;R=random.Random(379031+i);boot=[]
    for _ in range(400):
        z=R.choices(rr,k=len(rr));boot.append(sum(a for a,b in z)/sum(b for a,b in z))
    boot.sort();R=random.Random(379041+i);p=(1+sum(sum(a*R.choice((-1,1)) for a,b in rr)>=sum(a for a,b in rr) for _ in range(999)))/1000
    active=[];fixed=0.;nactive=0
    for js in groups.values():
        contexts=[rows[j][-1][-1] for j in js];unique=sorted(set(contexts))
        if len(unique)<2:fixed+=sum(gains[j] for j in js);continue
        nactive+=len(js);active.append((contexts,[{c:math.log(model.bigram(rows[j],c,bs[j])/bs[j]) for c in unique} for j in js]))
    null=[];R=random.Random(379051+i)
    for _ in range(199):
        val=fixed
        for ctx,tables in active:
            a=ctx.copy();R.shuffle(a);val+=sum(t[c] for t,c in zip(tables,a))
        null.append(val/N)
    perm=(1+sum(v>=obs-1e-12 for v in null))/200;gates=dict(support=N>=100 and len(rr)>=8,gain=obs>=.02,bootstrap=boot[9]>0,sign_p=p<=.05,perm_p=perm<=.05,perm_support=nactive>=100)
    return dict(N=N,roots=len(rr),gain=obs,bootstrap=[boot[9],boot[389]],p=p,positive_roots=sum(a>0 for a,b in rr),permutation_p=perm,permutation_mean=sum(null)/len(null),permutation_excess=obs-sum(null)/len(null),permutable=nactive,permutation_strata=len(active),gates=gates,decision='PASS' if all(gates.values()) else 'NOT_MET' if gates['support'] and gates['perm_support'] else 'INCONCLUSIVE',root_gains=[dict(root=r,N=len(v),gain=sum(v)/len(v)) for r,v in sorted(blocks.items())])
def run(zraw,graw):
    raw=[parse(zraw,0),parse(graw,1)];rows=[x[0] for x in raw];tr=[[x for x in r if not held(x[0])] for r in rows];te=[[x for x in r if held(x[0])] for r in rows];assert not ({x[0] for a in tr for x in a}&{x[0] for a in te for x in a})
    cnt=[C.Counter(x[1] for x in a) for a in tr];vocab={w for w in cnt[0].keys()&cnt[1].keys() if min(c[w] for c in cnt)>=5};support=C.defaultdict(list)
    for w in sorted(vocab):support[len(w)//2].append(w)
    for n in set(x[2] for r in rows for x in r):support[n].append('UNK:'+str(n))
    # No unseen lengths introduce known words; UNK-only support is structural.
    et=[encode(a,vocab) for a in tr];ee=[encode(a,vocab) for a in te];models=[Model(a,support) for a in et];ctl=controls()
    for m,a in zip(models,ee):
        for x in [a[0],next(x for x in a if len(x[-1])==3)]:
            p=[m.predict((x[0],w,*x[2:])) for w in support[x[2]]];assert all(abs(sum(v)-1)<1e-10 for v in zip(*p))
    # Parser cannot bridge a rejected or markup piece; verify explicitly from real locus and synthetic pattern.
    assert all(len(x[-1])<=3 for a in rows for x in a);assert all(len(x[-1])>=1 for a in ee for x in a)
    results={}
    for i in range(2):
        a=ee[1-i];m=models[i];key=NAME[i]+'_to_'+NAME[1-i];known=[x for x in a if not x[1].startswith('UNK:')];long=[x for x in a if len(x[-1])>=3]
        results[key]=dict(primary=assess(m,a,i),all=stats(m,a),known=stats(m,known),long=stats(m,long),own_all=stats(models[1-i],a),own_long=stats(models[1-i],long),known_fraction=len(known)/len(a))
    # Explicit synthetic barrier test uses same token logic as native parser.
    def history_pattern(s):
        h=[];out=[]
        for w in [w for w in re.sub(r'<[^>]*>','.!.' ,s).split('.') if w]:
            if not re.fullmatch(r'(?:[A-Z][0-9a-z]){2,}',w):h=[];continue
            out.append(len(h));h.append(w)
        return out
    assert history_pattern('A1A1.B1B1<->A1A1.A1?.B1B1.A1A1.A1.B1B1')==[0,1,0,0,1,0]
    ds=[v['primary']['decision'] for v in results.values()];decision='NOT_MET' if 'NOT_MET' in ds else 'INCONCLUSIVE' if 'INCONCLUSIVE' in ds else 'PASS'
    return dict(experiment='EXP-0037k',decision=decision,source_hashes=PIN,vocab_size=len(vocab),sources={NAME[i]:dict(tokens=len(rows[i]),loci=raw[i][1],train=len(tr[i]),test=len(te[i]),train_context=len(et[i]),test_context=len(ee[i]),test_three=sum(len(x[-1])==3 for x in ee[i]),train_roots=len({x[0] for x in tr[i]}),test_roots=len({x[0] for x in te[i]})) for i in range(2)},results=results,controls=dict(ctl,source_hashes=True,parser_replay=True,root_disjoint=True,barrier=True))
if __name__=='__main__':Path(sys.argv[3]).write_text(json.dumps(run(Path(sys.argv[1]).read_bytes(),Path(sys.argv[2]).read_bytes()),sort_keys=True,indent=2)+'\n')

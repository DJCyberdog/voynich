import collections as C, hashlib, itertools, json, math, random, re, sys
from pathlib import Path
import exp0034_currier_transfer as d

def read(raw):
    assert len(raw)==411671 and hashlib.sha256(raw).hexdigest()==d.SHA
    meta={};rows=[]
    for line in raw.decode('ascii').splitlines():
        h=re.match(r'^<(f\d+[rv]\d?)>\s*<!([^>]*)>',line)
        if h:
            v=dict(re.findall(r'\$([A-Z])=([^\s>]+)',h[2]));assert h[1] not in meta or meta[h[1]]==v;meta[h[1]]=v;continue
        m=re.match(r'^<(f[0-9]+[rv][0-9]?)\.([0-9]+),([^>]*)>\s*(.*)$',line)
        if not m or not re.search(r'P0\b',m[3]):continue
        f=m[1];r=re.match(r'f\d+',f)[0];prev=None
        for w in re.sub(r'<[^>]*>','.!.' ,m[4]).split('.'):
            if not re.fullmatch(r'[a-z]{4,}',w):prev=None;continue
            u=d.seg(w);rows.append((r,u,prev,meta.get(f,{}).get('L','?')));prev=u
    assert len(rows)==24351
    return rows

def inner(r):return int.from_bytes(hashlib.sha256(('EXP0032b-inner-v1|'+r).encode()).digest()[:8],'big')%5==0

def oov(rows,fit):
    v={x[1] for x in fit};return [x for x in rows if x[1] not in v]

def stat(rows):return dict(tokens=len(rows),types=len({x[1] for x in rows}),roots=len({x[0] for x in rows}))

def ctx(w,i,k):return (('^',)*k+w[:i])[-k:]

class Higher:
    def __init__(self,words,k,alpha,abc=d.ABC):
        self.base=d.Base(words,abc);self.k=k;self.alpha=alpha;self.abc=abc;self.count=C.Counter();self.den=C.Counter()
        for w in words:
            for i,x in enumerate(w):
                slot=d.slot(i,len(w))
                for j in range(2,k+1):
                    key=(j,slot,ctx(w,i,j));self.count[key,x]+=1;self.den[key]+=1
    def predict(self,w):
        n=len(w);b=self.base;p=1.
        for i,x in enumerate(w):
            l=w[i-1] if i else '^';s=d.slot(i,n);g=(b.u[x]+.5)/(b.N+.5*len(self.abc));pb=(b.b[l,x]+10*g)/(b.bd[l]+10);q=(b.s[s,l,x]+20*pb)/(b.sd[s,l]+20)
            for j in range(2,self.k+1):
                key=(j,s,ctx(w,i,j));q=(self.count[key,x]+self.alpha*q)/(self.den[key]+self.alpha)
            p*=q
        return p

def copy(w,prev,abc):
    n=len(w)
    if prev is None or len(prev)!=n:return None
    diff=sum(a!=b for a,b in zip(w,prev));a=len(abc)-1
    if diff==0:return .25
    if diff==1:return (.75 if n==1 else .5)/(n*a)
    if diff==2:return .25/(math.comb(n,2)*a*a)
    return 0.

def mix(h,c,weight=.25):return h if c is None else (1-weight)*h+weight*c

def probs(h,q,w,prev):
    s=h.base.predict(w);z=q.q(w);g=.5*(s+z);v=h.predict(w);j=.5*(v+z);c=copy(w,prev,h.abc)
    return (s,g,v,j,mix(v,c),mix(j,c))

NAMES=('S','G','H','J','M','K')

def controls():
    ctl=d.controls();abc=('a','b','c');words=[tuple(w) for w in ('ac','bc','aca','bca','acb','ccc')]*4;q=d.Grammar(words,32,abc,(('a','b'),));err=0.;rel=0.
    perm={'a':'c','b':'a','c':'b'};transform=lambda w:tuple(perm[x] for x in w)
    for k,alpha in itertools.product((2,3,4),(5,20,80)):
        h=Higher(words,k,alpha,abc);hp=Higher([transform(w) for w in words],k,alpha,abc)
        for n in range(1,6):
            for prev in (None,tuple('a'*n),tuple('a'*(n+1))):
                sums=[0.]*6
                for w in itertools.product(abc,repeat=n):
                    pp=probs(h,q,w,prev);sums=[a+b for a,b in zip(sums,pp)];rel=max(rel,abs(h.predict(w)-hp.predict(transform(w))));assert mix(h.predict(w),copy(w,prev,abc),0)==h.predict(w)
                err=max(err,max(abs(x-1) for x in sums))
    assert err<1e-12 and rel<1e-12
    h=Higher(words,2,5,abc);w=tuple('aaaaa');v=h.predict(w);cp=math.log(mix(v,copy(w,w,abc))/v);assert cp>0
    return dict(ctl,new_normalization_error=err,cipher_relabel_max_error=rel,copy_positive_gain=cp,copy_zero_weight=True)

def measure(rows,h,q):
    loss=[0.]*6;groups=C.defaultdict(list);same=0
    for r,w,prev,label in rows:
        v=[math.log(x) for x in probs(h,q,w,prev)];loss=[a-b for a,b in zip(loss,v)];groups[r].append(v[3]-v[2]);same+=prev is not None and len(prev)==len(w)
    n=len(rows);l=dict(zip(NAMES,[x/n for x in loss]));return dict(stat(rows),nll=l,J_H=l['H']-l['J'],K_M=l['M']-l['K'],M_H=l['H']-l['M'],K_J=l['J']-l['K'],same_length_prev=same),groups

def run(raw):
    ctl=controls();rows=read(raw);train=[x for x in rows if not d.held(x[0])];test=[x for x in rows if d.held(x[0])];fit=[x for x in train if not inner(x[0])];val=[x for x in train if inner(x[0])];vo=oov(val,fit);assert not ({x[0] for x in fit}&{x[0] for x in val}) and not ({x[0] for x in train}&{x[0] for x in test});grid=[]
    for k,a in itertools.product((2,3,4),(5,20,80)):
        h=Higher([x[1] for x in fit],k,a);loss=-sum(math.log(h.predict(x[1])) for x in vo)/len(vo);grid.append(dict(k=k,alpha=a,nll=loss,cells=len(h.count)))
    win=min(grid,key=lambda x:(x['nll'],x['k'],x['alpha']));words=[x[1] for x in train];h=Higher(words,win['k'],win['alpha']);q=d.Grammar(words,128);oo=oov(test,train);a,_=measure(test,h,q);o,groups=measure(oo,h,q);assert abs(o['nll']['S']-11.740734717509724)<1e-9 and abs(o['nll']['G']-11.46570758571434)<1e-9
    bb=[(sum(groups[r]),len(groups[r])) for r in sorted(groups)];obs=sum(x for x,_ in bb);rng=random.Random(350031);boot=[]
    for _ in range(400):
        z=rng.choices(bb,k=len(bb));boot.append(sum(x for x,_ in z)/sum(n for _,n in z))
    boot.sort();rng=random.Random(350032);ex=sum(sum(x*rng.choice((-1,1)) for x,_ in bb)>=obs for _ in range(999));p=(1+ex)/1000;support=len(vo)>=100 and stat(vo)['roots']>=8 and len(oo)>=100 and stat(oo)['roots']>=8;gates=dict(support=support,gain=o['J_H']>=.02,bootstrap=boot[9]>0,p=p<=.05)
    domains={z:measure([x for x in oo if x[3]==z],h,q)[0] for z in ('A','B')};return dict(experiment='EXP-0035',source_sha256=d.SHA,grid=grid,winner=win,split={k:stat(v) for k,v in [('fit',fit),('validation',val),('validation_oov',vo),('train',train),('test',test)]},all=a,oov=o,domains=domains,complexity=dict(higher_cells=len(h.count),higher_contexts=len(h.den),chunks=len(q.inv),role_cells=4*len(q.inv),role_nonzero=len(q.c),base_bigram_cells=len(h.base.b),base_slot_cells=len(h.base.s)),bootstrap=[boot[9],boot[389]],p=p,exceedances=ex,root_gains=[dict(root=r,tokens=len(groups[r]),gain=sum(groups[r])/len(groups[r])) for r in sorted(groups)],controls=dict(ctl,baseline_replay=True,root_disjoint=True),gates=gates,decision='PASS' if all(gates.values()) else 'NOT_MET' if support else 'INCONCLUSIVE')

if __name__=='__main__':Path(sys.argv[2]).write_text(json.dumps(run(Path(sys.argv[1]).read_bytes()),sort_keys=True,indent=2)+'\n')

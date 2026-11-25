import argparse, collections as C, hashlib, itertools, json, math, random, re
from pathlib import Path
SHA='bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'
COMPS=('cph','cfh','ckh','cth','ch','sh'); ABC=tuple(sorted(tuple('abcdefghijklmnopqrstuvwxyz')+COMPS))
PAIRS=(('ch','sh'),('k','t'),('f','p'),('l','r'),('cph','cth'))
def seg(w):
    out=[];i=0
    while i<len(w):
        x=next((x for x in COMPS if w.startswith(x,i)),w[i]);out.append(x);i+=len(x)
    return tuple(out)
def held(r,prefix):return int.from_bytes(hashlib.sha256((prefix+'|'+r).encode()).digest()[:8],'big')%5==0
def read(raw):
    assert len(raw)==411671 and hashlib.sha256(raw).hexdigest()==SHA
    s=raw.decode('ascii');assert s.startswith('#=IVTFF Eva- 2.0 M 5\n') and '# Version 3b of 13/05/2025' in s[:220]
    rows=[]
    for line in s.splitlines():
        m=re.match(r'^<(f[0-9]+[rv][0-9]?)\.([0-9]+),([^>]*)>\s*(.*)$',line)
        if not m:continue
        f,_,k,body=m.groups()
        if not re.search(r'P0\b',k):continue
        r=re.match(r'f\d+',f)[0];prev=None
        for w in re.sub(r'<[^>]*>','.!.' ,body).split('.'):
            if not re.fullmatch(r'[a-z]{4,}',w):prev=None;continue
            u=seg(w);rows.append((r,u,prev));prev=u
    return rows
def slot(i,n):return 'first' if i==0 else 'last' if i==n-1 else 'second' if i==1 else 'penultimate' if i==n-2 else 'middle'
def role(i,j,n):return 'whole' if i==0 and j==n else 'first' if i==0 else 'last' if j==n else 'middle'
ROLES=('whole','first','last','middle')
class Base:
    def __init__(self,words,abc=ABC):
        self.abc=abc;self.u=C.Counter();self.b=C.Counter();self.bd=C.Counter();self.s=C.Counter();self.sd=C.Counter()
        for w in words:
            for i,x in enumerate(w):
                l=w[i-1] if i else '^';k=slot(i,len(w));self.u[x]+=1;self.b[l,x]+=1;self.bd[l]+=1;self.s[k,l,x]+=1;self.sd[k,l]+=1
        self.N=sum(self.u.values());self.lex=dict(sorted(C.Counter(words).items(),key=lambda kv:(-kv[1],kv[0]))[:128]);self.ld=C.Counter()
        for w,n in self.lex.items():self.ld[len(w)]+=n
    def predict(self,w,prev):
        n=len(w);s=1.
        for i,x in enumerate(w):
            l=w[i-1] if i else '^';k=slot(i,n);g=(self.u[x]+.5)/(self.N+.5*len(self.abc));pb=(self.b[l,x]+10*g)/(self.bd[l]+10);s*=(self.s[k,l,x]+20*pb)/(self.sd[k,l]+20)
        lex=self.lex.get(w,0)/self.ld[n] if self.ld[n] else s
        if prev is not None and len(prev)==n:
            d=sum(x!=y for x,y in zip(w,prev));copy=.5 if d==0 else .5/(n*(len(self.abc)-1)) if d==1 else 0.
        else:copy=s
        return s,.25*lex+.25*copy
class Mapping:
    def __init__(self,words,abc,pairs):
        self.cls={x:x for x in abc}
        for a,b in pairs:self.cls[b]=a
        self.members=C.defaultdict(list)
        for x in abc:self.members[self.cls[x]].append(x)
        u=C.Counter(x for w in words for x in w)
        self.em={x:(u[x]+.5)/sum(u[z]+.5 for z in self.members[self.cls[x]]) for x in abc}
    def shape(self,w):return tuple(self.cls[x] for x in w)
    def emit(self,w):return math.prod(self.em[x] for x in w)
class Whole:
    def __init__(self,words):
        self.m=Mapping(words,ABC,PAIRS);self.c=C.Counter(self.m.shape(w) for w in words);self.d=C.Counter()
        for w,n in self.c.items():self.d[len(w)]+=n
    def q(self,w):return self.c[self.m.shape(w)]/self.d[len(w)]*self.m.emit(w) if self.d[len(w)] else None
class Grammar:
    def __init__(self,words,merges,abc=ABC,pairs=()):
        self.m=Mapping(words,abc,pairs);inventory={(x,) for x in self.m.members};forms=C.Counter(tuple((x,) for x in self.m.shape(w)) for w in words)
        for _ in range(merges):
            cnt=C.Counter()
            for seq,n in forms.items():
                for a,b in zip(seq,seq[1:]):
                    if len(a)+len(b)<=4 and a+b not in inventory:cnt[a,b]+=n
            if not cnt:break
            pair=min(cnt,key=lambda p:(-cnt[p],p))
            if cnt[pair]<2:break
            a,b=pair;ab=a+b;inventory.add(ab);new=C.Counter()
            for seq,n in forms.items():
                out=[];i=0
                while i<len(seq):
                    if i+1<len(seq) and (seq[i],seq[i+1])==pair:out.append(ab);i+=2
                    else:out.append(seq[i]);i+=1
                new[tuple(out)]+=n
            forms=new
        self.inv=sorted(inventory);self.c=C.Counter();self.mass={r:{} for r in ROLES};self.bylen=C.Counter();self.zcache={}
        for seq,n in forms.items():
            end=sum(map(len,seq));i=0
            for chunk in seq:
                j=i+len(chunk);self.c[role(i,j,end),chunk]+=n;i=j
        for r in ROLES:
            total=sum(self.c[r,u]+.5 for u in self.inv)
            for u in self.inv:
                p=(self.c[r,u]+.5)/total;self.mass[r][u]=p;self.bylen[r,len(u)]+=p
    def norm(self,n):
        if n not in self.zcache:
            d=[1.]+[0.]*n
            for j in range(1,n+1):d[j]=sum(d[i]*self.bylen[role(i,j,n),j-i] for i in range(max(0,j-4),j))
            self.zcache[n]=d[n]
        return self.zcache[n]
    def q(self,w):
        v=self.m.shape(w);n=len(v);d=[1.]+[0.]*n
        for j in range(1,n+1):d[j]=sum(d[i]*self.mass[role(i,j,n)].get(v[i:j],0.) for i in range(max(0,j-4),j))
        return d[n]/self.norm(n)*self.m.emit(w)
    def multi_coverage(self,w):
        v=self.m.shape(w);return any(v[i:j] in self.mass['middle'] for i in range(len(v)) for j in range(i+2,min(len(v),i+4)+1))
def mixed(s,o,q,w):
    g=s if q is None else (1-w)*s+w*q
    return g,.5*g+o
def controls():
    abc=('a','b','c');words=[tuple(w) for w in ('ac','bc','aca','bca','acb','ccc')]*4;err=0.
    for pairs in ((),(('a','b'),)):
        g=Grammar(words,32,abc,pairs);b=Base(words,abc)
        for n in range(1,6):
            total=0.
            for w in itertools.product(abc,repeat=n):
                q=g.q(w);total+=q;s,o=b.predict(w,None);assert mixed(s,o,q,0)==(s,.5*s+o)
            err=max(err,abs(total-1))
        z=Grammar(words,0,abc,pairs)
        for n in range(1,6):
            for w in itertools.product(abc,repeat=n):
                expected=z.m.emit(w)*math.prod(z.mass[role(i,i+1,n)][(x,)] for i,x in enumerate(z.m.shape(w)))
                assert abs(z.q(w)-expected)<1e-12
    assert err<1e-12
    a=[tuple(w) for w in ('abc','def','ghi')];z=[tuple(w) for w in ('jkl','mno','pqr')];tr=[x+y for i,x in enumerate(a) for j,y in enumerate(z) if i!=j]*100;te=[x+y for x,y in zip(a,z)];g=Grammar(tr,32,tuple('abcdefghijklmnopqr'));b=Base(tr,tuple('abcdefghijklmnopqr'));positive=sum(math.log(g.q(w)/b.predict(w,None)[0]) for w in te)/len(te)
    assert positive>0,positive
    return dict(normalization_max_error=err,zero_weight_exact=True,singleton_negative=True,synthetic_positive_gain=positive)
def summary(rows):return dict(tokens=len(rows),types=len({w for _,w,_ in rows}),roots=len({r for r,_,_ in rows}))
def oov(rows,fit):
    vocab={w for _,w,_ in fit};return [z for z in rows if z[1] not in vocab]
def metrics(rows,b,g,whole,weight):
    losses=[0.]*5;blocks=C.defaultdict(list);hits=0
    for r,w,p in rows:
        s,o=b.predict(w,p);q=g.q(w);a,gc=mixed(s,o,q,weight);_,wc=mixed(s,o,whole.q(w),.25);c=.5*s+o
        logs=[math.log(x) for x in (s,c,wc,a,gc)];losses=[x-y for x,y in zip(losses,logs)];blocks[r].append(logs[3]-logs[0]);hits+=g.multi_coverage(w)
    n=len(rows);l=dict(zip(('S','C','W','G','GC'),[x/n for x in losses]));return dict(summary(rows),nll=l,G_S=l['S']-l['G'],GC_C=l['C']-l['GC'],GC_W=l['W']-l['GC'],multi_chunk_hits=hits),blocks
def run(raw):
    ctl=controls();rows=read(raw);train=[z for z in rows if not held(z[0],'EXP0029-root-v1')];test=[z for z in rows if held(z[0],'EXP0029-root-v1')];fit=[z for z in train if not held(z[0],'EXP0032b-inner-v1')];val=[z for z in train if held(z[0],'EXP0032b-inner-v1')];assert not ({r for r,_,_ in fit}&{r for r,_,_ in val}) and not ({r for r,_,_ in train}&{r for r,_,_ in test});vo=oov(val,fit);words=[w for _,w,_ in fit];b=Base(words);cached=[(w,b.predict(w,p)[0]) for _,w,p in vo];grid=[]
    for merges,classes in itertools.product((32,64,128),(27,32)):
        g=Grammar(words,merges,ABC,PAIRS if classes==27 else ());qs=[(s,g.q(w)) for w,s in cached]
        for weight in (.25,.5,.75,1.):
            gain=sum(math.log(((1-weight)*s+weight*q)/s) for s,q in qs)/len(qs);grid.append(dict(merges=merges,classes=classes,weight=weight,inventory=len(g.inv),gain=gain))
    top=max(x['gain'] for x in grid);winner=min((x for x in grid if top-x['gain']<=1e-12),key=lambda x:(x['merges'],x['classes'],x['weight']));words=[w for _,w,_ in train];b=Base(words);g=Grammar(words,winner['merges'],ABC,PAIRS if winner['classes']==27 else ());whole=Whole(words);all_,_=metrics(test,b,g,whole,winner['weight']);oo,blocks=metrics(oov(test,train),b,g,whole,winner['weight']);assert all(abs(oo['nll'][k]-v)<1e-9 for k,v in [('S',11.740734717509724),('C',12.008504037349509),('W',12.035869856265881)])
    bb=[(sum(blocks[r]),len(blocks[r])) for r in sorted(blocks)];obs=sum(x for x,_ in bb);rng=random.Random(330031);boot=[]
    for _ in range(400):
        z=rng.choices(bb,k=len(bb));boot.append(sum(x for x,_ in z)/sum(n for _,n in z))
    boot.sort();rng=random.Random(330032);ex=sum(sum(x*rng.choice((-1,1)) for x,_ in bb)>=obs for _ in range(999));p=(1+ex)/1000;support=len(vo)>=100 and summary(vo)['roots']>=8 and oo['tokens']>=100 and oo['roots']>=8
    gates=dict(support=support,inner=winner['gain']>=.02,outer_G_S=oo['G_S']>=.02,outer_GC_C=oo['GC_C']>=.02,outer_GC_W=oo['GC_W']>=.02,bootstrap=boot[9]>0,p=p<=.05,inventory=len(g.inv)<=160 and len(g.inv)<len(whole.c))
    return dict(experiment='EXP-0033',source_sha256=SHA,split={k:summary(v) for k,v in [('fit',fit),('validation',val),('validation_oov',vo),('train',train),('test',test)]},grid=grid,winner=winner,all=all_,oov=oo,complexity=dict(chunks=len(g.inv),multi_chunks=sum(len(x)>1 for x in g.inv),chunk_symbols=sum(map(len,g.inv)),role_nonzero=len(g.c),role_cells=4*len(g.inv),emission_entries=len(g.m.em),whole_entries=len(whole.c),whole_symbols=sum(map(len,whole.c)),baseline_bigram_nonzero=len(b.b),baseline_slot_nonzero=len(b.s)),root_gains=[dict(root=r,tokens=len(v),gain=sum(v)/len(v)) for r,v in sorted(blocks.items())],bootstrap=[boot[9],boot[389]],p=p,exceedances=ex,controls=dict(ctl,baseline_replay=True,root_disjoint=True),gates=gates,decision='PASS' if all(gates.values()) else 'NOT_MET' if support else 'INCONCLUSIVE')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('output');a=p.parse_args();Path(a.output).write_text(json.dumps(run(Path(a.input).read_bytes()),sort_keys=True,indent=2)+'\n')

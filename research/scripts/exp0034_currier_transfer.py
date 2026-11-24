import collections as C, hashlib, itertools, json, math, random, re, sys
from pathlib import Path
SHA='bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'
COMPS=('cph','cfh','ckh','cth','ch','sh'); ABC=tuple(sorted(tuple('abcdefghijklmnopqrstuvwxyz')+COMPS)); PAIRS=(('ch','sh'),('k','t'),('f','p'),('l','r'),('cph','cth'))
def seg(w):
    out=[];i=0
    while i<len(w):
        x=next((x for x in COMPS if w.startswith(x,i)),w[i]);out.append(x);i+=len(x)
    return tuple(out)
def held(r):return int.from_bytes(hashlib.sha256(('EXP0029-root-v1|'+r).encode()).digest()[:8],'big')%5==0
def read(raw):
    assert len(raw)==411671 and hashlib.sha256(raw).hexdigest()==SHA
    s=raw.decode('ascii');assert s.startswith('#=IVTFF Eva- 2.0 M 5\n') and '# Version 3b of 13/05/2025' in s[:220]
    meta={};rows=[]
    for line in s.splitlines():
        h=re.match(r'^<(f\d+[rv]\d?)>\s*<!([^>]*)>',line)
        if h:
            d=dict(re.findall(r'\$([A-Z])=([^\s>]+)',h[2]));assert h[1] not in meta or meta[h[1]]==d;meta[h[1]]=d;continue
        m=re.match(r'^<(f[0-9]+[rv][0-9]?)\.([0-9]+),([^>]*)>\s*(.*)$',line)
        if not m:continue
        f,_,k,body=m.groups()
        if not re.search(r'P0\b',k):continue
        r=re.match(r'f\d+',f)[0];d=meta.get(f,{})
        for w in re.sub(r'<[^>]*>','.!.' ,body).split('.'):
            if re.fullmatch(r'[a-z]{4,}',w):rows.append((r,seg(w),d.get('L','?'),d.get('I','?'),d.get('H','?')))
    assert len(rows)==24351;return rows,len(meta)
def slot(i,n):return 'first' if i==0 else 'last' if i==n-1 else 'second' if i==1 else 'penultimate' if i==n-2 else 'middle'
def role(i,j,n):return 'whole' if i==0 and j==n else 'first' if i==0 else 'last' if j==n else 'middle'
ROLES=('whole','first','last','middle')
class Base:
    def __init__(self,words,abc=ABC):
        self.abc=abc;self.u=C.Counter();self.b=C.Counter();self.bd=C.Counter();self.s=C.Counter();self.sd=C.Counter()
        for w in words:
            for i,x in enumerate(w):
                l=w[i-1] if i else '^';k=slot(i,len(w));self.u[x]+=1;self.b[l,x]+=1;self.bd[l]+=1;self.s[k,l,x]+=1;self.sd[k,l]+=1
        self.N=sum(self.u.values())
    def predict(self,w):
        n=len(w);s=1.
        for i,x in enumerate(w):
            l=w[i-1] if i else '^';k=slot(i,n);g=(self.u[x]+.5)/(self.N+.5*len(self.abc));pb=(self.b[l,x]+10*g)/(self.bd[l]+10);s*=(self.s[k,l,x]+20*pb)/(self.sd[k,l]+20)
        return s
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
class Grammar:
    def __init__(self,words,merges,abc=ABC,pairs=PAIRS):
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
def controls():
    abc=('a','b','c');words=[tuple(w) for w in ('ac','bc','aca','bca','acb','ccc')]*4;err=0.
    for pairs in ((),(('a','b'),)):
        g=Grammar(words,32,abc,pairs);b=Base(words,abc)
        for n in range(1,6):
            total=0.
            for w in itertools.product(abc,repeat=n):
                q=g.q(w);total+=q;s=b.predict(w);assert (1-0)*s+0*q==s
            err=max(err,abs(total-1))
    assert err<1e-12
    a=[tuple(w) for w in ('abc','def','ghi')];z=[tuple(w) for w in ('jkl','mno','pqr')];tr=[x+y for i,x in enumerate(a) for j,y in enumerate(z) if i!=j]*100;te=[x+y for x,y in zip(a,z)];g=Grammar(tr,32,tuple('abcdefghijklmnopqr'),());b=Base(tr,tuple('abcdefghijklmnopqr'));positive=sum(math.log(g.q(w)/b.predict(w)) for w in te)/len(te);assert positive>0
    return dict(normalization_error=err,synthetic_gain=positive,zero_weight=True)
def stat(rows):
    return dict(tokens=len(rows),types=len({x[1] for x in rows}),roots=len({x[0] for x in rows}),lengths=dict(sorted(C.Counter(len(x[1]) for x in rows).items())),sections=dict(sorted(C.Counter(x[3] for x in rows).items())),hands=dict(sorted(C.Counter(x[4] for x in rows).items())))
def scope(rows,herbal=False):
    pool=[x for x in rows if x[2] in ('A','B') and (not herbal or x[3]=='H')];train={d:[x for x in pool if x[2]==d and not held(x[0])] for d in 'AB'};test={d:[x for x in pool if x[2]==d and held(x[0])] for d in 'AB'};assert not ({x[0] for d in 'AB' for x in train[d]}&{x[0] for d in 'AB' for x in test[d]})
    vocab={x[1] for d in 'AB' for x in train[d]};oov={d:[x for x in test[d] if x[1] not in vocab] for d in 'AB'};bins={d:C.defaultdict(list) for d in 'AB'}
    for d in 'AB':
        for x in train[d]:bins[d][len(x[1])].append(x[1])
    counts={n:min(len(bins['A'][n]),len(bins['B'][n])) for n in sorted(set(bins['A'])|set(bins['B']))};counts={n:c for n,c in counts.items() if c};scores={d:[[0.]*4 for x in oov[d]] for d in 'AB'};sizes=[]
    for i in range(5):
        rng=random.Random(34000+i);sample={d:[] for d in 'AB'}
        for n,c in counts.items():
            for d in 'AB':sample[d].extend(rng.sample(bins[d][n],c))
        assert C.Counter(map(len,sample['A']))==C.Counter(map(len,sample['B']))
        models={d:(Base(sample[d]),Grammar(sample[d],128)) for d in 'AB'};sizes.append({d:len(models[d][1].inv) for d in 'AB'})
        for d in 'AB':
            other='B' if d=='A' else 'A'
            for j,(_,w,*_) in enumerate(oov[d]):
                vals=[]
                for src in (d,other):
                    b,g=models[src];s=b.predict(w);vals.extend((math.log(s),math.log(.5*s+.5*g.q(w))))
                for k,v in enumerate(vals):scores[d][j][k]+=v/5
    results={}
    for ix,d in enumerate('AB'):
        rr=oov[d];sc=scores[d];N=len(rr);loss=[-sum(x[k] for x in sc)/N for k in range(4)] if N else [None]*4;groups=C.defaultdict(list)
        for x,v in zip(rr,sc):groups[x[0]].append(v[3]-v[2])
        bb=[(sum(groups[r]),len(groups[r])) for r in sorted(groups)];obs=sum(x for x,_ in bb);boot=[];rng=random.Random(34031+ix)
        if bb:
            for _ in range(400):
                z=rng.choices(bb,k=len(bb));boot.append(sum(x for x,_ in z)/sum(n for _,n in z))
        boot.sort();rng=random.Random(34041+ix);ex=sum(sum(x*rng.choice((-1,1)) for x,_ in bb)>=obs for _ in range(999)) if bb else 999;p=(1+ex)/1000
        results[d]=dict(nll=dict(zip(('own_S','own_G','cross_S','cross_G'),loss)),cross_gain=loss[2]-loss[3] if N else None,own_gain=loss[0]-loss[1] if N else None,penalty=loss[3]-loss[1] if N else None,bootstrap=[boot[9],boot[389]] if boot else None,p=p,exceedances=ex,positive_roots=sum(x>0 for x,_ in bb),root_gains=[dict(root=r,tokens=len(groups[r]),gain=sum(groups[r])/len(groups[r])) for r in sorted(groups)])
    return dict(train={d:stat(train[d]) for d in 'AB'},test={d:stat(test[d]) for d in 'AB'},oov={d:stat(oov[d]) for d in 'AB'},matched_counts=counts,matched_tokens=sum(counts.values()),inventory_sizes=sizes,results=results)
def run(raw):
    ctl=controls();rows,headers=read(raw);primary=scope(rows);secondary=scope(rows,True);gates={}
    for d in 'AB':
        o=primary['oov'][d];r=primary['results'][d];gates[d]=dict(support=o['tokens']>=100 and o['roots']>=4,gain=r['cross_gain'] is not None and r['cross_gain']>=.02,bootstrap=r['bootstrap'] is not None and r['bootstrap'][0]>0,p=r['p']<=.05,penalty=r['penalty'] is not None and r['penalty']<=.5)
    support=all(g['support'] for g in gates.values());return dict(experiment='EXP-0034',source_sha256=SHA,headers=headers,accepted_tokens=len(rows),unknown_tokens=sum(x[2] not in 'AB' for x in rows),primary=primary,herbal=secondary,controls=ctl,gates=gates,decision='PASS' if all(all(g.values()) for g in gates.values()) else 'NOT_MET' if support else 'INCONCLUSIVE')
if __name__=='__main__':Path(sys.argv[2]).write_text(json.dumps(run(Path(sys.argv[1]).read_bytes()),sort_keys=True,indent=2)+'\n')

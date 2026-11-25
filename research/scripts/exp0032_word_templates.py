import argparse, collections as C, hashlib, itertools, json, math, random, re
from pathlib import Path
SHA='bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'
COMPS=('cph','cfh','ckh','cth','ch','sh')
ABC=tuple(sorted(tuple('abcdefghijklmnopqrstuvwxyz')+COMPS))
PAIRS=(('ch','sh'),('k','t'),('f','p'),('l','r'),('cph','cth'))
def seg(w):
    out=[]; i=0
    while i<len(w):
        x=next((x for x in COMPS if w.startswith(x,i)),w[i]);out.append(x);i+=len(x)
    return tuple(out)
def held(r):return int.from_bytes(hashlib.sha256(('EXP0029-root-v1|'+r).encode()).digest()[:8],'big')%5==0
def read(b):
    assert len(b)==411671 and hashlib.sha256(b).hexdigest()==SHA
    s=b.decode('ascii');assert s.startswith('#=IVTFF Eva- 2.0 M 5\n') and '# Version 3b of 13/05/2025' in s[:220]
    rows=[];c=C.Counter()
    for line in s.splitlines():
        m=re.match(r'^<(f[0-9]+[rv][0-9]?)\.([0-9]+),([^>]*)>\s*(.*)$',line)
        if not m:continue
        f,_,k,body=m.groups()
        if not re.search(r'P0\b',k):continue
        c['p0_loci']+=1;r=re.match(r'f\d+',f)[0];prev=None
        for w in re.sub(r'<[^>]*>','.!.' ,body).split('.'):
            if not re.fullmatch(r'[a-z]{4,}',w):prev=None;continue
            u=seg(w);rows.append((r,u,prev));prev=u;c['accepted_tokens']+=1
    return rows,dict(c)
def slot(i,n):return 'first' if i==0 else 'last' if i==n-1 else 'second' if i==1 else 'penultimate' if i==n-2 else 'middle'
class Model:
    def __init__(self,words,abc=ABC,pairs=PAIRS,cap=128):
        self.abc=abc;self.cls={x:x for x in abc}
        for a,b in pairs:self.cls[b]=a
        self.members=C.defaultdict(list)
        for x in abc:self.members[self.cls[x]].append(x)
        self.u=C.Counter();self.b=C.Counter();self.bd=C.Counter();self.s=C.Counter();self.sd=C.Counter()
        for w in words:
            for i,x in enumerate(w):
                l=w[i-1] if i else '^';k=slot(i,len(w));self.u[x]+=1;self.b[l,x]+=1;self.bd[l]+=1;self.s[k,l,x]+=1;self.sd[k,l]+=1
        self.N=sum(self.u.values());self.em={x:(self.u[x]+.5)/(sum(self.u[z]+.5 for z in self.members[self.cls[x]])) for x in abc}
        def top(c):return dict(sorted(c.items(),key=lambda kv:(-kv[1],kv[0]))[:cap])
        self.templates=top(C.Counter(self.shape(w) for w in words));self.lex=top(C.Counter(words));self.td=C.Counter();self.ld=C.Counter()
        for w,n in self.templates.items():self.td[len(w)]+=n
        for w,n in self.lex.items():self.ld[len(w)]+=n
    def shape(self,w):return tuple(self.cls[x] for x in w)
    def predict(self,w,prev=None):
        n=len(w);b=s=1.
        for i,x in enumerate(w):
            l=w[i-1] if i else '^';k=slot(i,n);g=(self.u[x]+.5)/(self.N+.5*len(self.abc));pb=(self.b[l,x]+10*g)/(self.bd[l]+10);ps=(self.s[k,l,x]+20*pb)/(self.sd[k,l]+20);b*=pb;s*=ps
        q=self.templates.get(self.shape(w),0)/self.td[n]*math.prod(self.em[x] for x in w) if self.td[n] else s
        t=.5*q+.5*s if self.td[n] else s
        lex=self.lex.get(w,0)/self.ld[n] if self.ld[n] else s
        if prev is not None and len(prev)==n:
            d=sum(x!=y for x,y in zip(w,prev));copy=.5 if d==0 else .5/(n*(len(self.abc)-1)) if d==1 else 0.
        else:copy=s
        return (b,s,t,.5*s+.25*lex+.25*copy,.5*t+.25*lex+.25*copy)
def controls():
    abc=('a','b','c');pairs=(('a','b'),);words=[tuple(w) for w in ('ac','bc','aca','bca','acb','ccc')];m=Model(words,abc,pairs)
    err=0.
    for n in (2,3,4):
        for prev in (None,tuple('a'*n),tuple('a'*(n+1))):
            sums=[sum(m.predict(w,prev)[i] for w in itertools.product(abc,repeat=n)) for i in range(5)];err=max(err,max(abs(x-1) for x in sums))
    assert err<1e-12
    target=[(x,'c',y,'c') for x in 'ab' for y in 'ab'];train=target*100+[tuple(w) for w in ('cccc','ccaa','ccbb','aaaa','bbbb')]*60
    p=Model(train,abc,pairs);gain=sum(math.log(p.predict(w)[2]/p.predict(w)[1]) for w in target)/len(target);assert gain>0
    z=Model(words,abc,pairs,0)
    assert all(z.predict(w)[1]==z.predict(w)[2] and z.predict(w)[3]==z.predict(w)[4] for w in words)
    return {'normalization_max_error':err,'positive_gain':gain,'negative_no_templates':True}
def run(b):
    ctl=controls();rows,parser=read(b);tr=[z for z in rows if not held(z[0])];te=[z for z in rows if held(z[0])];assert not ({r for r,_,_ in tr}&{r for r,_,_ in te});vocab={w for _,w,_ in tr};m=Model([w for _,w,_ in tr]);oov=[z for z in te if z[1] not in vocab]
    def summary(rr):
        n=len(rr);ws={w for _,w,_ in rr};loss=[0.]*5;blocks=C.defaultdict(list)
        for r,w,p in rr:
            lp=[math.log(x) for x in m.predict(w,p)];loss=[a-b for a,b in zip(loss,lp)];blocks[r].append(lp[4]-lp[3])
        return {'tokens':n,'types':len(ws),'roots':len(blocks),'nll':dict(zip(('B','S','T','C','TC'),[x/n for x in loss])),'T_minus_S':(loss[1]-loss[2])/n,'TC_minus_C':(loss[3]-loss[4])/n,'template_token_hits':sum(m.shape(w) in m.templates for _,w,_ in rr),'template_type_hits':sum(m.shape(w) in m.templates for w in ws)},blocks
    a,_=summary(tr);t,_=summary(te);o,blocks=summary(oov);bb=[(sum(blocks[r]),len(blocks[r])) for r in sorted(blocks)];obs=sum(x for x,_ in bb);rng=random.Random(320031);boot=[]
    for _ in range(400):
        z=rng.choices(bb,k=len(bb));boot.append(sum(x for x,_ in z)/sum(n for _,n in z))
    boot.sort();rng=random.Random(320032);null=[sum(x*rng.choice((-1,1)) for x,_ in bb) for _ in range(999)];ex=sum(x>=obs for x in null);p=(1+ex)/1000
    gates={'support':o['tokens']>=100 and o['roots']>=8,'gain':o['TC_minus_C']>=.020,'bootstrap':boot[9]>0,'p':p<=.05}
    return {'experiment':'EXP-0032','source_sha256':SHA,'parser':parser,'controls':ctl,'train':a,'test':t,'oov':o,'template_entries':len(m.templates),'lexicon_entries':len(m.lex),'classes':len(m.members),'emission_entries':len(m.em),'bigram_nonzero':len(m.b),'slot_bigram_nonzero':len(m.s),'bootstrap_gain':[boot[9],boot[389]],'null_exceedances':ex,'p_empirical':p,'gates':gates,'decision':'PASS' if all(gates.values()) else 'NOT_MET' if gates['support'] else 'INCONCLUSIVE'}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('output');a=ap.parse_args();Path(a.output).write_text(json.dumps(run(Path(a.input).read_bytes()),sort_keys=True,indent=2)+'\n')

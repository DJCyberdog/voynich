import argparse, collections as C, hashlib, itertools, json, math, random, re
from pathlib import Path
SHA='bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'
COMPS=('cph','cfh','ckh','cth','ch','sh'); ABC=tuple(sorted(tuple('abcdefghijklmnopqrstuvwxyz')+COMPS))
PAIRS=(('ch','sh'),('k','t'),('f','p'),('l','r'),('cph','cth'))
CAPS=(32,64,128,256,512,1024,2048,None); WEIGHTS=(.05,.1,.25,.5,.75,.9)
ORIG=(128,.5,27,'frequency','global')
def seg(w):
    out=[]; i=0
    while i<len(w):
        x=next((x for x in COMPS if w.startswith(x,i)),w[i]);out.append(x);i+=len(x)
    return tuple(out)
def held(r,prefix):return int.from_bytes(hashlib.sha256((prefix+'|'+r).encode()).digest()[:8],'big')%5==0
def read(b):
    assert len(b)==411671 and hashlib.sha256(b).hexdigest()==SHA
    s=b.decode('ascii');assert s.startswith('#=IVTFF Eva- 2.0 M 5\n') and '# Version 3b of 13/05/2025' in s[:220]
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
def ranked(c):return sorted(c.items(),key=lambda kv:(-kv[1],kv[0]))
class Base:
    def __init__(self,words,abc=ABC):
        self.abc=abc;self.u=C.Counter();self.b=C.Counter();self.bd=C.Counter();self.s=C.Counter();self.sd=C.Counter()
        for w in words:
            for i,x in enumerate(w):
                l=w[i-1] if i else '^';k=slot(i,len(w));self.u[x]+=1;self.b[l,x]+=1;self.bd[l]+=1;self.s[k,l,x]+=1;self.sd[k,l]+=1
        self.N=sum(self.u.values());self.lex=dict(ranked(C.Counter(words))[:128]);self.ld=C.Counter()
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
class Templates:
    def __init__(self,words,abc,pairs,cap,selection,mode):
        self.cls={x:x for x in abc};self.mode=mode
        for a,b in pairs:self.cls[b]=a
        self.members=C.defaultdict(list)
        for x in abc:self.members[self.cls[x]].append(x)
        self.u=C.Counter();self.s=C.Counter()
        for w in words:
            for i,x in enumerate(w):self.u[x]+=1;self.s[slot(i,len(w)),x]+=1
        rr=ranked(C.Counter(self.shape(w) for w in words))
        if selection=='diversity':
            buckets=C.defaultdict(list)
            for w,n in rr:buckets[len(w)].append((w,n))
            rr=[buckets[l][i] for i in range(max(map(len,buckets.values()))) for l in sorted(buckets) if i<len(buckets[l])]
        self.templates=dict(rr[:cap]);self.td=C.Counter()
        for w,n in self.templates.items():self.td[len(w)]+=n
    def shape(self,w):return tuple(self.cls[x] for x in w)
    def q(self,w):
        n=len(w)
        if not self.td[n]:return None
        v=self.templates.get(self.shape(w),0)/self.td[n]
        if not v:return 0.
        for i,x in enumerate(w):
            k=slot(i,n);u=(lambda z:self.u[z]) if self.mode=='global' else (lambda z:self.s[k,z])
            v*=(u(x)+.5)/sum(u(z)+.5 for z in self.members[self.cls[x]])
        return v
    def hit(self,w):return self.shape(w) in self.templates
def mixed(s,other,q,weight):
    t=s if q is None else (1-weight)*s+weight*q
    return t,.5*t+other
def controls():
    abc=('a','b','c');words=[tuple(w) for w in ('ac','bc','aca','bca','acb','ccc')];b=Base(words,abc);err=0.
    for pairs,sel,mode in itertools.product(((('a','b'),),()),('frequency','diversity'),('global','slot')):
        t=Templates(words,abc,pairs,128,sel,mode)
        for n in (2,3,4):
            for prev in (None,tuple('a'*n),tuple('a'*(n+1))):
                sums=[0.,0.,0.]
                for w in itertools.product(abc,repeat=n):
                    s,o=b.predict(w,prev);q=t.q(w);a,c=mixed(s,o,q,.5);assert mixed(s,o,q,0)==(s,.5*s+o);sums[0]+=a;sums[1]+=c;sums[2]+=.5*s+o
                err=max(err,max(abs(x-1) for x in sums))
    assert err<1e-12
    targets=[(x,'c',y,'c') for x in 'ab' for y in 'ab'];train=targets*100+[tuple(w) for w in ('cccc','ccaa','ccbb','aaaa','bbbb')]*60
    b=Base(train,abc);t=Templates(train,abc,(('a','b'),),128,'frequency','global');gain=sum(math.log(mixed(*b.predict(w,None),t.q(w),.5)[0]/b.predict(w,None)[0]) for w in targets)/len(targets);assert gain>0
    return {'normalization_max_error':err,'zero_weight_exact':True,'synthetic_positive_gain':gain}
def data_summary(rows):return {'tokens':len(rows),'types':len({w for _,w,_ in rows}),'roots':len({r for r,_,_ in rows})}
def oov(rows,fit):
    vocab={w for _,w,_ in fit};return [z for z in rows if z[1] not in vocab]
def grid(fit,val):
    words=[w for _,w,_ in fit];b=Base(words);cached=[(w,*b.predict(w,p)) for _,w,p in val];results=[]
    for cap,classes,sel,mode in itertools.product(CAPS,(27,32),('frequency','diversity'),('global','slot')):
        t=Templates(words,ABC,PAIRS if classes==27 else (),cap,sel,mode);q=[(s,o,t.q(w)) for w,s,o in cached];hits=sum(t.hit(w) for w,_,_ in cached)
        for weight in WEIGHTS:
            gain=sum(math.log(mixed(s,o,x,weight)[1]/(.5*s+o)) for s,o,x in q)/len(q)
            results.append({'config':[cap,weight,classes,sel,mode],'gain':gain,'hits':hits,'entries':len(t.templates)})
    return results
def order(x):
    cap,w,c,s,m=x['config'];return (float('inf') if cap is None else cap,w,c,s!='frequency',m!='global')
def best(rows):
    g=max(x['gain'] for x in rows);return min((x for x in rows if g-x['gain']<=1e-12),key=order)
def eval_config(fit,test,conf):
    cap,w,c,sel,mode=conf;words=[w0 for _,w0,_ in fit];b=Base(words);t=Templates(words,ABC,PAIRS if c==27 else (),cap,sel,mode)
    def calc(rows):
        loss=[0.]*4;blocks=C.defaultdict(list)
        for r,word,p in rows:
            s,o=b.predict(word,p);a,tc=mixed(s,o,t.q(word),w);logs=[math.log(x) for x in (s,a,.5*s+o,tc)];loss=[x-y for x,y in zip(loss,logs)];blocks[r].append(logs[3]-logs[2])
        n=len(rows);return dict(data_summary(rows),gain=(loss[2]-loss[3])/n,T_minus_S=(loss[0]-loss[1])/n,nll=dict(zip(('S','T','C','TC'),[x/n for x in loss])),hits=sum(t.hit(word) for _,word,_ in rows),type_hits=sum(t.hit(word) for word in {v for _,v,_ in rows})),blocks
    all_,_=calc(test);oo,blocks=calc(oov(test,fit));bb=[(sum(blocks[r]),len(blocks[r])) for r in sorted(blocks)];obs=sum(x for x,_ in bb);rng=random.Random(320031);boot=[]
    for _ in range(400):
        z=rng.choices(bb,k=len(bb));boot.append(sum(x for x,_ in z)/sum(n for _,n in z))
    boot.sort();rng=random.Random(320032);ex=sum(sum(x*rng.choice((-1,1)) for x,_ in bb)>=obs for _ in range(999));return {'config':list(conf),'entries':len(t.templates),'lexicon_entries':len(b.lex),'classes':len(t.members),'emission_mode':mode,'bigram_nonzero':len(b.b),'slot_bigram_nonzero':len(b.s),'all':all_,'oov':oo,'bootstrap':[boot[9],boot[389]],'p':(1+ex)/1000,'exceedances':ex}
def run(raw):
    ctl=controls();rows=read(raw);train=[z for z in rows if not held(z[0],'EXP0029-root-v1')];test=[z for z in rows if held(z[0],'EXP0029-root-v1')];fit=[z for z in train if not held(z[0],'EXP0032b-inner-v1')];val=[z for z in train if held(z[0],'EXP0032b-inner-v1')];assert len({r for r,_,_ in fit}&{r for r,_,_ in val})==0 and not ({r for r,_,_ in train}&{r for r,_,_ in test});vo=oov(val,fit);g=grid(fit,vo);assert len(g)==384;winner=best(g)
    # Selection completed before either outer score is calculated.
    selected=eval_config(train,test,winner['config']);orig=eval_config(train,test,ORIG);assert abs(orig['oov']['gain']-(-.35256954002597846))<1e-9
    factors={str(i):[best([x for x in g if x['config'][i]==v]) for v in vals] for i,vals in enumerate((CAPS,WEIGHTS,(27,32),('frequency','diversity'),('global','slot')))}
    support=len(vo)>=100 and data_summary(vo)['roots']>=8 and selected['oov']['tokens']>=100 and selected['oov']['roots']>=8;gates={'support':support,'validation_gain':winner['gain']>=.02,'outer_gain':selected['oov']['gain']>=.02,'bootstrap':selected['bootstrap'][0]>0,'p':selected['p']<=.05}
    return {'experiment':'EXP-0032b','source_sha256':SHA,'controls':dict(ctl,original_replay=True),'split':{k:data_summary(v) for k,v in [('fit',fit),('validation',val),('validation_oov',vo),('train',train),('test',test)]},'grid':g,'factor_best':factors,'winner':winner,'validation_positive':sum(x['gain']>0 for x in g),'validation_ge_threshold':sum(x['gain']>=.02 for x in g),'selected':selected,'original':orig,'gates':gates,'decision':'PASS' if all(gates.values()) else 'NOT_MET' if support else 'INCONCLUSIVE'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('output');a=p.parse_args();Path(a.output).write_text(json.dumps(run(Path(a.input).read_bytes()),sort_keys=True,indent=2)+'\n')

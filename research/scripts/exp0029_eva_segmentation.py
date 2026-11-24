#!/usr/bin/env python3
import argparse, collections as C, hashlib, json, math, random, re
from pathlib import Path
SHA='bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'
SCHEMES={'ASCII':(), 'BENCH':('ch','sh'), 'COMPOUND':('cph','cfh','ckh','cth','ch','sh')}
ABC=tuple('abcdefghijklmnopqrstuvwxyz')
def h(s): return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8],'big')
def root(f): return re.match(r'f\d+',f)[0]
def held(f): return h('EXP0029-root-v1|'+root(f))%5==0
def segment(w, compounds):
    out=[]; i=0
    while i<len(w):
        s=next((c for c in compounds if w.startswith(c,i)),w[i]);out.append((s,i));i+=len(s)
    return out
def read(b):
    assert len(b)==411671 and hashlib.sha256(b).hexdigest()==SHA
    s=b.decode('ascii');assert s.startswith('#=IVTFF Eva- 2.0 M 5\n') and '# Version 3b of 13/05/2025' in s[:220]
    rows=[];counts=C.Counter()
    for line in s.splitlines():
        m=re.match(r'^<(f[0-9]+[rv][0-9]?)\.([0-9]+),([^>]*)>\s*(.*)$',line)
        if not m:continue
        f,n,k,body=m.groups()
        if not re.search(r'P0\b',k):continue
        counts['p0_loci']+=1
        for j,w in enumerate(re.sub(r'<[^>]*>','.',body.replace('<->','.').replace('<~>','.')).split('.')):
            if not w:continue
            counts['candidate_segments']+=1
            if not re.fullmatch(r'[a-z]{4,}',w):counts['rejected_segments']+=1;continue
            counts['accepted_tokens']+=1;rows.append((f,n,j,w))
    return rows,dict(counts)
class Model:
    def __init__(self,triples,alphabet):
        self.a=alphabet;self.z=C.Counter();self.l=C.Counter();self.nl=C.Counter();self.p=C.Counter();self.np=C.Counter();self.cache={}
        for l,x,r in triples:self.z[x]+=1;self.l[l,x]+=1;self.nl[l]+=1;self.p[l,r,x]+=1;self.np[l,r]+=1
        self.N=sum(self.z.values())
    def prob(self,l,r):
        if (l,r) not in self.cache:
            p1={x:(self.l[l,x]+10*(self.z[x]+.5)/(self.N+.5*len(self.a)))/(self.nl[l]+10) for x in self.a}
            p2={x:(self.p[l,r,x]+15*p1[x])/(self.np[l,r]+15) for x in self.a}
            self.cache[l,r]=p1,p2
        return self.cache[l,r]
    def gain(self,l,x,r):
        a,b=self.prob(l,r);return math.log(b[x]/a[x])
def slot(i,n): return 'start' if i==1 else 'end' if i==n-2 else 'middle'
def make(f,u,i):return (root(f),u[i-1][0],u[i][0],u[i+1][0],slot(i,len(u)))
def score(m,rows,full=False):
    if not rows:return {'n':0}
    ds=[]; hit=[0,0]; groups=C.defaultdict(list); strata=C.defaultdict(list)
    for j,(f,l,x,r,s) in enumerate(rows):
        a,b=m.prob(l,r);d=math.log(b[x]/a[x]);ds.append(d);groups[f].append(d);strata[f,l,s].append(j)
        for k,p in enumerate((a,b)):hit[k]+=min(p,key=lambda v:(-p[v],v))==x
    n=len(rows);obs=sum(ds)/n;out={'n':n,'roots':len(groups),'gain':obs,'left_top1':hit[0]/n,'bridge_top1':hit[1]/n}
    if not full:return out
    movable=sum(len(g) for g in strata.values() if len({rows[j][3] for j in g})>1)/n
    rng=random.Random(290125);null=[]
    for _ in range(199):
        rr=[row[3] for row in rows]
        for g in strata.values():
            v=[rr[j] for j in g];rng.shuffle(v)
            for j,x in zip(g,v):rr[j]=x
        null.append(sum(m.gain(l,x,r2) for (_,l,x,_,_),r2 in zip(rows,rr))/n)
    rng=random.Random(290126);blocks=list(groups.values());boot=[]
    for _ in range(400):
        bs=[rng.choice(blocks) for _ in blocks];boot.append(sum(map(sum,bs))/sum(map(len,bs)))
    boot.sort();p=(1+sum(x>=obs for x in null))/200
    eligible=n>=100 and len(groups)>=5 and movable>=.30
    out.update(movable_fraction=movable,null_mean=sum(null)/199,null_max=max(null),p=p,bootstrap=[boot[9],boot[389]],eligible=eligible,passed=eligible and obs>=.020 and boot[9]>0 and p<=.01)
    return out
def control(a):
    o={}
    for positive in (True,False):
        rng=random.Random(290127 if positive else 290128);train=[];test=[]
        for i in range(15000):
            l=rng.randrange(4);r=rng.randrange(4);x=(l+r)%4 if positive else l
            if rng.random()<.1:x=rng.randrange(4)
            (test if i%5==0 else train).append((ABC[l],ABC[x],ABC[r]))
        m=Model(train,a);g=sum(m.gain(*z) for z in test)/len(test);o['positive' if positive else 'negative']=g
    o['passed']=o['positive']>.12 and o['negative']<.04;return o
def run(b):
    rows,counts=read(b);train=[z for z in rows if not held(z[0])];test=[z for z in rows if held(z[0])];voc={z[3] for z in train};common=[];aligned=[]
    for f,n,j,w in test:
        if w in voc:continue
        us={k:segment(w,v) for k,v in SCHEMES.items()}
        if min(map(len,us.values()))<3:continue
        seed=h(f'EXP0029-mask-v1|{f}|{n}|{j}');common.append((f,seed,us))
        choices=[]
        for i in range(1,len(w)-1):
            if all(any(u[k-1:k+2]==[(w[i-1],i-1),(w[i],i),(w[i+1],i+1)] for k in range(1,len(u)-1)) for u in us.values()):choices.append(i)
        if choices:aligned.append((f,choices[seed%len(choices)],us))
    out={'experiment':'EXP-0029','source_sha256':SHA,'parser_counts':counts,'train_tokens':len(train),'test_tokens':len(test),'train_roots':len({root(z[0]) for z in train}),'test_roots':len({root(z[0]) for z in test}),'train_wordtypes':len(voc),'common_oov':len(common),'aligned_oov':len(aligned),'schemes':{}}
    for k,c in SCHEMES.items():
        a=ABC+c;co=control(a);assert co['passed'];trip=[]
        for *_,w in train:
            u=[x[0] for x in segment(w,c)];trip.extend(zip(u,u[1:],u[2:]))
        m=Model(trip,a);rr=[make(f,us[k],1+seed%(len(us[k])-2)) for f,seed,us in common];aa=[]
        for f,i,us in aligned:
            u=us[k];idx=next(j for j,(_,off) in enumerate(u) if off==i);aa.append(make(f,u,idx))
        out['schemes'][k]={'alphabet_size':len(a),'train_positions':len(trip),'primary':score(m,rr,True),'aligned':score(m,aa),'controls':co}
    p=[v['primary'] for v in out['schemes'].values()];out['decision']='PASS' if all(v['passed'] for v in p) else 'INCONCLUSIVE' if not all(v['eligible'] for v in p) else 'NOT_MET';return out
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('output');a=ap.parse_args();Path(a.output).write_text(json.dumps(run(Path(a.input).read_bytes()),indent=2,sort_keys=True)+'\n')

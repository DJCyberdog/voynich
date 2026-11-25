import collections as C, hashlib, json, math, random, re, sys
from pathlib import Path
import exp0037_roles as r
import exp0036a_native as n
import exp0034_currier_transfer as d

def assess(vals,idx):
    blocks=C.defaultdict(list)
    for root,g in vals:blocks[root].append(g)
    N=len(vals);bb=[(sum(v),len(v)) for _,v in sorted(blocks.items())]
    if not N:return dict(N=0,roots=0,gain=None,decision='INCONCLUSIVE')
    obs=sum(x for x,_ in bb);R=random.Random(377000+idx);boot=[]
    for _ in range(400):
        z=R.choices(bb,k=len(bb));boot.append(sum(x for x,_ in z)/sum(k for _,k in z))
    boot.sort();R=random.Random(378000+idx);p=(1+sum(sum(x*R.choice((-1,1)) for x,_ in bb)>=obs for _ in range(999)))/1000
    gates=dict(support=N>=100 and len(bb)>=8,gain=obs/N>=.02,bootstrap=boot[9]>0,p=p<=.05)
    return dict(N=N,roots=len(bb),gain=obs/N,bootstrap=[boot[9],boot[389]],p=p,positive_roots=sum(x>0 for x,_ in bb),gates=gates,decision='PASS' if all(gates.values()) else 'NOT_MET' if gates['support'] else 'INCONCLUSIVE')
def joint(ds):return 'NOT_MET' if 'NOT_MET' in ds else 'INCONCLUSIVE' if 'INCONCLUSIVE' in ds else 'PASS'
def prof(obs,role):
    p=r.profile(obs);return dict(N=p['occurrences'],roots=p['roots'],purity=p['counts'][role]/p['occurrences'] if p['occurrences'] else 0)
def ok(p,N,roots,purity):return p['N']>=N and p['roots']>=roots and p['purity']>=purity

def labels(raw):
    out=[];meta={}
    for line in raw.decode('ascii').splitlines():
        h=re.match(r'^<(f\d+[rv]\d?)>\s*<!([^>]*)>',line)
        if h:meta[h[1]]=dict(re.findall(r'\$([A-Z])=([^\s>]+)',h[2]));continue
        m=re.match(r'^<(f[0-9]+[rv][0-9]?)\.([0-9]+),([^>]*)>\s*(.*)$',line)
        if not m or not re.search(r'P0\b',m[3]):continue
        root=re.match(r'f\d+',m[1])[0]
        for w in re.sub(r'<[^>]*>','.!.' ,m[4]).split('.'):
            a=n.units(w)
            if a is not None and len(a)>=2:out.append((root,a,meta.get(m[1],{}).get('L','?')))
    return out

def decompose(w,P,S):
    choices=[(p,s) for p in P for s in S if (p or s) and w[:len(p)]==p and (not s or w[-len(s):]==s) and len(w)-len(p)-len(s)>=2]
    if not choices:return None
    p,s=min(choices,key=lambda v:(-sum(map(len,v)),-len(v[0]),v));core=w[len(p):len(w)-len(s)]
    assert p+core+s==w and len(core)>=2
    return core,(p,s)
class CatModel:
    def __init__(self,rows,options,kind):
        self.options=options;self.kind=kind;self.b=C.Counter();self.bd=C.Counter();self.m=C.Counter();self.md=C.Counter()
        for _,core,(p,s) in rows:
            if kind=='suffix' and (not p or not s):continue
            k=(len(core),len(p),len(s));y=(p,s) if kind=='frame' else s;x=core if kind=='frame' else p
            self.b[k,y]+=1;self.bd[k]+=1;self.m[k,x,y]+=1;self.md[k,x]+=1
    def predict(self,core,frame):
        p,s=frame;k=(len(core),len(p),len(s));y=frame if self.kind=='frame' else s;x=core if self.kind=='frame' else p
        opts=self.options[len(p),len(s)];assert y in opts
        B=(self.b[k,y]+.5)/(self.bd[k]+.5*len(opts));M=(self.m[k,x,y]+20*B)/(self.md[k,x]+20)
        return B,M

def run(zraw,graw,eraw):
    ctl=r.controls();z,g=n.read(zraw,'ZL'),n.read(graw,'GC');abc=tuple(sorted(z['alphabet']|g['alphabet']));assert len(abc)==253
    gs=[d.Grammar([w for _,w in x['train']],128,abc,n.PAIRS) for x in (z,g)];inv={c for c in set(gs[0].inv)&set(gs[1].inv) if len(c)>1};assert len(inv)==102
    shape=gs[0].m.shape;assert gs[0].m.cls==gs[1].m.cls;assert not ({root for x in (z,g) for root,_ in x['train']}&{root for x in (z,g) for root,_ in x['test']})
    train=[list(r.occurrences(x['train'],shape,inv)) for x in (z,g)];test=[list(r.occurrences(x['test'],shape,inv)) for x in (z,g)];tr=list(map(r.grouped,train));te=list(map(r.grouped,test));models=list(map(r.RoleModel,train));vocab={shape(w) for x in (z,g) for _,w in x['train']}
    cand={}
    for c in sorted(inv):
        p=[r.profile(x[c]) for x in tr]
        if all(x['occurrences']>=30 and x['roots']>=5 and x['purity']>=.8 and x['unique'] for x in p) and p[0]['dominant']==p[1]['dominant']:cand[c]=r.ROLES.index(p[0]['dominant'])
    assert len(cand)==58
    keys=('ZL_to_GC','GC_to_ZL');A={}
    for i,key in enumerate(keys):
        m=models[i];v=C.defaultdict(list)
        for root,w,c,role,_ in test[1-i]:
            _,B,_=m.predict(w,c);M=B if len(c)==2 else r.interp(m.chunk,(len(w),len(c),c),B,20);assert abs(sum(M)-1)<1e-12
            v[len(c)].append((root,math.log(M[role]/B[role])))
        assert all(x==0 for _,x in v[2]);A[key]={str(k):assess(v[k],10*i+k) for k in (2,3,4)};A[key]['long']=assess(v[3]+v[4],10*i+5)
    A['decision']=joint([A[k]['long']['decision'] for k in keys]);ctl['two_code_exact_zero']=True
    def covered(c,L,obs,role):
        selected=[x for x in obs if x[3]==role];hits=0
        for _,w,_,_,(left,right) in selected:
            i=len(left);N=len(w)
            for j in range(max(0,i+len(c)-len(L)),min(i,N-len(L))+1):
                rr=0 if j==0 else 1 if j+len(L)==N else 2
                if len(L)<N and rr==role and w[j:j+len(L)]==L:hits+=1;break
        return hits/len(selected) if selected else 0
    dropped={}
    for c,role in cand.items():
        for L in sorted(cand,key=lambda x:(-len(x),x)):
            if len(L)<=len(c) or cand[L]!=role or not any(L[j:j+len(c)]==c for j in range(len(L)-len(c)+1)):continue
            cov=[covered(c,L,x[c],role) for x in tr]
            if min(cov)>=.8:dropped[c]=(L,cov);break
    keep={c:role for c,role in cand.items() if c not in dropped};counts={x:dict(retained=0,validated=0,recombining=0) for x in r.ROLES};profiles=[]
    for c,role in keep.items():
        p=[prof(x[c],role) for x in te];valid=all(ok(x,10,3,.7) for x in p);ctx=[{x[4] for x in h[c] if x[3]==role} for h in tr];union=ctx[0]|ctx[1];nov=[{x[4] for x in h[c] if x[3]==role and x[1] not in vocab and x[4] not in union} for h in te];prod=valid and min(map(len,ctx))>=5 and min(map(len,nov))>=3
        ct=counts[r.ROLES[role]];ct['retained']+=1;ct['validated']+=valid;ct['recombining']+=prod;profiles.append(dict(chunk=list(c),role=r.ROLES[role],test=p,validated=valid,recombining=prod))
    val=sum(x['validated'] for x in counts.values());B=dict(retained=len(keep),dropped=len(dropped),validated=val,counts=counts,profiles=profiles,redundancy=[dict(short=list(c),long=list(L),cover=cov) for c,(L,cov) in dropped.items()],decision='PASS' if val>=.7*len(keep) and all(counts[x]['recombining']>=1 for x in ('prefix','suffix')) else 'NOT_MET')
    P=[()]+[c for c,role in keep.items() if role==0];S=[()]+[c for c,role in keep.items() if role==1];opts=C.defaultdict(list);sopts={}
    for p in P:
        for s in S:opts[len(p),len(s)].append((p,s))
    for a,b in opts:sopts[a,b]=sorted({s for p,s in opts[a,b]})
    def dec(rows):
        out=[]
        for root,w in rows:
            ans=decompose(shape(w),P,S)
            if ans:out.append((root,*ans))
        return out
    dt=[dec(x['train']) for x in (z,g)];de=[dec(x['test']) for x in (z,g)]
    corecounts=[C.Counter(c for _,c,_ in x) for x in dt];frames=[C.defaultdict(set) for _ in dt];framecores=[C.defaultdict(set) for _ in dt]
    for i,x in enumerate(dt):
        for _,c,f in x:frames[i][c].add(f);framecores[i][f].add(c)
    supported={c for c in corecounts[0].keys()&corecounts[1].keys() if all(corecounts[i][c]>=5 and len(frames[i][c])>=2 for i in range(2))};Cr={};D={}
    for i,key in enumerate(keys):
        model=CatModel(dt[i],opts,'frame');target=[x for x in de[1-i] if x[1] in supported];scores=[]
        for root,c,f in target:
            b,m=model.predict(c,f);scores.append((root,math.log(m/b)))
        novel={(c,f) for _,c,f in target if all(f not in frames[j][c] and bool(framecores[j][f]-{c}) for j in range(2))};Cr[key]=dict(assess(scores,30+i),novel_pairs=len(novel));Cr[key]['novel_gate']=len(novel)>=10
        m=CatModel(dt[i],sopts,'suffix');scores=[]
        for root,c,(p,s) in de[1-i]:
            if p and s:
                b,q=m.predict(c,(p,s));scores.append((root,math.log(q/b)))
        D[key]=assess(scores,40+i)
    Cr['supported_cores']=len(supported);Cr['train_decomposed']=list(map(len,dt));Cr['test_decomposed']=list(map(len,de));Cr['decision']=joint([joint([Cr[k]['decision'],'PASS' if Cr[k]['novel_gate'] else 'NOT_MET']) for k in keys]);D['decision']=joint([D[k]['decision'] for k in keys])
    pp=('p',);ss=('s',);tt=('t',);cc=('a','a');dd=('b','b');oo={(1,1):[(pp,ss),(pp,tt)]};toy=CatModel([('r',cc,(pp,ss))]*100+[('r',dd,(pp,tt))]*100,oo,'frame');probs=[toy.predict(cc,f) for f in oo[1,1]];assert all(abs(sum(x[j] for x in probs)-1)<1e-12 for j in range(2));assert probs[0][1]>probs[0][0];assert toy.predict(('c','c'),(pp,ss))[0]==toy.predict(('c','c'),(pp,ss))[1];ctl['categorical_positive_gain']=math.log(probs[0][1]/probs[0][0]);ctl['categorical_normalization']=True
    labeled=[]
    for raw,x in [(zraw,z),(graw,g)]:
        lr=labels(raw);assert [(a,b) for a,b,_ in lr]==x['rows'];labeled.append(lr)
    def domainobs(rows,hold):
        for root,w,label in rows:
            if label in ('A','B') and d.held(root)==hold:
                for ob in r.occurrences([(root,w)],shape,inv):yield ob,label
    ltr=[list(domainobs(x,False)) for x in labeled];lte=[list(domainobs(x,True)) for x in labeled];E={}
    for i,key in enumerate(keys):
        m=r.RoleModel([x for x,_ in ltr[i]]);cnt=C.defaultdict(lambda:[0,0,0]);scores=C.defaultdict(list)
        for (_,w,c,role,_),label in ltr[i]:cnt[len(w),len(c),c,label][role]+=1
        for (root,w,c,role,_),label in lte[1-i]:
            _,_,p=m.predict(w,c);q=r.interp(cnt,(len(w),len(c),c,label),p,20);assert abs(sum(q)-1)<1e-12;scores[label].append((root,math.log(q[role]/p[role])))
        E[key]=dict(assess(scores['A']+scores['B'],50+i),strata={label:assess(scores[label],52+2*i+j) for j,label in enumerate('AB')})
    E['decision']=joint([E[k]['decision'] for k in keys]);ctl['folio_metadata_replay']=True
    assert hashlib.sha256(eraw).hexdigest()==d.SHA;erows,_=d.read(eraw);assert len(erows)==24351
    code={'A1':'o','A2':'y','A3':'a','A4':'u','B1':'d','B2':'l','B3':'m','B4':'g','B5':'j','B6':'z','C1':'l','C2':'s','D1':'q','E1':'i','E2':'n','F1':'in','F2':'ii','F3':'il','G1':'iin','G2':'iii','G3':'iil','H1':'iiin','H2':'iiiin','H3':'iiil','J1':'e','J2':'b','Ja':'c','Jb':'h','K1':'ch','K2':'ee','M1':'eee','N1':'eeee','P1':'f','Q1':'k','T1':'cph','T2':'cfh','U1':'ckh','X1':'x','X2':'v'}
    ec={b:a for a,b in d.PAIRS};eshape=lambda w:tuple(ec.get(x,x) for x in w);mapped=C.defaultdict(list);unmapped=short=0
    for c,role in keep.items():
        if not all(x in code for x in c):unmapped+=1;continue
        v=eshape(d.seg(''.join(code[x] for x in c)))
        if len(v)<2:short+=1;continue
        mapped[v].append((c,role))
    collision=sum(len(x) for x in mapped.values() if len(x)>1);unique={v:x[0] for v,x in mapped.items() if len(x)==1};etr=C.defaultdict(list);ete=C.defaultdict(list)
    for root,w,*_ in erows:
        w=eshape(w);group=ete if d.held(root) else etr
        for v in unique:
            k=len(v)
            if len(w)<=k:continue
            for j in range(len(w)-k+1):
                if w[j:j+k]==v:group[v].append((root,w,v,0 if j==0 else 1 if j+k==len(w) else 2,(w[:j],w[j+k:])))
    fc={x:dict(mapped=0,validated=0) for x in r.ROLES};fp=[]
    for v,(c,role) in unique.items():
        a=prof(etr[v],role);b=prof(ete[v],role);valid=ok(a,30,5,.8) and ok(b,10,3,.7);fc[r.ROLES[role]]['mapped']+=1;fc[r.ROLES[role]]['validated']+=valid;fp.append(dict(sta=list(c),eva=list(v),role=r.ROLES[role],train=a,test=b,validated=valid))
    fv=sum(x['validated'] for x in fc.values());F=dict(mapped=len(unique),unmapped=unmapped,short=short,collision=collision,validated=fv,counts=fc,profiles=fp,decision='PASS' if unique and fv>=.7*len(unique) and all(fc[x]['validated']>=1 for x in ('prefix','suffix')) else 'NOT_MET' if unique else 'INCONCLUSIVE');assert len(unique)+unmapped+short+collision==len(keep)
    results=dict(a=A,b=B,c=Cr,d=D,e=E,f=F);return dict(experiment='EXP-0037a-f',decision=joint([x['decision'] for x in results.values()]),results=results,controls=dict(ctl,source_hashes=True,root_disjoint=True,inventory_replay=True,train_candidate_replay=True),shared_chunks=102,train_candidates=58)
if __name__=='__main__':Path(sys.argv[4]).write_text(json.dumps(run(*[Path(p).read_bytes() for p in sys.argv[1:4]]),sort_keys=True,indent=2)+'\n')

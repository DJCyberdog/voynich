import collections as C, hashlib, json, math, random, re, sys, zlib
from pathlib import Path
import numpy as np
from sklearn.metrics import adjusted_rand_score as ari
PIN=['8438ba1c45f47fe1d06b5262cbcdf60ce69158a0edbd4dd802612896f3217e2a','0c0d1eea4b5ab87f8a65fb7f4346864cd90758ad993812b4f2122b3899d4ac88']
NAMES=['ZL','GC']; DIR=['ZL_to_GC','GC_to_ZL']
def parse(raw,i):
    assert hashlib.sha256(raw).hexdigest()==PIN[i]
    meta={};lines={};rows=[]
    for line in raw.decode('ascii').splitlines():
        h=re.match(r'^<(f\d+[rv]\d?)>\s*<!([^>]*)>',line)
        if h:meta[h[1]]=dict(re.findall(r'\$([A-Z])=([^\s>]+)',h[2]));continue
        m=re.match(r'^<(f[0-9]+[rv][0-9]?)\.([0-9]+),([^>]*)>\s*(.*)$',line)
        if not m or not re.search(r'P0\b',m[3]):continue
        f=m[1];root=re.match(r'f\d+',f)[0];d=meta.get(f,{}).get('L','?');d=d if d in ('A','B') else '?';start='<%>' in m[4];pieces=[w for w in re.sub(r'<[^>]*>','.!.' ,m[4]).split('.') if w];idx=[j for j,w in enumerate(pieces) if w!='!'];ls=lines.setdefault(f,[]);line_id=len(ls);ls.append((start,[]));hist=[]
        for j,w in enumerate(pieces):
            if not re.fullmatch(r'(?:[A-Z][0-9a-z]){2,}',w):hist=[];ls[-1][1].append(None);continue
            pos='single' if len(idx)==1 else 'first' if j==idx[0] else 'last' if j==idx[-1] else 'middle'
            x=(root,f,line_id,w,len(w)//2,d,pos,start,tuple(hist[-3:]));rows.append(x);ls[-1][1].append(x);hist.append(w)
    assert len(rows)==[28464,30691][i] and sum(map(len,lines.values()))==3885
    return rows,lines

def held(root,split):return int.from_bytes(hashlib.sha256((['EXP0029-root-v1','EXP0037t-root-v1'][split]+'|'+root).encode()).digest()[:8],'big')%5==0

def km(X,k):
    X=np.asarray(X,dtype=float);assert len(X)>=k;centers=[X[0]]
    for _ in range(k-1):centers.append(X[np.argmax(np.min(((X[:,None,:]-np.array(centers)[None,:,:])**2).sum(2),axis=1))])
    centers=np.array(centers)
    for _ in range(30):
        lab=np.argmin(((X[:,None,:]-centers[None,:,:])**2).sum(2),axis=1);new=np.array([X[lab==i].mean(0) if np.any(lab==i) else centers[i] for i in range(k)])
        if np.array_equal(new,centers):break
        centers=new
    return np.argmin(((X[:,None,:]-centers[None,:,:])**2).sum(2),axis=1),centers

def assess(vals,split,idx,direction,minimum=100):
    blocks=C.defaultdict(list)
    for r,v in vals:blocks[r].append(v)
    N=len(vals);bb=[(sum(v),len(v)) for _,v in sorted(blocks.items())];roots=len(bb)
    if not N:return dict(N=0,roots=0,gain=None,decision='INCONCLUSIVE')
    obs=sum(a for a,b in bb);seed=100*split+10*idx+direction;R=random.Random(381000+seed);boot=[]
    for _ in range(400):
        z=R.choices(bb,k=roots);boot.append(sum(a for a,b in z)/sum(b for a,b in z))
    boot.sort();R=random.Random(382000+seed);p=(1+sum(sum(a*R.choice((-1,1)) for a,b in bb)>=obs-1e-12 for _ in range(999)))/1000;gates=dict(support=N>=minimum and roots>=8,gain=obs/N>=.02,bootstrap=boot[9]>0,p=p<=.05)
    return dict(N=N,roots=roots,gain=obs/N,bootstrap=[boot[9],boot[389]],p=p,positive_roots=sum(a>0 for a,b in bb),gates=gates,decision='PASS' if all(gates.values()) else 'NOT_MET' if gates['support'] else 'INCONCLUSIVE')
def joint(v):return 'NOT_MET' if 'NOT_MET' in v else 'INCONCLUSIVE' if 'INCONCLUSIVE' in v else 'PASS'
class Model:
    def __init__(self,rows,keys,K=9):
        self.keys=keys;self.K=K;self.c=[C.Counter() for _ in keys];self.n=[C.Counter() for _ in keys]
        for x in rows:
            for i,key in enumerate(keys):k=key(x);self.c[i][k,x['c']]+=1;self.n[i][k]+=1
    def predict(self,x):
        p=1/self.K;out=[]
        for i,key in enumerate(self.keys):
            k=key(x);p=(self.c[i][k,x['c']]+20*p)/(self.n[i][k]+20);out.append(p)
        return out

def normalized(m,x):
    v=[m.predict(dict(x,c=c)) for c in range(m.K)];assert all(abs(sum(p)-1)<1e-12 for p in zip(*v))
def hist(seq,K):return np.bincount(seq,minlength=K).astype(float)
def hell(h):return np.sqrt(h/h.sum())
def js(a,b):
    a=(a+.5)/(a.sum()+.5*len(a));b=(b+.5)/(b.sum()+.5*len(b));m=(a+b)/2;return float(.5*np.sum(a*np.log(a/m))+.5*np.sum(b*np.log(b/m)))
def split_run(raw,split):
    train=[[x for x in r if not held(x[0],split)] for r,ls in raw];test=[[x for x in r if held(x[0],split)] for r,ls in raw];assert not ({x[0] for a in train for x in a}&{x[0] for a in test for x in a})
    cnt=[C.Counter(x[3] for x in a) for a in train];vocab=sorted(w for w in cnt[0].keys()&cnt[1].keys() if min(c[w] for c in cnt)>=5);vi={w:i for i,w in enumerate(vocab)};top=sorted(vocab,key=lambda w:(-sum(c[w] for c in cnt),w))[:32];ti={w:i for i,w in enumerate(top)};D=len(top)+1
    mats=[]
    for a in train:
        h=np.full((len(vocab),2,D),.5)
        for x in a:
            w=x[3];prev=x[-1][-1] if x[-1] else None
            if prev is None:continue
            if w in vi:h[vi[w],0,ti.get(prev,D-1)]+=1
            if prev in vi:h[vi[prev],1,ti.get(w,D-1)]+=1
        mats.append(h)
    feat=lambda h:np.sqrt(h/h.sum(axis=2,keepdims=True)).reshape(len(vocab),-1)
    labs=[km(feat(h),8)[0] for h in mats];pool=km(feat(mats[0]+mats[1]-.5),8)[0];obs=float(ari(*labs));R=random.Random(380001);groups=C.defaultdict(list)
    for i,w in enumerate(vocab):groups[len(w)//2].append(i)
    null=[]
    for _ in range(199):
        p=labs[1].copy()
        for inds in groups.values():v=[int(p[i]) for i in inds];R.shuffle(v);p[inds]=v
        null.append(float(ari(labs[0],p)))
    p=(1+sum(v>=obs for v in null))/200;L=dict(vocab=len(vocab),ari=obs,permutation_p=p,null_mean=sum(null)/len(null),class_sizes=[hist(a,8).astype(int).tolist() for a in [*labs,pool]],decision='PASS' if len(vocab)>=100 and obs>=.1 and p<=.05 else 'NOT_MET' if len(vocab)>=100 else 'INCONCLUSIVE')
    cm={w:int(pool[i]) for w,i in vi.items()};cat=lambda w:cm.get(w,8);wc=lambda w:vi.get(w,len(vocab));K=len(vocab)+1
    encoded=[];folios=[]
    for i,(rs,ls) in enumerate(raw):
        fd={};out=[]
        for f,lines in ls.items():
            fl=[]
            for li,(_,line) in enumerate(lines):
                rr=[x for x in line if x is not None];seq=[cat(x[3]) for x in rr];fl.append(seq)
                far=[c for old in fl[max(0,li-4):max(0,li-1)] for c in old];prev=fl[li-1] if li else [];dominant=lambda a: min(C.Counter(a).items(),key=lambda kv:(-kv[1],kv[0]))[0] if a else None
                for root,fol,j,w,n,d,pos,start,h in rr:
                    out.append(dict(r=root,f=fol,j=j,w=w,c=cat(w),n=n,d=d,pos=pos,start=start,h=tuple(map(cat,h)),pl=len(h[-1])//2 if h else 0,far=dominant(far),prev=dominant(prev)))
            rr=[x for _,line in lines for x in line if x is not None]
            if rr:fd[f]=dict(r=rr[0][0],d=rr[0][5],classes=fl,words=[wc(x[3]) for x in rr],starts=[s for s,_ in lines])
        assert [x['w'] for x in out]==[x[3] for x in rs];encoded.append(out);folios.append(fd)
    tr=[[x for x in a if not held(x['r'],split)] for a in encoded];te=[[x for x in a if held(x['r'],split)] for a in encoded]
    base=[lambda x:(x['n'],),lambda x:(x['n'],x['d']),lambda x:(x['n'],x['d'],x['pos'])];mkeys=base+[lambda x:(x['n'],x['d'],x['pos'],x['pl']),lambda x:(x['n'],x['d'],x['pos'],x['pl'],x['h'][-1])];nkeys=mkeys+[lambda x:(x['n'],x['h'][-1],x['far'])];pkeys=base+[lambda x:(x['n'],x['d'],x['pos'],x['start'])];res={'l':L,'m':{},'n':{},'o':{},'p':{},'q':{},'r':{},'s':{}}
    def score(m,rows,idx,i):
        vals=[];b=[];a=[]
        for x in rows:
            p=m.predict(x);vals.append((x['r'],math.log(p[-1]/p[-2])));b.append(-math.log(p[-2]));a.append(-math.log(p[-1]))
        return dict(assess(vals,split,idx,i),baseline_bits=sum(b)/len(b)/math.log(2),model_bits=sum(a)/len(a)/math.log(2)) if b else assess(vals,split,idx,i)
    for i,key in enumerate(DIR):
        a,b=tr[i],te[1-i];aa=[x for x in a if x['h']];bb=[x for x in b if x['h']];M=Model(aa,mkeys);normalized(M,bb[0]);res['m'][key]=score(M,bb,1,i)
        strata=C.defaultdict(list)
        for x in bb:strata[x['r'],x['d'],x['pos'],x['n'],x['pl']].append(x)
        R=random.Random(380100+i);null=[];tables=[]
        for xs in strata.values():
            cs=[x['h'][-1] for x in xs];tables.append((cs,[{c:math.log(M.predict(dict(x,h=(c,)))[-1]/M.predict(x)[-2]) for c in sorted(set(cs))} for x in xs]))
        for _ in range(99):
            t=0.
            for cs,tt in tables:v=cs.copy();R.shuffle(v);t+=sum(q[c] for q,c in zip(tt,v))
            null.append(t/len(bb))
        obs=res['m'][key]['gain'];res['m'][key].update(null_mean=sum(null)/99,permutation_p=(1+sum(x>=obs-1e-12 for x in null))/100)
        N=Model([x for x in aa if x['far'] is not None],nkeys);far=[x for x in bb if x['far'] is not None];res['n'][key]=score(N,far,2,i)
        longkeys=mkeys+[lambda x:(x['n'],x['h'][-2:]),lambda x:(x['n'],x['h'][-3:])];lm=Model([x for x in aa if len(x['h'])==3],longkeys);long=[x for x in bb if len(x['h'])==3];loss=[-sum(math.log(lm.predict(x)[j]) for x in long)/len(long) for j in (4,5,6)];res['n'][key]['long_history_gains']=[loss[0]-v for v in loss[1:]]
        O=Model(a,base);res['o'][key]=score(O,b,3,i);P=Model(a,pkeys);res['p'][key]=score(P,b,4,i);res['p'][key]['start_gain']={str(flag):sum(math.log(P.predict(x)[-1]/P.predict(x)[-2]) for x in b if x['start']==flag)/sum(x['start']==flag for x in b) for flag in (True,False)}
        pm=Model([x for x in a if x['prev'] is not None],pkeys+[lambda x:(x['n'],x['start'],x['prev'])]);prev=[x for x in b if x['prev'] is not None];res['p'][key]['previous_line_gain']=sum(math.log(pm.predict(x)[-1]/pm.predict(x)[-2]) for x in prev)/len(prev)
        docs=[x for x in folios[i].values() if not held(x['r'],split) and len(x['words'])>=20];lab,cent=km([hell(hist(x['words'],K)) for x in docs],6);dh=C.defaultdict(lambda:np.zeros(K));ch=np.zeros((6,K))
        for x,c in zip(docs,lab):v=hist(x['words'],K);dh[x['d']]+=v;ch[c]+=v
        vals=[];counts=C.Counter();targets=0
        for x in folios[1-i].values():
            if not held(x['r'],split) or len(x['words'])<20:continue
            w=x['words'];j=len(w)//2;z=int(np.argmin(((cent-hell(hist(w[:j],K)))**2).sum(1)));B=(dh[x['d']]+.5)/(dh[x['d']].sum()+.5*K);Q=(ch[z]+20*B)/(ch[z].sum()+20);assert abs(Q.sum()-1)<1e-12;targets+=1;counts[z]+=1;vals.extend((x['r'],math.log(Q[c]/B[c])) for c in w[j:])
        res['q'][key]=dict(assess(vals,split,5,i),training_folios=len(docs),target_folios=targets,cluster_sizes=hist(lab,6).astype(int).tolist(),target_cluster_sizes=[counts[j] for j in range(6)])
    for i,name in enumerate(NAMES):
        vals=[];negatives=[];positives=[];cross=[];prior=None
        for x in folios[i].values():
            if not held(x['r'],split):prior=None;continue
            lines=x['classes'];ss=x['starts'];scores=[]
            for j in range(3,len(lines)-2):
                a=[v for l in lines[j-3:j] for v in l];b=[v for l in lines[j:j+3] for v in l]
                if min(len(a),len(b))>=5:scores.append((ss[j],js(hist(a,9),hist(b,9))))
            neg=[v for f,v in scores if not f];pos=[v for f,v in scores if f];negatives+=neg;positives+=pos
            if neg:vals.extend((x['r'],sum((v>w)+.5*(v==w) for w in neg)/len(neg)-.5) for v in pos)
            if prior and prior['d']==x['d'] and len(prior['classes'])>=3 and len(lines)>=3:
                a=[v for l in prior['classes'][-3:] for v in l];b=[v for l in lines[:3] for v in l]
                if min(len(a),len(b))>=5:cross.append(js(hist(a,9),hist(b,9)))
            prior=x
        res['r'][name]=dict(assess(vals,split,6,i,30),auc=.5+sum(v for _,v in vals)/len(vals) if vals else None,positive_boundaries=len(positives),negative_boundaries=len(negatives),adjacent_folio_boundaries=len(cross),adjacent_mean_js=sum(cross)/len(cross) if cross else None,within_mean_js=sum(negatives)/len(negatives) if negatives else None)
        grouped=C.defaultdict(list)
        for f,lines in raw[i][1].items():
            for _,line in lines:
                for x in line:
                    if x is not None and held(x[0],split):grouped[x[0]].append(x)
        R=random.Random(380300+i);vals=[];orig=shuf=origc=shufc=0;total=0
        for root,xs in sorted(grouped.items()):
            strata=C.defaultdict(list)
            for j,x in enumerate(xs):strata[x[5],x[6],x[4]].append(j)
            w=[x[3] for x in xs];N=len(w);template=[];j=0
            for f,lines in raw[i][1].items():
                if re.match(r'f\d+',f)[0]!=root:continue
                template.append('F')
                for _,line in lines:
                    template.append('L')
                    for x in line:
                        if x is None:template.append('!')
                        else:template.append(j);j+=1
            assert j==N
            def size(a,coarse=False):
                b='.'.join((str(cat(a[v])) if coarse else a[v]) if isinstance(v,int) else v for v in template).encode();z=zlib.compress(b,9);assert zlib.decompress(z)==b;return 8*len(z)
            u=size(w);uc=size(w,True);v=[];vc=[]
            for _ in range(20):
                y=w.copy()
                for ids in strata.values():
                    a=[w[j] for j in ids];R.shuffle(a)
                    for j,k in zip(ids,a):y[j]=k
                v.append(size(y));vc.append(size(y,True))
            mean=sum(v)/20;orig+=u;shuf+=mean;origc+=uc;shufc+=sum(vc)/20;total+=N;vals.extend([(root,(mean-u)/N)]*N)
        res['s'][name]=dict(assess(vals,split,7,i),original_bits_per_word=orig/total,shuffle_bits_per_word=shuf/total,coarse_original_bits_per_word=origc/total,coarse_shuffle_bits_per_word=shufc/total)
    for k in 'mnopqrs':res[k]['decision']=joint([v['decision'] for v in res[k].values()])
    return dict(results=res,split=split,train_roots=[len({x[0] for x in a}) for a in train],test_roots=[len({x[0] for x in a}) for a in test],train_tokens=list(map(len,train)),test_tokens=list(map(len,test)),known_test_fraction=[sum(x['c']!=8 for x in a)/len(a) for a in te])

def run(z,g):
    raw=[parse(z,0),parse(g,1)];assert ari([0,0,1,1],[1,1,0,0])==1
    a=[dict(c=i%2,k=i%2) for i in range(200)];m=Model(a,[lambda x:(),lambda x:x['k']],2);normalized(m,a[0]);p=m.predict(a[0]);assert p[1]>p[0] and m.predict(dict(a[0],k=2))[0]==m.predict(dict(a[0],k=2))[1]
    seq=['a','b']*2000;sh=seq.copy();random.Random(9).shuffle(sh);assert len(zlib.compress(''.join(seq).encode(),9))<len(zlib.compress(''.join(sh).encode(),9))
    x,y=[split_run(raw,i) for i in range(2)];a=x['results'];b=y['results'];same=sum(a[k]['decision']==b[k]['decision'] for k in a);positive=[k for k in a if a[k]['decision']=='PASS'];t=dict(agreement=same,initial_pass=positive,replicated_pass=[k for k in positive if b[k]['decision']=='PASS'],decision='PASS' if same>=6 and len(positive)>=2 and all(b[k]['decision']=='PASS' for k in positive) else 'NOT_MET')
    return dict(experiment='EXP-0037l-t',decision=joint([v['decision'] for v in a.values()]+[t['decision']]),primary=x,alternate=y,t=t,controls=dict(source_hashes=True,parser_replay=True,root_disjoint=True,normalization=True,zero_count=True,synthetic_gain=math.log(p[1]/p[0]),ari_identity=True,compression_roundtrip=True,compression_positive=True),numpy=np.__version__,zlib=zlib.ZLIB_VERSION)
if __name__=='__main__':Path(sys.argv[3]).write_text(json.dumps(run(*[Path(p).read_bytes() for p in sys.argv[1:3]]),sort_keys=True,indent=2)+'\n')

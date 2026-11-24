import collections as C, functools, hashlib, json, math, sys
from pathlib import Path
import exp0037_cluster as a
import exp0036a_native as n
import exp0034_currier_transfer as d
from exp0035_competing_generators import Higher

def run(zraw,graw,prior):
    assert hashlib.sha256(prior).hexdigest()=='4c61a9f04d43c3d71f1b200fc7fffe340b34cb2bea617df7c0fd5515118fab82'
    old=json.loads(prior); profiles=old['results']['b']['profiles']; assert len(profiles)==57
    P=[()]+[tuple(x['chunk']) for x in profiles if x['role']=='prefix']; S=[()]+[tuple(x['chunk']) for x in profiles if x['role']=='suffix']; assert (len(P),len(S))==(9,46)
    z,g=n.read(zraw,'ZL'),n.read(graw,'GC');abc=sorted(z['alphabet']|g['alphabet']); mp=d.Mapping([],abc,n.PAIRS);shape=mp.shape; classes=tuple(sorted(mp.members));assert len(classes)==248
    assert not ({r for x in (z,g) for r,w in x['train']}&{r for x in (z,g) for r,w in x['test']})
    @functools.lru_cache(None)
    def dec(w):return a.decompose(w,P,S)
    def data(rows):return [(r,*v) for r,w in rows if (v:=dec(shape(w))) is not None]
    dt=[data(x['train']) for x in (z,g)];de=[data(x['test']) for x in (z,g)];assert list(map(len,dt))==[11709,10291] and list(map(len,de))==[2611,2304]
    counts=[C.Counter((c,f) for _,c,f in rows) for rows in dt]; totals=[C.Counter(c for _,c,f in rows) for rows in dt]; frames=[C.defaultdict(set),C.defaultdict(set)]; framecores=[C.defaultdict(set),C.defaultdict(set)]
    for i,rows in enumerate(dt):
        for _,c,f in rows:frames[i][c].add(f);framecores[i][f].add(c)
    supported=sorted(c for c in totals[0].keys()&totals[1].keys() if all(totals[i][c]>=5 and len(frames[i][c])>=2 for i in range(2)));assert len(supported)==97
    @functools.lru_cache(None)
    def options(c,lp,ls):return tuple((p,s) for p in P for s in S if len(p)==lp and len(s)==ls and dec(p+c+s)==(c,(p,s)))
    def novel(c,f):return all((c,f) not in counts[i] and bool(framecores[i][f]-{c}) for i in range(2))
    def auc(probs,f,neg):return sum((probs[f]>probs[k])+.5*(probs[f]==probs[k]) for k in neg)/len(neg)
    def assess(v,i):return a.assess(v,i)
    G={};L={};I={};groups_out={};keys=['ZL_to_GC','GC_to_ZL']
    for i,key in enumerate(keys):
        h=Higher([shape(w) for _,w in (z,g)[i]['train']],4,80,classes)
        labels={c:min(frames[i][c],key=lambda f:(-counts[i][c,f],f)) for c in supported};groups=C.defaultdict(list)
        for c in supported:groups[labels[c]].append(c)
        groups_out[key]=dict(groups=len(groups),singletons=sum(len(v)==1 for v in groups.values()),sizes=sorted(map(len,groups.values()),reverse=True))
        @functools.lru_cache(None)
        def predict(c,lp,ls):
            opts=options(c,lp,ls);raw={f:h.predict(f[0]+c+f[1]) for f in opts};Z=sum(raw.values());H={f:v/Z for f,v in raw.items()};v={f:counts[i][c,f] for f in opts};w={f:sum(counts[i][other,f] for other in groups[labels[c]] if other!=c) for f in opts};
            G={f:(v[f]+20*H[f])/(sum(v.values())+20) for f in opts};L={f:(w[f]+20*H[f])/(sum(w.values())+20) for f in opts};assert all(abs(sum(p.values())-1)<1e-12 for p in (H,G,L));return H,G,L,sum(w.values())>0
        target=[x for x in de[1-i] if x[1] in supported];testpairs={(c,f) for _,c,f in de[1-i]};gv=[];lv=[];iv=[];gn=[];ln=[];covered=0;positive=set();negcounts=[];ha=[];la=[];novelall=set();single=0
        for root,c,f in target:
            H,U,V,cov=predict(c,len(f[0]),len(f[1]));assert f in H;covered+=cov;single+=len(H)==1
            dg=math.log(U[f]/H[f]);dl=math.log(V[f]/H[f]);gv.append((root,dg));lv.append((root,dl))
            if novel(c,f):
                novelall.add((c,f));gn.append(dg);ln.append(dl)
                neg=[k for k in H if k!=f and (c,k) not in testpairs and novel(c,k)]
                if neg:
                    positive.add((c,f));negcounts.append(len(neg));x=auc(H,f,neg);y=auc(V,f,neg);ha.append(x);la.append(y);iv.append((root,y-x))
        G[key]=dict(assess(gv,70+i),novel_tokens=len(gn),novel_gain=sum(gn)/len(gn),novel_pairs=len(novelall),singleton_options=single)
        L[key]=dict(assess(lv,80+i),novel_gain=sum(ln)/len(ln),other_core_coverage=covered)
        I[key]=dict(assess(iv,90+i),distinct_pairs=len(positive),auc_H=sum(ha)/len(ha) if ha else None,auc_L=sum(la)/len(la) if la else None,mean_negatives=sum(negcounts)/len(negcounts) if negcounts else None)
        if len(positive)<30:I[key]['decision']='INCONCLUSIVE'
    for x in (G,L,I):x['decision']=a.joint([x[k]['decision'] for k in keys])
    # synthetic conditional control: two options, equal H, known core-specific frame counts.
    H=(.5,.5);p=tuple((v+20*b)/120 for v,b in zip((100,0),H));assert abs(sum(p)-1)<1e-12 and p[0]>H[0] and tuple((0+20*b)/20 for b in H)==H
    return dict(experiment='EXP-0037g-i',decision=a.joint([x['decision'] for x in (G,L,I)]),results=dict(g=G,h=L,i=I),supported_cores=len(supported),groups=groups_out,controls=dict(prior_hash=True,source_hashes=True,root_disjoint=True,replay=True,normalization=True,synthetic_gain=math.log(p[0]/H[0]),zero_count=True))
if __name__=='__main__':Path(sys.argv[4]).write_text(json.dumps(run(*[Path(p).read_bytes() for p in sys.argv[1:4]]),sort_keys=True,indent=2)+'\n')

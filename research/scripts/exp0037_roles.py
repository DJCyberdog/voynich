import collections as C, json, math, random, sys
from pathlib import Path
import exp0036a_native as n
import exp0034_currier_transfer as d
ROLES=('prefix','suffix','internal')
def geometric(N,k):
    assert N>k
    return (1/(N-k+1),1/(N-k+1),(N-k-1)/(N-k+1))
def interp(count,key,p,a):
    v=count.get(key,(0,0,0));den=sum(v)+a
    return tuple((x+a*y)/den for x,y in zip(v,p))
def occurrences(rows,shape,inventory):
    for root,word in rows:
        w=shape(word);N=len(w)
        for k in range(2,min(4,N-1)+1):
            for i in range(N-k+1):
                c=w[i:i+k]
                if c in inventory:
                    r=0 if i==0 else 1 if i+k==N else 2
                    yield root,w,c,r,(w[:i],w[i+k:])
class RoleModel:
    def __init__(self,obs):
        self.length=C.defaultdict(lambda:[0,0,0]);self.ends=C.defaultdict(lambda:[0,0,0]);self.chunk=C.defaultdict(lambda:[0,0,0])
        for _,w,c,r,_ in obs:
            a=(len(w),len(c));self.length[a][r]+=1;self.ends[a+(c[0],c[-1])][r]+=1;self.chunk[a+(c,)][r]+=1
    def predict(self,w,c):
        a=(len(w),len(c));p=geometric(*a);b=interp(self.length,a,p,20);b=interp(self.ends,a+(c[0],c[-1]),b,20);m=interp(self.chunk,a+(c,),b,10)
        assert abs(sum(b)-1)<1e-12 and abs(sum(m)-1)<1e-12 and all(x==0 and y==0 for v,x,y in zip(p,b,m) if v==0)
        return p,b,m

def controls():
    # Same endpoints, opposite role preference; no difference in length.
    a=('a','b','c');b=('a','d','c');w=('x',)*5
    obs=[('r',w,c,r,((),())) for c,r in ((a,0),(b,1)) for _ in range(100)]
    m=RoleModel(obs);g=sum(math.log(m.predict(w,c)[2][r]/m.predict(w,c)[1][r]) for c,r in ((a,0),(b,1)))/2
    assert g>0 and m.predict(w,('a','e','c'))[1]==m.predict(w,('a','e','c'))[2]
    assert geometric(3,2)==(.5,.5,0)
    return dict(synthetic_positive_gain=g,zero_count_backoff=True,normalization=True)
def assess(model,obs,i,vocab):
    blocks=C.defaultdict(list);loss=[0.,0.,0.];correct=[0,0,0];oov=[]
    for root,w,c,r,_ in obs:
        pp=model.predict(w,c);lg=[math.log(p[r]) for p in pp];gain=lg[2]-lg[1];blocks[root].append(gain)
        for k,p in enumerate(pp):loss[k]-=lg[k];correct[k]+=max(range(3),key=lambda j:p[j])==r
        if w not in vocab:oov.append(gain)
    N=len(obs);bb=[(sum(v),len(v)) for _,v in sorted(blocks.items())];obs_sum=sum(x for x,_ in bb);rng=random.Random(370031+i);boot=[]
    for _ in range(400):
        z=rng.choices(bb,k=len(bb));boot.append(sum(x for x,_ in z)/sum(k for _,k in z))
    boot.sort();rng=random.Random(370041+i);ex=sum(sum(x*rng.choice((-1,1)) for x,_ in bb)>=obs_sum for _ in range(999));p=(ex+1)/1000;gain=obs_sum/N
    return dict(occurrences=N,roots=len(bb),gain=gain,nll=dict(zip(('geometric','B','M'),[v/N for v in loss])),accuracy=dict(zip(('geometric','B','M'),[v/N for v in correct])),bootstrap=[boot[9],boot[389]],p=p,positive_roots=sum(x>0 for x,_ in bb),oov_occurrences=len(oov),oov_gain=sum(oov)/len(oov) if oov else None,gates=dict(support=N>=100 and len(bb)>=8,gain=gain>=.02,bootstrap=boot[9]>0,p=p<=.05))
def grouped(obs):
    g=C.defaultdict(list)
    for x in obs:g[x[2]].append(x)
    return g
def profile(obs):
    cnt=[sum(x[3]==i for x in obs) for i in range(3)];N=len(obs);r=max(range(3),key=lambda i:cnt[i]);return dict(occurrences=N,roots=len({x[0] for x in obs}),counts=cnt,dominant=ROLES[r],purity=cnt[r]/N if N else 0,unique=cnt.count(cnt[r])==1)
def run(zraw,graw):
    ctl=controls();z=n.read(zraw,'ZL');g=n.read(graw,'GC');abc=tuple(sorted(z['alphabet']|g['alphabet']));assert len(abc)==253
    assert not ({r for x in (z,g) for r,_ in x['train']}&{r for x in (z,g) for r,_ in x['test']})
    gs=[d.Grammar([w for _,w in x['train']],128,abc,n.PAIRS) for x in (z,g)];inv={c for c in set(gs[0].inv)&set(gs[1].inv) if len(c)>1};assert len(inv)==102
    shape=gs[0].m.shape;assert gs[0].m.cls==gs[1].m.cls
    vocab={shape(w) for x in (z,g) for _,w in x['train']}
    train=[list(occurrences(x['train'],shape,inv)) for x in (z,g)];test=[list(occurrences(x['test'],shape,inv)) for x in (z,g)]
    tr=[grouped(x) for x in train];te=[grouped(x) for x in test];models=[RoleModel(x) for x in train]
    transfer={'ZL_to_GC':assess(models[0],test[1],0,vocab),'GC_to_ZL':assess(models[1],test[0],1,vocab)}
    candidates=[];counts={r:dict(selected=0,validated=0,recombining=0) for r in ROLES}
    for c in sorted(inv):
        a=[profile(x[c]) for x in tr]
        if not all(x['occurrences']>=30 and x['roots']>=5 and x['purity']>=.8 and x['unique'] for x in a) or a[0]['dominant']!=a[1]['dominant']:continue
        role=a[0]['dominant'];r=ROLES.index(role);counts[role]['selected']+=1
        b=[profile(x[c]) for x in te];valid=all(x['occurrences']>=10 and x['roots']>=3 and x['counts'][r]/x['occurrences']>=.7 for x in b)
        contexts=[{x[4] for x in h[c] if x[3]==r} for h in tr];union=contexts[0]|contexts[1]
        novel=[{x[4] for x in h[c] if x[3]==r and x[1] not in vocab and x[4] not in union} for h in te]
        productive=valid and all(len(x)>=5 for x in contexts) and all(len(x)>=3 for x in novel)
        counts[role]['validated']+=valid;counts[role]['recombining']+=productive
        candidates.append(dict(chunk=list(c),role=role,train=a,test=b,validated=valid,recombining=productive,train_residual_types=list(map(len,contexts)),novel_residual_types=list(map(len,novel))))
    gates={k:v['gates'] for k,v in transfer.items()};recomb=all(counts[r]['recombining']>=1 for r in ('prefix','suffix'));support=all(g['support'] for g in gates.values());decision='PASS' if recomb and all(all(g.values()) for g in gates.values()) else 'NOT_MET' if support else 'INCONCLUSIVE'
    return dict(experiment='EXP-0037',source_hashes={k:v[0] for k,v in n.PIN.items()},shared_chunks=len(inv),train_occurrences=list(map(len,train)),test_occurrences=list(map(len,test)),transfer=transfer,role_counts=counts,candidates=candidates,recombination_gate=recomb,decision=decision,controls=dict(ctl,source_hashes=True,root_disjoint=True,inventory_replay=True))
if __name__=='__main__':Path(sys.argv[3]).write_text(json.dumps(run(Path(sys.argv[1]).read_bytes(),Path(sys.argv[2]).read_bytes()),sort_keys=True,indent=2)+'\n')

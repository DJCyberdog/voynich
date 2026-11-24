import argparse, json, math, random, statistics as st
from pathlib import Path
import exp0032b_template_sensitivity as b
FRACTIONS=(.05,.10,.20,.40,.60,.80,1.)
def curve_fit(xs,ys,kind):
    fits=[]
    for i in range(1,101):
        A=i/100
        for j in range(-60,61):
            k=10**(j/20)
            pred=[A*(-math.expm1(-k*x)) if kind=='exponential' else A*x/(x+k) for x in xs]
            rmse=math.sqrt(sum((p-y)**2 for p,y in zip(pred,ys))/len(xs))
            fits.append((rmse,A,k))
    rmse,A,k=min(fits); near=[a for e,a,_ in fits if e<=rmse+.01]
    return dict(asymptote=A,parameter=k,rmse=rmse,near_fit_asymptote_range=[min(near),max(near)])
def describe(v):
    return dict(mean=st.mean(v),min=min(v),max=max(v),sd=st.stdev(v))
def evaluate(train,cohorts):
    words=[w for _,w,_ in train]; model=b.Base(words); t=b.Templates(words,b.ABC,b.PAIRS,None,'frequency','global')
    out=dict(train_tokens=len(train),templates=len(t.templates))
    for name,rows in cohorts.items():
        c=tc=s=0.;hits=0
        for _,w,p in rows:
            sp,other=model.predict(w,p);q=t.q(w);_,p_tc=b.mixed(sp,other,q,.25);p_c=.5*sp+other
            assert b.mixed(sp,other,q,0)==(sp,p_c)
            c-=math.log(p_c);tc-=math.log(p_tc);s-=math.log(sp);hits+=t.hit(w)
        n=len(rows);out[name]=dict(coverage=hits/n,hits=hits,C_nll=c/n,TC_nll=tc/n,S_nll=s/n,gain=(c-tc)/n)
    return out
def run(raw):
    controls=b.controls();rows=b.read(raw);train=[z for z in rows if not b.held(z[0],'EXP0029-root-v1')];fit=[z for z in train if not b.held(z[0],'EXP0032b-inner-v1')];val=[z for z in train if b.held(z[0],'EXP0032b-inner-v1')];vo=b.oov(val,fit);roots=sorted({r for r,_,_ in fit});assert not set(roots)&{r for r,_,_ in val};assert len(roots)==67 and len(vo)==445
    cohorts={'oov':vo,'all':val};repeats=[]
    for i in range(20):
        rr=roots[:];random.Random(320300+i).shuffle(rr);seq=[]
        for f in FRACTIONS:
            n=max(1,math.floor(f*len(roots)+.5));chosen=set(rr[:n]);tr=[z for z in fit if z[0] in chosen];v=evaluate(tr,cohorts);v.update(fraction=f,roots=n);seq.append(v)
        assert all(a['oov']['hits']<=z['oov']['hits'] and a['all']['hits']<=z['all']['hits'] for a,z in zip(seq,seq[1:]));repeats.append(seq)
    full=repeats[0][-1];assert all(seq[-1]==full for seq in repeats);assert abs(full['oov']['gain']-.04709693448946789)<1e-9 and full['oov']['hits']==157
    summary=[]
    for j,f in enumerate(FRACTIONS):
        v=[z[j] for z in repeats];s=dict(fraction=f,roots=v[0]['roots']);s.update({k:describe([x[k] for x in v]) for k in ('train_tokens','templates')});s.update({c:{k:describe([x[c][k] for x in v]) for k in ('coverage','hits','C_nll','TC_nll','S_nll','gain')} for c in cohorts});summary.append(s)
    changes={}
    for name,j in [('late',5),('total',0)]:
        dg=[z[-1]['oov']['gain']-z[j]['oov']['gain'] for z in repeats];dc=[z[-1]['oov']['coverage']-z[j]['oov']['coverage'] for z in repeats];changes[name]=dict(gain=describe(dg),coverage=describe(dc),positive_gain=sum(x>0 for x in dg))
    l=changes['late'];support=len(vo)>=100 and len({r for r,_,_ in vo})>=8;gates=dict(support=support,late_gain=l['gain']['mean']>=.01,positive_repeats=l['positive_gain']>=15,late_coverage=l['coverage']['mean']>=.02)
    xs=[x['roots']/len(roots) for x in summary];ys=[x['oov']['coverage']['mean'] for x in summary]
    return dict(experiment='EXP-0032c',source_sha256=b.SHA,fit=b.data_summary(fit),validation=b.data_summary(val),fixed_oov=b.data_summary(vo),repeats=repeats,summary=summary,changes=changes,extrapolation={k:curve_fit(xs,ys,k) for k in ('exponential','rational')},controls=dict(controls,full_replay=True,nested_coverage=True,root_disjoint=True),gates=gates,decision='PASS' if all(gates.values()) else 'NOT_MET' if support else 'INCONCLUSIVE')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('output');a=p.parse_args();Path(a.output).write_text(json.dumps(run(Path(a.input).read_bytes()),sort_keys=True,indent=2)+'\n')

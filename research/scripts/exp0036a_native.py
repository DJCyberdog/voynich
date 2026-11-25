import collections as C, hashlib, json, math, re, sys
from pathlib import Path
import exp0034_currier_transfer as d
import exp0035_competing_generators as e
PIN={'ZL':('8438ba1c45f47fe1d06b5262cbcdf60ce69158a0edbd4dd802612896f3217e2a',472861,5),'GC':('0c0d1eea4b5ab87f8a65fb7f4346864cd90758ad993812b4f2122b3899d4ac88',468252,6)}
PAIRS=(('K1','L1'),('Q1','Q2'),('P1','P2'),('B2','C1'),('T1','U2'))
def units(w):
    return tuple(re.findall(r'[A-Z][0-9a-z]',w)) if re.fullmatch(r'(?:[A-Z][0-9a-z])+',w) else None
def read(raw,name):
    sha,size,m=PIN[name];assert len(raw)==size and hashlib.sha256(raw).hexdigest()==sha
    s=raw.decode('ascii');assert s.splitlines()[0]==f'#=IVTFF STA1 2.0 M {m}'
    rows=[];loci=set();pieces=invalid=short=0;alphabet=set()
    for line in s.splitlines():
        m=re.match(r'^<(f[0-9]+[rv][0-9]?)\.([0-9]+),([^>]*)>\s*(.*)$',line)
        if not m or not re.search(r'P0\b',m[3]):continue
        r=re.match(r'f\d+',m[1])[0];loc=(m[1],m[2]);assert loc not in loci;loci.add(loc)
        for w in re.sub(r'<[^>]*>','.!.' ,m[4]).split('.'):
            if not w or w=='!':continue
            pieces+=1;a=units(w)
            if a is None:invalid+=1;continue
            alphabet.update(a)
            if len(a)<2:short+=1;continue
            rows.append((r,a))
    assert pieces==invalid+short+len(rows)
    train=[x for x in rows if not d.held(x[0])];test=[x for x in rows if d.held(x[0])];return dict(rows=rows,train=train,test=test,vocab={w for _,w in train},loci=loci,alphabet=alphabet,pieces=pieces,invalid=invalid,short=short)
def stat(rows):return dict(tokens=len(rows),types=len({w for _,w in rows}),roots=len({r for r,_ in rows}))
def measure(model,rows):
    h,q=model;loss=[0.]*4;blocks=C.defaultdict(list)
    for r,w in rows:
        H=h.predict(w);Q=q.q(w);J=.5*(H+Q);S=h.base.predict(w);vals=[math.log(x) for x in (H,J,S,Q)]
        loss=[a-b for a,b in zip(loss,vals)];blocks[r].append(vals[1]-vals[0])
    n=len(rows);assert n>0
    res=dict(stat(rows),**dict(zip(('H','J','S','Q'),[v/n for v in loss])),gain=(loss[0]-loss[1])/n,root_gains=[dict(root=r,total=sum(v),tokens=len(v),gain=sum(v)/len(v)) for r,v in sorted(blocks.items())]);return res
def rng(seed):
    s=seed
    while True:
        s^=(s<<13)&0xffffffff;s^=s>>17;s^=(s<<5)&0xffffffff;s&=0xffffffff;yield s/2**32
def test(model,rows,i):
    a=measure(model,rows);r=a['root_gains'];R=rng(361031+i);P=rng(361041+i);boot=[];obs=sum(x['total'] for x in r)
    for _ in range(400):
        z=[r[int(next(R)*len(r))] for _ in r];boot.append(sum(x['total'] for x in z)/sum(x['tokens'] for x in z))
    boot.sort();ex=sum(sum(x['total']*(-1 if next(P)<.5 else 1) for x in r)>=obs for _ in range(999));p=(ex+1)/1000
    return dict(a,bootstrap=[boot[9],boot[389]],p=p,exceedances=ex,positive_roots=sum(x['gain']>0 for x in r),gates=dict(support=a['tokens']>=100 and a['roots']>=8,gain=a['gain']>=.02,bootstrap=boot[9]>0,p=p<=.05))
def run(zraw,graw):
    ctl=e.controls();assert units('B1A3G1')==('B1','A3','G1') and units('AaLe')==('Aa','Le') and all(units(w) is None for w in ('A1,B1','[A1:B1]','A1?','A1B','A1@'))
    z,g=read(zraw,'ZL'),read(graw,'GC');abc=tuple(sorted(z['alphabet']|g['alphabet']));assert all(a in abc and b in abc for a,b in PAIRS)
    assert not ({r for x in (z,g) for r,_ in x['train']}&{r for x in (z,g) for r,_ in x['test']})
    def fit(x):
        words=[w for _,w in x['train']];return e.Higher(words,2,80,abc),d.Grammar(words,128,abc,PAIRS)
    zm,gm=fit(z),fit(g);zo=[x for x in z['test'] if x[1] not in z['vocab']];go=[x for x in g['test'] if x[1] not in g['vocab']];co=[x for x in go if x[1] not in z['vocab']]
    zr,gr,tr=test(zm,zo,0),test(gm,go,1),test(zm,co,2);own=measure(gm,co);gates={k:v['gates'] for k,v in [('zrefit',zr),('grefit',gr),('transfer',tr)]}
    az={c for w in z['vocab'] for c in w};ag={c for w in g['vocab'] for c in w};shared=az&ag;common=[x for x in co if set(x[1])<=shared];rest=[x for x in co if not set(x[1])<=shared]
    sens={k:dict(transfer=measure(zm,x),own=measure(gm,x)) if x else None for k,x in [('shared_training_codes',common),('other',rest)]}
    def stats(x):return dict(all=stat(x['rows']),train=stat(x['train']),test=stat(x['test']),loci=len(x['loci']),pieces=x['pieces'],invalid=x['invalid'],short=x['short'],observed_codes=len(x['alphabet']))
    return dict(experiment='EXP-0036a-native',source_hashes={k:v[0] for k,v in PIN.items()},sources=dict(ZL=stats(z),GC=stats(g),shared_loci=len(z['loci']&g['loci'])),zrefit=zr,grefit=gr,transfer=tr,ownCommon=own,transfer_penalty=tr['J']-own['J'],sensitivity=sens,all=dict(ZL=measure(zm,z['test']),GC=measure(gm,g['test']),transfer=measure(zm,g['test'])),complexity=dict(alphabet=len(abc),singletons=len(abc)-len(PAIRS),ZL=len(zm[1].inv),GC=len(gm[1].inv),shared=len(set(zm[1].inv)&set(gm[1].inv)),ZL_train_codes=len(az),GC_train_codes=len(ag),shared_train_codes=len(shared),ZL_H_cells=len(zm[0].count),GC_H_cells=len(gm[0].count)),controls=dict(ctl,parser=True,source_hashes=True,root_disjoint=True),gates=gates,decision='PASS' if all(all(x.values()) for x in gates.values()) else 'NOT_MET' if all(x['support'] for x in gates.values()) else 'INCONCLUSIVE')
if __name__=='__main__':Path(sys.argv[3]).write_text(json.dumps(run(Path(sys.argv[1]).read_bytes(),Path(sys.argv[2]).read_bytes()),sort_keys=True,indent=2)+'\n')

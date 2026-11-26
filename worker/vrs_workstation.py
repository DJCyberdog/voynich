"""VRS-094 D: opt-in isolated local inference shards; no training or remote jobs."""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import vrs_core as core
import vrs_hardware as h
import vrs_resources as resources

INPUTS = ('manifest','review','alphabet','model_path','report_path')


def partition(weights, capacities):
    """Deterministic whole-region allocation by estimated candidate load."""
    core.require(type(weights) is list and weights and len({r for r,_ in weights})==len(weights),'Invalid regions')
    core.require(type(capacities) is list and 1<=len(capacities)<=len(weights),'Invalid shard count')
    for rid,n in weights:
        core.require(type(rid) is str and rid,'Invalid region ID'); h.positive(n,'region weight')
    for n in capacities: h.positive(n,'capacity')
    loads=[0]*len(capacities); groups=[[] for _ in capacities]
    for pos,(rid,n) in sorted(enumerate(weights),key=lambda x:(-x[1][1],x[0])):
        # Seed each slot, then minimize projected weighted load. Integer cross-products avoid float ties.
        i=next((j for j,g in enumerate(groups) if not g),None)
        if i is None:
            i=0
            for j in range(1,len(groups)):
                if (loads[j]+n)*capacities[i] < (loads[i]+n)*capacities[j]: i=j
        groups[i].append((pos,rid)); loads[i]+=n
    return [[rid for _,rid in sorted(g)] for g in groups]


def budgets(info, work, devices, preset=h.DEFAULT_PRESET, overrides=None):
    """Split a single host envelope, never duplicate host budgets per device.
    devices: list of verified CUDA probe dicts, or None entries for CPU shards.
    VRAM override is per device; all other overrides are aggregate.
    """
    core.require(type(devices) is list and devices,'No devices')
    caps=resources.limits(overrides); n=len(devices)
    cpu=all(d is None for d in devices)
    if not cpu:
        core.require(all(type(d) is dict and d.get('ok') is True for d in devices),'Unverified CUDA device')
        indices=[d['index'] for d in devices]
        for i in indices: h.positive(i,'GPU index',zero=True)
        core.require(len(set(indices))==n,'Duplicate CUDA device')
    preset='quiet' if preset=='silent' else preset
    global_plan=h.plan(info,work,'cpu',preset)
    slots=min(global_plan['cpu_workers'],caps.get('cpu_workers',global_plan['cpu_workers']))
    ram=min(global_plan['ram_budget'],caps.get('ram_bytes',global_plan['ram_budget']))
    disk=min(info['disk_free']-global_plan['disk_reserve'],caps.get('disk_bytes',info['disk_free']))
    core.require(slots>=n,'Insufficient CPU slots for isolated processes')
    # Reserve half for merged report, half for all intermediate reports.
    if disk//2 < max(work['disk'],n*1024**2): raise h.ResourceBlocked('Insufficient shared staging/output budget')
    plans=[]
    for j,d in enumerate(devices):
        child={**caps,'cpu_workers':slots//n+(j<slots%n),'ram_bytes':ram//n,'disk_bytes':disk//(2*n),
               'cache_bytes':min(ram//(20*n),caps.get('cache_bytes',ram)//n)}
        # Per-child report floor; final exact output size is checked separately.
        local=dict(work,disk=1024**2)
        p=resources.plan(dict(info,gpu=d),local,'cpu' if cpu else 'cuda',preset,child)
        child['batch_items']=p['batch_ceiling']
        plans.append(dict(index=None if cpu else d['index'],limits=child,capacity=p['batch_ceiling']))
    return dict(preset=preset,host_ram_budget=ram,cpu_slots=slots,disk_budget=disk,disk_reserve=global_plan['disk_reserve'],plans=plans)


def expected(manifest, review):
    m=core.dataset(manifest); a=core.read(review)
    core.require(a['manifest_sha256']==core.sha(manifest) and set(a['regions'])=={r['id'] for r in m['regions']},'Review binding mismatch')
    rows={r['id']:[tuple(x['box']) for x in sorted(a['regions'][r['id']]['glyphs'],key=lambda x:x['box'][0])] if a['regions'][r['id']]['status']=='single_line' else [] for r in m['regions']}
    excluded={r['id'] for r in m['regions'] if a['regions'][r['id']]['status']!='single_line'}
    return rows,excluded


def merge(reports, groups, expected_rows, excluded, binding, backend):
    core.require(len(reports)==len(groups) and reports,'Missing shard reports')
    flattened=[rid for group in groups for rid in group]
    core.require(len(set(flattened))==len(flattened) and set(flattened)==set(expected_rows),'Shard coverage mismatch')
    rows={}; version=reports[0]['version']
    for result,group in zip(reports,groups):
        core.require(all(result.get(k)==v for k,v in binding.items()) and result['version']==version and result['scientific_status']=='UNADJUDICATED' and result['environment']['device']==backend,'Shard provenance/backend mismatch')
        core.require(result['excluded_regions']==len(set(group)&excluded),'Shard exclusion mismatch')
        wanted=[(rid,b) for rid in group for b in expected_rows[rid]]
        got=[]
        for row in result['rows']:
            core.require(set(row)=={'region_id','box','predicted','distance','margin'},'Unexpected prediction fields')
            key=(row['region_id'],tuple(row['box'])); got.append(key)
            core.require(key not in rows and type(row['predicted']) is str and all(type(row[k]) in (int,float) and math.isfinite(row[k]) for k in ('distance','margin')),'Invalid or duplicate prediction')
            rows[key]=row
        core.require(got==wanted,'Shard row coverage/order mismatch')
    return dict(version=version,scientific_status='UNADJUDICATED',environment=reports[0]['environment'],**binding,
                excluded_regions=len(excluded),rows=[rows[(rid,b)] for rid,boxes in expected_rows.items() for b in boxes])


def probe(root,index):
    """Short-lived isolated CUDA probe; parent never retains GPU allocations."""
    command=[sys.executable,str(Path(h.__file__).resolve()),str(root),'--backend','cuda','--gpu-index',str(index)]
    try:
        result=subprocess.run(command,capture_output=True,text=True,timeout=90,check=True)
        gpu=json.loads(result.stdout)['hardware']['gpu']
        core.require(gpu['ok'] is True and gpu['index']==index,'CUDA probe binding mismatch')
        return gpu
    except (OSError,subprocess.SubprocessError,ValueError,KeyError) as exc:
        raise h.ResourceBlocked(f'CUDA device {index} not verified') from exc


def child(config):
    import torch
    import vrs_inference as v
    a=core.read(config)
    torch.set_num_interop_threads(1)
    v.predict(**a)


def execute(configs, timeout):
    """One fresh OS process per shard, bounded wait, terminate siblings on failure."""
    h.positive(timeout,'timeout')
    children=[]; deadline=time.monotonic()+timeout
    try:
        for cfg in configs:
            slots=core.read(cfg)['limits']['cpu_workers']
            env={**os.environ,**{k:str(slots) for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS')}}
            children.append(subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'child',str(cfg)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        while True:
            codes=[p.poll() for p in children]
            if any(c not in (None,0) for c in codes): raise h.ResourceBlocked('Isolated shard failed; no merged output')
            if all(c==0 for c in codes): return
            if time.monotonic()>=deadline: raise h.ResourceBlocked('Shard deadline exceeded; no merged output')
            time.sleep(.05)
    finally:
        for p in children:
            if p.poll() is None: p.terminate()
        for p in children:
            try: p.wait(timeout=3)
            except subprocess.TimeoutExpired: p.kill(); p.wait()


def run(manifest,review,alphabet,model_path,report_path,output,*,gpu_indices=None,cpu_processes=None,preset=h.DEFAULT_PRESET,limits=None,timeout=3600):
    from PIL import Image
    import vrs_inference as v
    import glyphs as g
    paths={k:str(Path(value).resolve(strict=True)) for k,value in zip(INPUTS,(manifest,review,alphabet,model_path,report_path))}
    output=Path(output).absolute(); root=Path(paths['manifest']).parent
    core.require(output.parent.is_dir() and not os.path.lexists(output),'New output in existing directory required')
    core.require(root.stat().st_dev==output.parent.stat().st_dev,'Output must share workspace filesystem')
    core.require((gpu_indices is None)!=(cpu_processes is None),'Choose explicit CUDA indices or CPU process count')
    h.positive(timeout,'timeout')
    initial={k:core.sha(p) for k,p in paths.items()}
    rows,excluded=expected(paths['manifest'],paths['review'])
    if gpu_indices is not None:
        core.require(type(gpu_indices) is list and gpu_indices and len(gpu_indices)<=len(rows),'Invalid CUDA indices')
        for i in gpu_indices: h.positive(i,'GPU index',zero=True)
        core.require(len(set(gpu_indices))==len(gpu_indices),'Duplicate CUDA device')
        devices=[probe(root,i) for i in gpu_indices]; backend='cuda'
    else:
        h.positive(cpu_processes,'CPU process count'); core.require(cpu_processes<=len(rows),'Too many processes')
        devices=[None]*cpu_processes; backend='cpu'
    labels=g.inventory(paths['alphabet'])['labels']; sizes=[]
    for r in core.dataset(paths['manifest'])['regions']:
        with Image.open(core.within(root,r['file'])) as im: sizes.append(im.width*im.height)
    count=sum(map(len,rows.values())); work=v.workload_estimate(max(sizes),len(labels),max(1,count),max(1024**2,count*512))
    info=h.snapshot(output.parent,'review'); plan=budgets(info,work,devices,preset,limits)
    groups=partition([(rid,max(1,len(boxes))) for rid,boxes in rows.items()],[p['capacity'] for p in plan['plans']])
    binding={k+'_sha256':initial[k] for k in ('manifest','review')}; binding['model_sha256']=initial['model_path']
    start=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='.vrs-shards-',dir=output.parent) as temp:
        configs=[]; outputs=[]
        for i,(group,p) in enumerate(zip(groups,plan['plans'])):
            cfg=Path(temp)/f'config-{i}.json'; dest=Path(temp)/f'shard-{i}.json'
            core.write(cfg,dict(**paths,output=str(dest),device=backend,gpu_index=p['index'] if backend=='cuda' else 0,region_ids=group,preset=plan['preset'],limits=p['limits']))
            configs.append(cfg); outputs.append(dest)
        execute(configs,timeout)
        core.require(initial=={k:core.sha(p) for k,p in paths.items()},'Input changed during execution')
        core.dataset(paths['manifest'])
        reports=[core.read(p) for p in outputs]
        for report,p in zip(reports,plan['plans']):
            target='cuda:'+str(p['index']) if backend=='cuda' else 'cpu'
            core.require(report['operational']['backend']==target,'Shard device binding mismatch')
        result=merge(reports,groups,rows,excluded,binding,backend)
        result['operational']=dict(adapter='0.9.4-d',preset=plan['preset'],plan=plan,shards=[dict(regions=len(gp),candidates=len(r['rows']),metrics=r['operational']) for gp,r in zip(groups,reports)],seconds=time.perf_counter()-start)
        staged=Path(temp)/'merged.json'; core.write(staged,result)
        used=sum(p.stat().st_size for p in Path(temp).iterdir())
        if used>plan['disk_budget'] or staged.stat().st_size>plan['disk_budget']//2 or h.snapshot(output.parent,'review')['disk_free']<plan['disk_reserve']:
            raise h.ResourceBlocked('Shared output budget exceeded')
        # Atomic no-replace publication on the same filesystem; fail closed if unsupported.
        os.link(staged,output)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='action',required=True)
    c=sub.add_parser('child'); c.add_argument('config')
    q=sub.add_parser('predict')
    for k in (*INPUTS,'output'): q.add_argument(k)
    m=q.add_mutually_exclusive_group(required=True); m.add_argument('--gpus',type=int,nargs='+',dest='gpu_indices'); m.add_argument('--cpu-processes',type=int)
    q.add_argument('--preset',choices=(*h.PRESETS,'silent'),default=h.DEFAULT_PRESET); q.add_argument('--limits',type=Path); q.add_argument('--timeout',type=int,default=3600)
    a=vars(p.parse_args()); action=a.pop('action')
    try:
        if action=='child': child(**a); return 0
        if a['limits'] is not None: a['limits']=core.read(a['limits'])
        result=run(**a); print(json.dumps(result['operational'],indent=2)); return 0
    except (ValueError,OSError,h.ResourceBlocked) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc)})); return 1


if __name__=='__main__': raise SystemExit(main())

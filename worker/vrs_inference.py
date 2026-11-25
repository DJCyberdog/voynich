"""VRS-094 A: bounded, ordered glyph inference; legacy scientific code unchanged."""
import argparse
import itertools
import json
import platform
import time
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from pathlib import Path
from threading import RLock

_THREAD_LOCK = RLock()

import vrs_hardware as h
import vrs_core as core
import vrs_resources as resources


def minimum(info, mode):
    if mode not in ('review', 'cpu', 'cuda'):
        raise ValueError('Invalid profile')
    physical = info.get('physical')
    issues = []
    if info['machine'].lower() not in ('amd64', 'x86_64'):
        issues.append('x64 required')
    if info['system'] not in (('Windows',) if mode == 'review' else ('Windows', 'Linux')):
        issues.append('OS outside target profile')
    if not physical or physical < 4 or info['allowed'] < (4 if mode == 'review' else 8):
        issues.append('CPU minimum not established')
    if info['ram_total'] < (8 if mode == 'review' else 16)*h.GIB:
        issues.append('RAM below provisional minimum')
    if info['disk_free'] < (10 if mode == 'review' else 50)*10**9:
        issues.append('Free storage below provisional floor')
    if mode == 'cuda' and (not (info.get('gpu') or {}).get('ok') or info['gpu']['total'] < 8*h.GIB):
        issues.append('CUDA or VRAM minimum not established')
    return {'profile': mode, 'issues': issues, 'meets_checked_minimum': not issues,
            'unverified': ['CPU ISA/AVX2', 'SSD type', 'display', 'native OS version', 'representative throughput']}


def workload_estimate(max_pixels, labels, items, disk):
    """Conservative initial estimate, not calibrated model peak measurements."""
    for n in (max_pixels, labels, items):
        h.positive(n, 'workload size')
    h.positive(disk, 'disk', zero=True)
    return dict(ram_base=256*h.MIB, ram_item=8*max_pixels+2*h.MIB,
                vram_base=256*h.MIB, vram_item=16*labels*1024+64*1024,
                disk=disk, items=items)


def fresh(workspace, selected):
    info = h.snapshot(workspace, 'review')
    if selected['backend'] == 'cuda':
        import torch
        i = selected['gpu_index']
        free, total = torch.cuda.mem_get_info(i)
        info['gpu'] = dict(ok=True,index=i,free=int(free),total=int(total))
    return info


def ordered_batches(items, prepare, infer, *, batch, workers, admit, group=None):
    """At most two chunks; one prefetch, one consumer. No partial batch publication."""
    h.positive(batch, 'batch'); h.positive(workers, 'workers')
    iterator = iter(items)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        def submit():
            chunk = list(itertools.islice(iterator,batch))
            if chunk:
                admit(batch)
            groups = [[x] for x in chunk] if group is None else [list(xs) for _,xs in itertools.groupby(chunk,group)]
            return chunk,[pool.submit(prepare,x) if group is None else pool.submit(prepare,xs) for xs in groups for x in (xs[0],)]
        chunk, pending = submit()
        while chunk:
            features = [h.bounded_call(f.result) for f in pending]
            if group is not None: features = list(itertools.chain.from_iterable(features))
            if len(features) != len(chunk): raise ValueError('Preparation cardinality mismatch')
            # Admission accounts for both current and prefetched chunk conservatively.
            following, futures = submit()
            result = list(h.bounded_call(infer,features))
            if len(result) != len(chunk):
                raise ValueError('Inference cardinality mismatch')
            yield from zip(chunk,result)
            chunk,pending = following,futures


def _predict(manifest, review, alphabet, model_path, report_path, output, *, device='auto', preset=h.DEFAULT_PRESET, serial=False, limits=None, profiler=None):
    """Opt-in local glyph prediction adapter. No training or automatic research."""
    import glyphs as g
    import torch
    import numpy as np
    from PIL import Image
    phase_start=time.perf_counter()
    labels=g.inventory(alphabet)['labels']; m=core.dataset(manifest)
    model=core.read(model_path); report=core.read(report_path)
    core.require(report['model_sha256']==core.sha(model_path) and model['inventory_sha256']==core.sha(alphabet) and model['code_sha256']==core.sha(g.__file__) and model['labels']==labels and model['thresholds']==[.12,.005], 'Model provenance mismatch')
    output=Path(output); core.require(not output.exists(), 'Output already exists')
    root=Path(manifest).resolve().parent; sizes={}; paths={}; hashes={}
    for r in m['regions']:
        p=core.within(root,r['file']); paths[r['id']]=p; hashes[r['id']]=r['sha256']
        with Image.open(p) as im: sizes[r['id']]=im.size
    a=g.checked_review(review,manifest,sizes,labels,core.sha(alphabet))
    items=[(r['id'],x['box']) for r in m['regions'] if a['regions'][r['id']]['status']=='single_line' for x in sorted(a['regions'][r['id']]['glyphs'],key=lambda z:z['box'][0])]
    excluded=sum(a['regions'][r['id']]['status']!='single_line' for r in m['regions'])
    if profiler: profiler.record('validation',time.perf_counter()-phase_start)
    phase_start=time.perf_counter()
    info=h.snapshot(root,device); estimate=workload_estimate(max(w*y for w,y in sizes.values()),len(labels),max(1,len(items)),max(1024**2,len(items)*512))
    repeated={key for key,count in Counter(hashes.values()).items() if count>1}
    caps=resources.limits(limits)
    plan_caps=caps if repeated else {**caps,'cache_bytes':0}
    selected=resources.plan(info,estimate,device,preset,plan_caps); dev=selected['backend']
    selected['limits']=caps
    batch=1 if serial else selected['batch_ceiling']
    slots=selected['cpu_workers']
    inline=serial or slots==1
    torch.set_num_threads(min(torch.get_num_threads(), max(1,slots-(0 if inline else 1))))
    workers=0 if inline else min(slots-torch.get_num_threads(),batch)
    cache=resources.FeatureCache(selected['cache_budget'] if repeated else 0)
    def admit(n):
        current=fresh(root,selected)
        demand=estimate['ram_base']+2*n*estimate['ram_item']
        headroom=max(0,current['ram_available']-selected['ram_reserve']-demand)
        cache.resize(min(cache.stats()['budget'],headroom))
        h.admit_next(current,selected,demand+cache.stats()['budget'],estimate['vram_base']+n*estimate['vram_item'] if dev=='cuda' else 0,estimate['disk'])
    if profiler:
        profiler.record('planning',time.perf_counter()-phase_start)
        admit_raw=admit
        def admit(n): return profiler.call('admission',admit_raw,n)
    admit(batch)
    phase_start=time.perf_counter()
    target='cuda:'+str(selected['gpu_index']) if dev=='cuda' else 'cpu'
    prototypes=h.bounded_call(torch.tensor,model['prototypes'],dtype=torch.float32,device=target)
    core.require(prototypes.shape==(len(labels),1024) and bool(torch.isfinite(prototypes).all()) and bool(((prototypes>=0)&(prototypes<=1)).all()), 'Invalid model prototypes')
    if profiler: profiler.record('model_setup',time.perf_counter()-phase_start)
    def prepare(group):
        rid=group[0][0]
        keys=[(hashes[rid],tuple(box)) for _,box in group]
        if hashes[rid] not in repeated or not cache.stats()['budget']:
            with Image.open(paths[rid]) as im: return [g.feature(im.crop(box)) for _,box in group]
        values=[cache.get(key) for key in keys]
        if any(value is None for value in values):
            with Image.open(paths[rid]) as im:
                for i,(_,box) in enumerate(group):
                    if values[i] is None:
                        values[i]=g.feature(im.crop(box)).tobytes()
                        cache.put(keys[i],values[i])
        return [np.frombuffer(value,dtype=np.float32) for value in values]
    def infer(features):
        with torch.inference_mode():
            f=torch.from_numpy(np.stack(features)).to(target)
            return g.classify(f,prototypes)
    if profiler:
        prepare_raw,infer_raw=prepare,infer
        def prepare(group): return profiler.call('preparation',prepare_raw,group)
        def infer(features):
            result=profiler.call('inference',infer_raw,features)
            if dev=='cuda': profiler.gpu_sample(torch,selected['gpu_index'])
            return result
    start=time.perf_counter(); rows=[]
    def sequential():
        iterator=iter(items)
        while chunk:=list(itertools.islice(iterator,batch)):
            admit(batch)
            features=[f for _,group in itertools.groupby(chunk,lambda x:x[0]) for f in h.bounded_call(prepare,list(group))]
            result=list(h.bounded_call(infer,features))
            if len(result)!=len(chunk): raise ValueError('Inference cardinality mismatch')
            yield from zip(chunk,result)
    batches=sequential() if inline else ordered_batches(items,prepare,infer,batch=batch,workers=workers,admit=admit,group=lambda x:x[0])
    for (rid,box),(i,d,gap) in batches:
        rows.append(dict(region_id=rid,box=box,predicted=g.decision(labels[i],d,gap),distance=d,margin=gap))
    result=dict(version=g.VERSION,scientific_status='UNADJUDICATED',environment={'device':dev,'torch':str(torch.__version__),'cuda_build':torch.version.cuda},manifest_sha256=core.sha(manifest),review_sha256=core.sha(review),model_sha256=core.sha(model_path),excluded_regions=excluded,rows=rows,
                operational=dict(adapter='0.9.4-b',preset=selected['preset'],workers=workers,torch_threads=torch.get_num_threads(),batch=batch,limits=selected['limits'],cache=cache.stats(),seconds=time.perf_counter()-start,estimate=estimate,backend=target))
    phase_start=time.perf_counter()
    # Estimate is advisory; also enforce the exact final JSON byte count before publishing.
    if len((json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n').encode('utf-8'))>selected['disk_budget']:
        raise h.ResourceBlocked('Configured disk limit exceeded by actual report')
    core.write(output,result)
    if profiler: profiler.record('serialization',time.perf_counter()-phase_start)
    return result


def predict(*args, **kwargs):
    # Process-global Torch settings: serialize adapter calls, restore on failure.
    import torch
    with _THREAD_LOCK:
        previous=torch.get_num_threads()
        try:
            return _predict(*args, **kwargs)
        finally:
            torch.set_num_threads(previous)


def main():
    p=argparse.ArgumentParser(description=__doc__); s=p.add_subparsers(dest='action',required=True)
    q=s.add_parser('minimum'); q.add_argument('workspace'); q.add_argument('--profile',choices=('review','cpu','cuda'),default='review')
    q=s.add_parser('predict')
    for k in ('manifest','review','alphabet','model_path','report_path','output'): q.add_argument(k)
    q.add_argument('--device',choices=('auto','cpu','cuda'),default='auto'); q.add_argument('--preset',choices=(*h.PRESETS,'silent'),default=h.DEFAULT_PRESET); q.add_argument('--serial',action='store_true'); q.add_argument('--limits',type=Path)
    a=vars(p.parse_args()); action=a.pop('action')
    try:
        if action=='minimum':
            profile=a['profile']; result=minimum(h.snapshot(a['workspace'],profile),profile)
            print(json.dumps(result,indent=2)); return 0 if result['meets_checked_minimum'] else 1
        if a['limits'] is not None: a['limits']=core.read(a['limits'])
        result=predict(**a); print(json.dumps(result['operational'],indent=2)); return 0
    except (ValueError,OSError,h.ResourceBlocked) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc)})); return 1


if __name__=='__main__': raise SystemExit(main())

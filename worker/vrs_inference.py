"""VRS-094 A: bounded, ordered glyph inference; legacy scientific code unchanged."""
import argparse
import itertools
import json
import platform
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import vrs_hardware as h
import vrs_core as core


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


def predict(manifest, review, alphabet, model_path, report_path, output, *, device='auto', preset=h.DEFAULT_PRESET, serial=False):
    """Opt-in local glyph prediction adapter. No training or automatic research."""
    import glyphs as g
    import torch
    import numpy as np
    from PIL import Image
    labels=g.inventory(alphabet)['labels']; m=core.dataset(manifest)
    model=core.read(model_path); report=core.read(report_path)
    core.require(report['model_sha256']==core.sha(model_path) and model['inventory_sha256']==core.sha(alphabet) and model['code_sha256']==core.sha(g.__file__) and model['labels']==labels and model['thresholds']==[.12,.005], 'Model provenance mismatch')
    output=Path(output); core.require(not output.exists(), 'Output already exists')
    root=Path(manifest).resolve().parent; sizes={}; paths={}
    for r in m['regions']:
        p=core.within(root,r['file']); paths[r['id']]=p
        with Image.open(p) as im: sizes[r['id']]=im.size
    a=g.checked_review(review,manifest,sizes,labels,core.sha(alphabet))
    items=[(r['id'],x['box']) for r in m['regions'] if a['regions'][r['id']]['status']=='single_line' for x in sorted(a['regions'][r['id']]['glyphs'],key=lambda z:z['box'][0])]
    excluded=sum(a['regions'][r['id']]['status']!='single_line' for r in m['regions'])
    info=h.snapshot(root,device); estimate=workload_estimate(max(w*y for w,y in sizes.values()),len(labels),max(1,len(items)),max(1024**2,len(items)*512))
    selected=h.plan(info,estimate,device,preset); dev=selected['backend']
    # Leave room for one in-flight chunk and one prefetched chunk in host RAM.
    batch=min(selected['batch_ceiling'],max(1,(selected['ram_budget']-estimate['ram_base'])//(2*estimate['ram_item'])))
    if serial: batch=1
    workers=1 if serial else min(max(1,selected['cpu_workers']-(torch.get_num_threads() if dev=='cpu' else 1)),batch)
    def admit(n):
        h.admit_next(fresh(root,selected),selected,estimate['ram_base']+2*n*estimate['ram_item'],estimate['vram_base']+n*estimate['vram_item'] if dev=='cuda' else 0,estimate['disk'])
    admit(batch)
    target='cuda:'+str(selected['gpu_index']) if dev=='cuda' else 'cpu'
    prototypes=h.bounded_call(torch.tensor,model['prototypes'],dtype=torch.float32,device=target)
    core.require(prototypes.shape==(len(labels),1024) and bool(torch.isfinite(prototypes).all()) and bool(((prototypes>=0)&(prototypes<=1)).all()), 'Invalid model prototypes')
    def prepare(group):
        rid=group[0][0]
        with Image.open(paths[rid]) as im: return [g.feature(im.crop(box)) for _,box in group]
    def infer(features):
        with torch.inference_mode():
            f=torch.from_numpy(np.stack(features)).to(target)
            return g.classify(f,prototypes)
    start=time.perf_counter(); rows=[]
    for (rid,box),(i,d,gap) in ordered_batches(items,prepare,infer,batch=batch,workers=workers,admit=admit,group=lambda x:x[0]):
        rows.append(dict(region_id=rid,box=box,predicted=g.decision(labels[i],d,gap),distance=d,margin=gap))
    result=dict(version=g.VERSION,scientific_status='UNADJUDICATED',environment={'device':dev,'torch':str(torch.__version__),'cuda_build':torch.version.cuda},manifest_sha256=core.sha(manifest),review_sha256=core.sha(review),model_sha256=core.sha(model_path),excluded_regions=excluded,rows=rows,
                operational=dict(adapter='0.9.4-a',preset=preset,workers=workers,batch=batch,seconds=time.perf_counter()-start,estimate=estimate,backend=target))
    core.write(output,result); return result


def main():
    p=argparse.ArgumentParser(description=__doc__); s=p.add_subparsers(dest='action',required=True)
    q=s.add_parser('minimum'); q.add_argument('workspace'); q.add_argument('--profile',choices=('review','cpu','cuda'),default='review')
    q=s.add_parser('predict')
    for k in ('manifest','review','alphabet','model_path','report_path','output'): q.add_argument(k)
    q.add_argument('--device',choices=('auto','cpu','cuda'),default='auto'); q.add_argument('--preset',choices=tuple(h.PRESETS),default=h.DEFAULT_PRESET); q.add_argument('--serial',action='store_true')
    a=vars(p.parse_args()); action=a.pop('action')
    try:
        if action=='minimum':
            profile=a['profile']; result=minimum(h.snapshot(a['workspace'],profile),profile)
            print(json.dumps(result,indent=2)); return 0 if result['meets_checked_minimum'] else 1
        result=predict(**a); print(json.dumps(result['operational'],indent=2)); return 0
    except (ValueError,OSError,h.ResourceBlocked) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc)})); return 1


if __name__=='__main__': raise SystemExit(main())

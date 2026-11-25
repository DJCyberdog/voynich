"""VRS-094 E: opt-in alternative inference qualification; no automatic selection."""
import argparse
import importlib
import json
import math
import platform
import warnings
from pathlib import Path

import vrs_hardware as h
import vrs_resources as resources
import vrs_dxgi as dxgi

BACKENDS = ('rocm', 'xpu', 'directml')


def resolve(torch, backend, index, system=None, loader=importlib.import_module):
    h.positive(index, 'GPU index', zero=True)
    system = system or platform.system()
    if backend not in BACKENDS:
        raise ValueError('Unknown alternative backend')
    if system not in ('Windows', 'Linux'):
        raise h.ResourceBlocked('Unsupported operating system')
    if backend == 'rocm':
        if not isinstance(torch.version.hip, str) or not torch.version.hip:
            raise h.ResourceBlocked('ROCm requires a HIP-enabled PyTorch build')
        api, target = torch.cuda, f'cuda:{index}'
    elif backend == 'xpu':
        api, target = getattr(torch, 'xpu', None), f'xpu:{index}'
        if api is None:
            raise h.ResourceBlocked('Intel XPU runtime unavailable')
    else:
        if system != 'Windows':
            raise h.ResourceBlocked('DirectML qualification currently targets native Windows')
        try:
            api = loader('torch_directml')
        except ImportError as exc:
            raise h.ResourceBlocked('DirectML runtime unavailable') from exc
        if index >= api.device_count():
            raise h.ResourceBlocked('DirectML device unavailable')
        target = api.device(index)
        if getattr(target, 'type', None) != 'privateuseone':
            raise h.ResourceBlocked('Unexpected DirectML device type')
        return api, target
    if not api.is_available() or index >= api.device_count():
        raise h.ResourceBlocked('Requested GPU unavailable')
    return api, target


def memory(api, index):
    try:
        free, total = api.mem_get_info(index)
        if type(free) is not int or type(total) is not int or not 0 <= free <= total or total <= 0:
            raise ValueError('Invalid device memory counters')
        return dict(ok=True, index=index, free=free, total=total)
    except (AttributeError, RuntimeError, ValueError, TypeError, NotImplementedError) as exc:
        raise h.ResourceBlocked('Reliable free/total device memory unavailable') from exc


def exact_classify(torch, classify, features, prototypes, target):
    """Qualification only: compare every candidate with the unchanged CPU classifier."""
    with torch.inference_mode(), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        cpu = classify(features, prototypes)
        actual_features = features.to(target)
        actual_prototypes = prototypes.to(target)
        if actual_features.device != torch.device(target) or actual_prototypes.device != torch.device(target):
            raise h.ResourceBlocked('Tensor device mismatch')
        gpu = classify(actual_features, actual_prototypes)
    if any('fallback' in str(w.message).lower() or 'fall back' in str(w.message).lower() or 'falling back' in str(w.message).lower() for w in caught):
        raise h.ResourceBlocked('Backend reported operator fallback')
    if len(gpu) != len(features) or gpu != cpu or any(not math.isfinite(x) for _,d,m in gpu for x in (d,m)):
        raise h.ResourceBlocked('Exact CPU/backend classifier parity not established')
    return gpu


def probe(backend, index=0, *, torch=None):
    """Exercise the real classifier operators, not only device enumeration."""
    try:
        if torch is None:
            import torch
        import glyphs as g
        api, target = resolve(torch, backend, index)
        before = dxgi.memory(api,index) if backend == 'directml' else memory(api,index)
        if before['free'] < 256*h.MIB:
            raise h.ResourceBlocked('Insufficient device budget for classifier probe')
        # Exactly representable values, distinct nearest prototypes, no ties.
        p = torch.stack([torch.zeros(1024), torch.ones(1024)]).float()
        f = torch.stack([torch.full((1024,), .125), torch.full((1024,), .875)]).float()
        result = exact_classify(torch, g.classify, f, p, target)
        if result != [(0, .015625, .75), (1, .015625, .75)]:
            raise h.ResourceBlocked('Unexpected probe result')
        if backend != 'directml':
            api.synchronize(index)
        telemetry = dxgi.memory(api,index,before['luid']) if backend == 'directml' else memory(api,index)
        return dict(backend=backend, index=index, target=str(target), status='PROBE_PASS',
                    torch=str(torch.__version__), hip=getattr(torch.version,'hip',None),
                    memory=telemetry, qualification_available=telemetry is not None,
                    native_acceptance='UNVERIFIED')
    except Exception as exc:
        return dict(backend=backend, index=index, status='BLOCKED', reason=type(exc).__name__+': '+str(exc),
                    qualification_available=False, native_acceptance='UNVERIFIED')


def qualify(manifest, review, alphabet, model_path, report_path, output, *, backend, index=0, preset=h.DEFAULT_PRESET, limits=None):
    """Bounded local inference qualification, never auto-selected or used for training.

    Every backend batch is independently checked on CPU before any report is written.
    DirectML is limited to a single unambiguous dedicated Windows adapter.
    """
    import torch
    import glyphs as g
    import worker as w
    from PIL import Image
    import numpy as np
    import os
    import tempfile
    caps = resources.limits(limits)
    if backend not in BACKENDS:
        raise ValueError('Explicit alternative backend required')
    evidence = probe(backend,index)
    if evidence['status'] != 'PROBE_PASS' or not evidence['qualification_available']:
        raise h.ResourceBlocked('Backend qualification blocked: '+evidence.get('reason','memory unavailable'))
    api,target = resolve(torch,backend,index)
    output=Path(output)
    w.require(not output.exists(),'Output already exists')
    root=Path(manifest).resolve().parent
    labels=g.inventory(alphabet)['labels']; m=w.dataset(manifest); model=w.read(model_path); report=w.read(report_path)
    w.require(report['model_sha256']==w.sha(model_path) and model['inventory_sha256']==w.sha(alphabet) and model['code_sha256']==w.sha(g.__file__) and model['labels']==labels and model['thresholds']==[.12,.005],'Model provenance mismatch')
    sizes={}
    for r in m['regions']:
        with Image.open(w.within(root,r['file'])) as im: sizes[r['id']]=im.size
    a=g.checked_review(review,manifest,sizes,labels,w.sha(alphabet))
    n=sum(len(a['regions'][r['id']]['glyphs']) for r in m['regions'] if a['regions'][r['id']]['status']=='single_line')
    pixels=max(x*y for x,y in sizes.values())
    scratch=16*len(labels)*1024+64*1024
    # Include CPU mirror and whole-region decode; estimates remain cooperative.
    work=dict(ram_base=256*h.MIB+8*pixels+n*1024,ram_item=2*h.MIB+scratch,
              vram_base=256*h.MIB,vram_item=scratch,disk=max(h.MIB,n*512),items=max(1,n))
    output.parent.mkdir(parents=True,exist_ok=True)
    def snapshot():
        info=h.snapshot(output.parent,'review')
        info['gpu']=dxgi.memory(api,index,evidence['memory']['luid']) if backend=='directml' else memory(api,index)
        return info
    info=snapshot()
    # Reuse the CUDA-shaped budget contract only internally; actual identity stays explicit.
    selected=resources.plan(info,work,'cuda',preset,{**caps,'cache_bytes':0})
    batch=min(128,selected['batch_ceiling'])
    def admit(count):
        h.admit_next(snapshot(),selected,work['ram_base']+count*work['ram_item'],work['vram_base']+count*work['vram_item'],work['disk'])
    admit(batch)
    p=torch.tensor(model['prototypes'],dtype=torch.float32,device='cpu')
    w.require(p.shape==(len(labels),1024) and bool(torch.isfinite(p).all()) and bool(((p>=0)&(p<=1)).all()),'Invalid model prototypes')
    rows=[]; excluded=0; previous=torch.get_num_threads()
    try:
        torch.set_num_threads(min(previous,selected['cpu_workers']))
        for r in m['regions']:
            line=a['regions'][r['id']]
            if line['status']!='single_line': excluded+=1; continue
            glyphs=sorted(line['glyphs'],key=lambda x:x['box'][0])
            admit(batch)
            with Image.open(w.within(root,r['file'])) as im:
                for start in range(0,len(glyphs),batch):
                    chunk=glyphs[start:start+batch]; admit(len(chunk))
                    f=torch.from_numpy(np.stack([g.feature(im.crop(x['box'])) for x in chunk]))
                    result=h.bounded_call(exact_classify,torch,g.classify,f,p,target)
                    if backend != 'directml': api.synchronize(index)
                    # Classifier list conversion synchronizes DirectML readback.
                    # Recheck budget after execution; never publish under pressure.
                    admit(len(chunk))
                    for x,(i,d,gap) in zip(chunk,result):
                        rows.append(dict(region_id=r['id'],box=x['box'],predicted=g.decision(labels[i],d,gap),distance=d,margin=gap))
    finally:
        torch.set_num_threads(previous)
    result=dict(version=g.VERSION,scientific_status='UNADJUDICATED',environment={'device':backend,'probe':evidence},
                manifest_sha256=w.sha(manifest),review_sha256=w.sha(review),model_sha256=w.sha(model_path),excluded_regions=excluded,rows=rows,
                operational=dict(adapter='0.9.4-e',backend=backend,index=index,batch=batch,preset=selected['preset'],limits=caps,exact_cpu_mirror=True,native_acceptance='UNVERIFIED'))
    payload=(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n').encode('utf-8')
    if len(payload)>selected['disk_budget'] or len(payload)+selected['disk_reserve']>snapshot()['disk_free']:
        raise h.ResourceBlocked('Final report exceeds disk budget')
    # No replacement, even if a competing output appears during inference.
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='.vrs-e-') as tmp:
        stage=Path(tmp)/'report.json'; stage.write_bytes(payload); os.link(stage,output)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='action',required=True)
    q=sub.add_parser('probe'); q.add_argument('backend',choices=BACKENDS); q.add_argument('--index',type=int,default=0)
    q=sub.add_parser('qualify')
    for k in ('manifest','review','alphabet','model_path','report_path','output'): q.add_argument(k)
    q.add_argument('--backend',choices=BACKENDS,required=True); q.add_argument('--index',type=int,default=0)
    q.add_argument('--preset',choices=(*h.PRESETS,'silent'),default=h.DEFAULT_PRESET); q.add_argument('--limits',type=Path)
    args=vars(p.parse_args()); action=args.pop('action')
    try:
        if action=='probe':
            result=probe(**args); print(json.dumps(result,indent=2)); return 0 if result['status']=='PROBE_PASS' else 1
        if args['limits'] is not None: args['limits']=json.loads(args['limits'].read_text(encoding='utf-8'))
        result=qualify(**args); print(json.dumps(result['operational'],indent=2)); return 0
    except (ValueError,OSError,RuntimeError,ImportError,MemoryError) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc)})); return 1


if __name__=='__main__': raise SystemExit(main())

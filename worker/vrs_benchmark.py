"""Local synthetic engineering benchmark, never scientific acceptance."""
import argparse
import json
import tempfile
import time
from pathlib import Path

import psutil
import vrs_core as core
import vrs_hardware as h
import vrs_inference as v


def benchmark(device='cpu', repeats=3, regions=64, unique=False, profile=False):
    import torch
    import glyphs as g
    from PIL import Image, ImageDraw
    h.positive(repeats,'repeats'); h.positive(regions,'regions')
    if repeats>10 or regions>1024: raise ValueError('Benchmark size limit')
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); manifest=root/'manifest.json'; alphabet=root/'alphabet.json'; review=root/'review.json'; model=root/'model.json'; report=root/'report.json'
        records=[]; reviewed={}
        from vrs_diagnostics import Profiler
        # Fixed generated synthetic line images, not manuscript pages or holdout evidence.
        for i in range(regions):
            im=Image.new('L',(192,48),255); draw=ImageDraw.Draw(im)
            for j in range(8):
                x=4+j*24; draw.rectangle((x,5+(i+j)%4,x+3+j%4,40-j%3),fill=0)
            if unique:
                # Encode region identity within ink, not a metadata-only change.
                for bit in range(10):
                    if (i >> bit) & 1:
                        draw.point((5,7+bit*2),fill=255)
            path=root/f'r{i}.png'; im.save(path)
            rid=f'r{i}'; records.append(dict(id=rid,group=rid,page=i+1,file=path.name,sha256=core.sha(path)))
            reviewed[rid]=dict(status='single_line',glyphs=[dict(box=b,label='unknown') for b in g.boxes(im)])
        core.write(manifest,dict(regions=records)); core.write(alphabet,dict(convention='synthetic',labels=['X','Y']))
        core.write(review,dict(schema=1,reviewer='fixture',manifest_sha256=core.sha(manifest),inventory_sha256=core.sha(alphabet),regions=reviewed))
        core.write(model,dict(version=g.VERSION,labels=['X','Y'],prototypes=[[0.0]*1024,[1.0]*1024],inventory_sha256=core.sha(alphabet),code_sha256=core.sha(g.__file__),thresholds=[.12,.005]))
        core.write(report,dict(model_sha256=core.sha(model)))
        args=(manifest,review,alphabet,model,report)
        result=dict(device=device,regions=regions,repeats=repeats,unique_input=unique,unique_region_hashes=len({r['sha256'] for r in records}),profiled=profile,fixture_sha256=core.sha(manifest),torch=str(torch.__version__),torch_threads=torch.get_num_threads(),runs=[])
        baseline=g.predict(*args,root/'legacy-warmup.json',device)
        v.predict(*args,root/'adaptive-warmup.json',device=device)
        proc=psutil.Process()
        for n in range(repeats):
            for mode in (('legacy','adaptive') if n%2==0 else ('adaptive','legacy')):
                out=root/f'{mode}-{n}.json'; t=time.perf_counter()
                if device=='cuda': torch.cuda.reset_peak_memory_stats()
                prof=Profiler() if profile and mode=='adaptive' else None
                if prof:
                    with prof: value=v.predict(*args,out,device=device,profiler=prof)
                else:
                    value=g.predict(*args,out,device) if mode=='legacy' else v.predict(*args,out,device=device)
                if device=='cuda': torch.cuda.synchronize()
                seconds=time.perf_counter()-t
                if value['rows']!=baseline['rows'] or value['excluded_regions']!=baseline['excluded_regions']:
                    raise ValueError('Exact synthetic output parity failed')
                result['runs'].append(dict(mode=mode,seconds=seconds,glyphs=len(value['rows']),glyphs_per_second=len(value['rows'])/seconds,rss_after=proc.memory_info().rss,cuda_peak_allocated=torch.cuda.max_memory_allocated() if device=='cuda' else None,operational=value.get('operational'),profile=prof.report() if prof else None))
        result['exact_parity']=True; result['scientific_status']='UNADJUDICATED'
        return result


def runtime_candidate(device='cpu', repeats=3, boxes_per_run=512):
    """Measure the exact Runtime classifier/candidate function on generated glyphs."""
    import statistics
    import threading
    import torch
    from PIL import Image,ImageDraw
    import vrs_recognition as rec
    if device not in ('cpu','cuda') or type(repeats) is not int or not 1<=repeats<=10 or type(boxes_per_run) is not int or not 64<=boxes_per_run<=4096:
        raise ValueError('Invalid benchmark bounds')
    binding=None
    if device=='cuda':
        binding=h.cuda_binding(dict(gpu=h.cuda_probe(torch,0)))
    image=Image.new('L',(512,((boxes_per_run+15)//16)*32),255);draw=ImageDraw.Draw(image);boxes=[]
    for i in range(boxes_per_run):
        x=i%16*32;y=i//16*32
        draw.rectangle((x+4,y+3,x+7+i%9,y+27),fill=0)
        draw.line((x+6,y+10+i%11,x+25,y+12+i%11),fill=0,width=2)
        boxes.append((x,y,x+32,y+32))
    labels=[str(i) for i in range(16)];inv={'fixture':(labels,'0'*64)}
    models={'fixture':[[float((i+j)%17<8) for j in range(1024)] for i in range(16)]}
    process=psutil.Process();stop=threading.Event();peak=[process.memory_info().rss];rows=[]
    def sample():
        while not stop.wait(.02):peak[0]=max(peak[0],process.memory_info().rss)
    thread=threading.Thread(target=sample,daemon=True)
    previous=torch.get_num_threads()
    def execute(fn):
        result=[]
        for offset in range(0,len(boxes),64):result.extend(fn(boxes[offset:offset+64],image,inv,models))
        return result
    try:
        torch.set_num_threads(max(1,min(previous,4)))
        reference=execute(rec.classify)
        if device=='cuda':execute(rec.candidate);torch.cuda.synchronize(0)
        thread.start()
        for i in range(repeats):
            for mode in (('cpu','cuda_candidate') if device=='cuda' and i%2==0 else ('cuda_candidate','cpu') if device=='cuda' else ('cpu',)):
                if mode=='cuda_candidate':
                    if h.cuda_binding(dict(gpu=h.cuda_probe(torch,0)))!=binding:raise ValueError('CUDA device/build changed')
                    torch.cuda.reset_peak_memory_stats(0)
                t=time.perf_counter()
                output=execute(rec.candidate if mode=='cuda_candidate' else rec.classify)
                if mode=='cuda_candidate':torch.cuda.synchronize(0)
                elapsed=time.perf_counter()-t
                if mode=='cuda_candidate':rec.compare_candidate(reference,output,inv)
                elif output!=reference:raise ValueError('CPU benchmark parity failed')
                rows.append(dict(mode=mode,seconds=elapsed,glyphs=len(output),glyphs_per_second=len(output)/elapsed,
                                 cuda_peak_allocated=torch.cuda.max_memory_allocated(0) if mode=='cuda_candidate' else None,
                                 cuda_peak_reserved=torch.cuda.max_memory_reserved(0) if mode=='cuda_candidate' else None))
    finally:
        stop.set()
        if thread.ident is not None:thread.join()
        torch.set_num_threads(previous)
    return dict(schema=1,scope='SYNTHETIC_RUNTIME_CLASSIFIER_ONLY',scientific_status='UNADJUDICATED',
                device=device,cuda_binding=binding,torch=str(torch.__version__),boxes=boxes_per_run,repeats=repeats,
                batch_ceiling=64,sampled_peak_rss_bytes=peak[0],parity=True,rows=rows,
                median_glyphs_per_second={mode:statistics.median(r['glyphs_per_second'] for r in rows if r['mode']==mode) for mode in sorted({r['mode'] for r in rows})})


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--device',choices=('cpu','cuda'),default='cpu'); p.add_argument('--repeats',type=int,default=3); p.add_argument('--regions',type=int,default=64)
    p.add_argument('--unique',action='store_true'); p.add_argument('--profile',action='store_true')
    p.add_argument('--runtime-candidate',action='store_true');p.add_argument('--boxes',type=int,default=512)
    a=p.parse_args(); result=runtime_candidate(a.device,a.repeats,a.boxes) if a.runtime_candidate else benchmark(a.device,a.repeats,a.regions,a.unique,a.profile)
    print(json.dumps(result,indent=2)); return 0


if __name__=='__main__': raise SystemExit(main())

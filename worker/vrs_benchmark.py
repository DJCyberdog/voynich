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


def benchmark(device='cpu', repeats=3, regions=64):
    import torch
    import glyphs as g
    from PIL import Image, ImageDraw
    h.positive(repeats,'repeats'); h.positive(regions,'regions')
    if repeats>10 or regions>1024: raise ValueError('Benchmark size limit')
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); manifest=root/'manifest.json'; alphabet=root/'alphabet.json'; review=root/'review.json'; model=root/'model.json'; report=root/'report.json'
        records=[]; reviewed={}
        # Fixed generated synthetic line images, not manuscript pages or holdout evidence.
        for i in range(regions):
            im=Image.new('L',(192,48),255); draw=ImageDraw.Draw(im)
            for j in range(8):
                x=4+j*24; draw.rectangle((x,5+(i+j)%4,x+3+j%4,40-j%3),fill=0)
            path=root/f'r{i}.png'; im.save(path)
            rid=f'r{i}'; records.append(dict(id=rid,group=rid,page=i+1,file=path.name,sha256=core.sha(path)))
            reviewed[rid]=dict(status='single_line',glyphs=[dict(box=b,label='unknown') for b in g.boxes(im)])
        core.write(manifest,dict(regions=records)); core.write(alphabet,dict(convention='synthetic',labels=['X','Y']))
        core.write(review,dict(schema=1,reviewer='fixture',manifest_sha256=core.sha(manifest),inventory_sha256=core.sha(alphabet),regions=reviewed))
        core.write(model,dict(version=g.VERSION,labels=['X','Y'],prototypes=[[0.0]*1024,[1.0]*1024],inventory_sha256=core.sha(alphabet),code_sha256=core.sha(g.__file__),thresholds=[.12,.005]))
        core.write(report,dict(model_sha256=core.sha(model)))
        args=(manifest,review,alphabet,model,report)
        result=dict(device=device,regions=regions,repeats=repeats,fixture_sha256=core.sha(manifest),torch=str(torch.__version__),torch_threads=torch.get_num_threads(),runs=[])
        baseline=g.predict(*args,root/'legacy-warmup.json',device)
        v.predict(*args,root/'adaptive-warmup.json',device=device)
        proc=psutil.Process()
        for n in range(repeats):
            for mode in (('legacy','adaptive') if n%2==0 else ('adaptive','legacy')):
                out=root/f'{mode}-{n}.json'; t=time.perf_counter()
                if device=='cuda': torch.cuda.reset_peak_memory_stats()
                value=g.predict(*args,out,device) if mode=='legacy' else v.predict(*args,out,device=device)
                if device=='cuda': torch.cuda.synchronize()
                seconds=time.perf_counter()-t
                if value['rows']!=baseline['rows'] or value['excluded_regions']!=baseline['excluded_regions']:
                    raise ValueError('Exact synthetic output parity failed')
                result['runs'].append(dict(mode=mode,seconds=seconds,glyphs=len(value['rows']),glyphs_per_second=len(value['rows'])/seconds,rss_after=proc.memory_info().rss,cuda_peak_allocated=torch.cuda.max_memory_allocated() if device=='cuda' else None,operational=value.get('operational')))
        result['exact_parity']=True; result['scientific_status']='UNADJUDICATED'
        return result


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--device',choices=('cpu','cuda'),default='cpu'); p.add_argument('--repeats',type=int,default=3); p.add_argument('--regions',type=int,default=64)
    a=p.parse_args(); print(json.dumps(benchmark(a.device,a.repeats,a.regions),indent=2)); return 0


if __name__=='__main__': raise SystemExit(main())

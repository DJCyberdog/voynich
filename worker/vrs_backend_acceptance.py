"""Local synthetic native backend acceptance fixture, not manuscript evidence.
No downloads, network, training on user data or automatic backend selection.
"""
import argparse
import json
import platform
import tempfile
import time
from pathlib import Path

import vrs_backends as b
import vrs_hardware as h


def run(backend, index=0, *, workspace):
    import glyphs as g
    import worker as w
    import torch
    from PIL import Image, ImageDraw
    workspace=Path(workspace).resolve(strict=True)
    started=time.perf_counter()
    evidence=b.probe(backend,index)
    result=dict(schema=1,backend=backend,index=index,system=platform.system(),torch=str(torch.__version__),
                probe=evidence,status='BLOCKED',scientific_status='UNADJUDICATED',representative_acceptance='UNVERIFIED')
    if evidence['status']!='PROBE_PASS' or not evidence['qualification_available']:
        return result
    try:
        with tempfile.TemporaryDirectory(dir=workspace,prefix='.vrs-e-acceptance-') as d:
            root=Path(d); manifest=root/'manifest.json'; inventory=root/'inventory.json'; review=root/'review.json'; model=root/'model.json'; report=root/'report.json'
            rows=[]; annotations={}
            for i in range(4):
                im=Image.new('L',(100,44),255); draw=ImageDraw.Draw(im)
                draw.rectangle((8,6,12+i,34),fill=0); draw.rectangle((49,14,83,18+i),fill=0)
                path=root/f'r{i}.png'; im.save(path); rid=f'r{i}'
                rows.append(dict(id=rid,page=i+1,group=rid,file=path.name,sha256=w.sha(path)))
                annotations[rid]=dict(status='single_line',glyphs=[dict(box=box,label='unknown') for box in g.boxes(im)])
            w.write(manifest,dict(regions=rows)); w.write(inventory,dict(convention='synthetic-only',labels=['X','Y']))
            w.write(review,dict(schema=1,reviewer='synthetic fixture',manifest_sha256=w.sha(manifest),inventory_sha256=w.sha(inventory),regions=annotations))
            w.write(model,dict(version=g.VERSION,labels=['X','Y'],prototypes=[[0.0]*1024,[1.0]*1024],inventory_sha256=w.sha(inventory),code_sha256=w.sha(g.__file__),thresholds=[.12,.005]))
            w.write(report,dict(model_sha256=w.sha(model)))
            args=(manifest,review,inventory,model,report)
            expected=g.predict(*args,root/'cpu.json','cpu')
            actual=b.qualify(*args,root/'gpu.json',backend=backend,index=index)
            if len(expected['rows'])!=8 or expected['rows']!=actual['rows'] or expected['excluded_regions']!=actual['excluded_regions']:
                raise h.ResourceBlocked('Synthetic fixture parity failed')
            target=actual['environment']['probe']['target']
            # Test doubles or unexpected CPU routing cannot establish native acceptance.
            expected_type={'rocm':'cuda','xpu':'xpu','directml':'privateuseone'}[backend]
            if torch.device(target).type!=expected_type or torch.device(target).index!=index:
                raise h.ResourceBlocked('Native target identity not established')
            result.update(status='NATIVE_FIXTURE_PASS',glyphs=len(actual['rows']),exact_parity=True,
                          target=target,fixture_sha256=w.sha(manifest),seconds=time.perf_counter()-started)
    except (RuntimeError,ValueError,OSError,ImportError,MemoryError) as exc:
        result.update(reason=type(exc).__name__+': '+str(exc))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('backend',choices=b.BACKENDS); p.add_argument('--index',type=int,default=0); p.add_argument('--workspace',type=Path,default=Path(__file__).resolve().parent)
    a=p.parse_args(); result=run(a.backend,a.index,workspace=a.workspace); print(json.dumps(result,indent=2,allow_nan=False)); return 0 if result['status']=='NATIVE_FIXTURE_PASS' else 1


if __name__=='__main__': raise SystemExit(main())

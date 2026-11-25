"""VRS-094 S: read-only diagnostics and fail-closed resource admission.
No experiment, model, scheduler or network activity. Estimates are not hard OS limits.
"""
import argparse
import json
import os
import platform
import shutil
from pathlib import Path

GIB = 1024**3
MIB = 1024**2
DEFAULT_PRESET = 'performance'
PRESETS = {'performance': 90, 'balanced': 65, 'quiet': 35}


class ResourceBlocked(RuntimeError):
    """Caller must checkpoint/pause or abort; never silently change backend."""


def positive(value, name, zero=False):
    if type(value) is not int or value < (0 if zero else 1):
        raise ValueError('Invalid ' + name)
    return value


def cuda_probe(torch, index=0):
    """Require actual allocation, arithmetic and synchronization on selected device."""
    try:
        if not torch.cuda.is_available():
            raise ResourceBlocked('CUDA unavailable')
        if not 0 <= index < torch.cuda.device_count():
            raise ResourceBlocked('CUDA device unavailable')
        with torch.cuda.device(index):
            x = torch.ones((32, 32), device=f'cuda:{index}', dtype=torch.float32)
            y = x @ x
            torch.cuda.synchronize(index)
            if not bool((y == 32).all().item()):
                raise ResourceBlocked('CUDA arithmetic probe failed')
            del x, y
            free, total = torch.cuda.mem_get_info(index)
        p = torch.cuda.get_device_properties(index)
        return dict(ok=True, index=index, name=p.name, capability=list(torch.cuda.get_device_capability(index)),
                    free=int(free), total=int(total), torch=str(torch.__version__), cuda_build=torch.version.cuda,
                    build_arches=list(torch.cuda.get_arch_list()), reason=None)
    except Exception as exc:
        return dict(ok=False, index=index, reason=type(exc).__name__ + ': ' + str(exc))


def snapshot(workspace, request='auto', index=0):
    """psutil is required; torch is imported only for compute probes."""
    if request not in ('review', 'cpu', 'cuda', 'auto'):
        raise ValueError('Invalid backend request')
    positive(index, 'GPU index', zero=True)
    import psutil
    mem = psutil.virtual_memory()
    logical = psutil.cpu_count(logical=True)
    physical = psutil.cpu_count(logical=False)
    proc = psutil.Process()
    try:
        allowed = len(proc.cpu_affinity())
    except (AttributeError, NotImplementedError, psutil.Error):
        allowed = os.process_cpu_count() or logical
    # Honor visible cgroup v2 memory/CPU limits when present (Linux container).
    total, available = int(mem.total), int(mem.available)
    if platform.system() == 'Linux':
        cg = Path('/sys/fs/cgroup')
        try:
            rel = next(s.split(':', 2)[2] for s in Path('/proc/self/cgroup').read_text().splitlines() if s.startswith('0::'))
            leaf = cg / rel.lstrip('/')
            for node in (leaf, *leaf.parents):
                if not node.is_relative_to(cg):
                    break
                try:
                    limit = (node/'memory.max').read_text().strip()
                    if limit != 'max':
                        total = min(total, int(limit))
                        available = min(available, max(0, int(limit)-int((node/'memory.current').read_text())))
                    quota, period = (node/'cpu.max').read_text().split()
                    if quota != 'max':
                        allowed = min(allowed, max(1, int(quota)//int(period)))
                except (OSError, ValueError):
                    pass
        except (OSError, StopIteration, ValueError):
            pass
    gpu = None
    if request in ('cuda', 'auto'):
        try:
            import torch
            gpu = cuda_probe(torch, index)
        except ImportError as exc:
            gpu = dict(ok=False, index=index, reason='Torch unavailable: ' + str(exc))
    return dict(system=platform.system(), machine=platform.machine(), logical=logical, physical=physical,
                allowed=allowed, ram_total=total, ram_available=available,
                disk_free=shutil.disk_usage(Path(workspace).resolve(strict=True)).free, gpu=gpu)


def plan(info, workload, request='auto', preset=DEFAULT_PRESET):
    """Fixed workload byte estimates supplied by trusted producer, not guessed from model names.
    base/item are incremental peak memory estimates, disk is incremental workspace demand.
    Batch is an operational ceiling only; scientific settings must remain fixed.
    """
    if request not in ('review', 'cpu', 'cuda', 'auto') or preset not in PRESETS:
        raise ValueError('Invalid request or preset')
    keys = ('ram_base', 'ram_item', 'vram_base', 'vram_item', 'disk', 'items')
    if type(workload) is not dict or set(workload) != set(keys):
        raise ValueError('Invalid workload estimate')
    for k in keys:
        positive(workload[k], k, zero=k in ('ram_base','vram_base','vram_item','disk'))
    for k in ('allowed','ram_total','ram_available','disk_free'):
        positive(info[k], k, zero=k in ('ram_available','disk_free'))
    gpu = info.get('gpu')
    backend = 'review' if request == 'review' else 'cpu'
    if request in ('cuda','auto') and gpu and gpu.get('ok') is True:
        backend = 'cuda'
    elif request == 'cuda':
        raise ResourceBlocked('Explicit CUDA unavailable: ' + str((gpu or {}).get('reason', 'not probed')))
    percent = PRESETS[preset]
    reserve_ram = max(2*GIB, info['ram_total']//8)
    reserve_disk = 5*GIB
    ram = max(0, min(info['ram_total'], info['ram_available'])-reserve_ram)*percent//100
    if info['disk_free'] < workload['disk'] + reserve_disk:
        raise ResourceBlocked('Insufficient workspace storage reserve')
    batch = min(workload['items'], max(0, ram-workload['ram_base'])//workload['ram_item'])
    vram, reserve_vram = 0, 0
    if backend == 'cuda':
        positive(gpu['total'],'VRAM total')
        positive(gpu['free'],'VRAM free',zero=True)
        positive(workload['vram_item'],'VRAM item')
        reserve_vram = max(GIB, gpu['total']//16)
        vram = max(0,min(gpu['free'],gpu['total'])-reserve_vram)*percent//100
        batch = min(batch,max(0,vram-workload['vram_base'])//workload['vram_item'])
    if batch < 1:
        raise ResourceBlocked('Insufficient RAM/VRAM for one item with reserve')
    return dict(backend=backend, preset=preset, gpu_index=gpu['index'] if backend=='cuda' else None,
                cpu_workers=max(1,(max(1,info['allowed']-1)*percent+99)//100), batch_ceiling=batch,
                ram_budget=ram,vram_budget=vram,ram_reserve=reserve_ram,vram_reserve=reserve_vram,
                disk_reserve=reserve_disk, fallback_reason=(gpu or {}).get('reason','CUDA not probed') if request=='auto' and backend=='cpu' else None)


def admit_next(info, selected, ram_bytes, vram_bytes=0, disk_bytes=0):
    """At a safe boundary check incremental demand against fresh free memory and frozen budgets."""
    for name, value in [('RAM',ram_bytes),('VRAM',vram_bytes),('disk',disk_bytes)]:
        positive(value,name,zero=True)
    if ram_bytes > min(selected['ram_budget'],max(0,info['ram_available']-selected['ram_reserve'])) or info['ram_available'] < selected['ram_reserve']:
        raise ResourceBlocked('RAM pressure; checkpoint/pause')
    if info['disk_free'] < disk_bytes+selected['disk_reserve']:
        raise ResourceBlocked('Storage pressure; checkpoint/pause')
    if selected['backend']=='cuda':
        gpu=info.get('gpu') or {}
        if gpu.get('ok') is not True or gpu.get('index')!=selected['gpu_index']:
            raise ResourceBlocked('Selected CUDA device unavailable; no fallback')
        if gpu['free'] < selected['vram_reserve'] or vram_bytes > min(selected['vram_budget'],max(0,gpu['free']-selected['vram_reserve'])):
            raise ResourceBlocked('VRAM pressure; checkpoint/pause')
    elif vram_bytes:
        raise ResourceBlocked('GPU allocation requested on non-CUDA profile')


def bounded_call(fn, *args, **kwargs):
    """Normalize allocation failure without retry, fallback or scientific parameter changes."""
    try:
        return fn(*args, **kwargs)
    except MemoryError as exc:
        raise ResourceBlocked('Host allocation failed; checkpoint/pause') from exc
    except RuntimeError as exc:
        if 'out of memory' in str(exc).lower() or type(exc).__name__=='OutOfMemoryError':
            raise ResourceBlocked('Device allocation failed; checkpoint/pause') from exc
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('workspace',type=Path)
    p.add_argument('--backend',choices=('review','cpu','cuda','auto'),default='auto')
    p.add_argument('--gpu-index',type=int,default=0)
    p.add_argument('--preset',choices=tuple(PRESETS),default=DEFAULT_PRESET)
    p.add_argument('--workload',type=Path,help='Trusted local workload estimates JSON in bytes')
    a=p.parse_args()
    try:
        info=snapshot(a.workspace,a.backend,a.gpu_index)
        result=dict(hardware=info,preset=a.preset)
        if a.workload:
            result['plan']=plan(info,json.loads(a.workload.read_text(encoding='utf-8')),a.backend,a.preset)
        elif a.backend=='cuda' and not (info['gpu'] or {}).get('ok'):
            raise ResourceBlocked('Explicit CUDA probe failed: '+str(info['gpu']))
        print(json.dumps(result,indent=2,sort_keys=True))
        return 0
    except (ResourceBlocked,ValueError,ImportError,OSError) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc)}))
        return 1


if __name__=='__main__':
    raise SystemExit(main())

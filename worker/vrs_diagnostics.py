"""VRS-094 C: local hardware diagnostics and opt-in sampled phase profiling."""
import argparse
import json
import math
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

import psutil
import vrs_hardware as h
import vrs_preflight as pre

PHASES = ('validation', 'planning', 'admission', 'model_setup', 'preparation', 'inference', 'serialization')


def windows_storage(workspace):
    """Read-only exact disk-to-physical-disk mapping; ambiguity is UNKNOWN."""
    drive = Path(workspace).resolve().drive
    if not re.fullmatch(r'[A-Za-z]:', drive):
        return None
    exe = shutil.which('powershell.exe')
    if not exe:
        return None
    script = ("$ErrorActionPreference='Stop'; "
              f"$d=@(Get-Partition -DriveLetter '{drive[0]}' | Get-Disk); "
              "if($d.Count -ne 1 -or !$d[0].UniqueId -or "
              "$d[0].BusType -in @('Virtual','File Backed Virtual','Spaces','Unknown','RAID','iSCSI')){exit 2}; "
              "$p=@(Get-PhysicalDisk | Where-Object {$_.UniqueId -eq $d[0].UniqueId}); "
              "if($p.Count -ne 1){exit 2}; [string]$p[0].MediaType")
    try:
        result = subprocess.run([exe, '-NoProfile', '-NonInteractive', '-Command', script],
                                capture_output=True, text=True, timeout=8, check=True)
        return {'SSD': True, 'HDD': False}.get(result.stdout.strip())
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return None


def diagnostic(workspace, profile='review', gui=False):
    base = pre.check(workspace, profile, gui=gui)
    if base['hardware']['system'] == 'Windows':
        ssd = windows_storage(workspace)
        base['checks']['ssd'] = 'UNKNOWN' if ssd is None else ('PASS' if ssd else 'NOT_MET')
        states = base['checks'].values()
        base['status'] = 'NOT_MET' if 'NOT_MET' in states else ('UNVERIFIED' if 'UNKNOWN' in states else 'PASS')
    frequency = psutil.cpu_freq()
    swap = psutil.swap_memory()
    return {'schema': 1, 'preflight': base,
            'cpu_frequency_mhz': None if frequency is None else {k: float(getattr(frequency,k)) for k in ('current','min','max')},
            'swap': {'total': swap.total, 'used': swap.used, 'free': swap.free},
            'scientific_status': 'UNADJUDICATED'}


class Profiler:
    """Single-run collector. Wall-clock phase sums may overlap across threads.
    RSS/available RAM and allocator values are sampled, not guaranteed peaks.
    No paths, source content, labels or exception messages in profiling report.
    """
    def __init__(self, interval=.05):
        if type(interval) not in (int,float) or not math.isfinite(interval) or not .01 <= interval <= 5:
            raise ValueError('Sampling interval must be between 0.01 and 5 seconds')
        self.interval = interval
        self.proc = psutil.Process()
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.phases = {k: {'calls':0,'seconds_sum':0.,'seconds_max':0.,'errors':0} for k in PHASES}
        self.samples = self.sample_errors = 0
        self.rss_max = self.available_min = self.gpu_allocated_max = self.gpu_reserved_max = None
        self.thread = None
        self.finished = False

    def _sample(self):
        try:
            rss = self.proc.memory_info().rss
            available = psutil.virtual_memory().available
            with self.lock:
                self.samples += 1
                self.rss_max = max(self.rss_max or 0,rss)
                self.available_min = available if self.available_min is None else min(self.available_min,available)
        except (psutil.Error,OSError):
            with self.lock: self.sample_errors += 1

    def _loop(self):
        while not self.stop.wait(self.interval): self._sample()

    def __enter__(self):
        if self.thread is not None: raise ValueError('Profiler is single-use')
        self.started = time.perf_counter()
        self.cpu_start = self.proc.cpu_times()
        self._sample()
        self.thread = threading.Thread(target=self._loop,daemon=True)
        self.thread.start()
        return self

    def __exit__(self, typ, value, tb):
        self.stop.set(); self.thread.join(); self._sample()
        cpu_end = self.proc.cpu_times()
        self.cpu_seconds = cpu_end.user+cpu_end.system-self.cpu_start.user-self.cpu_start.system
        self.wall = time.perf_counter()-self.started
        self.finished = True
        self.failed = typ is not None

    def record(self, phase, seconds, failed=False):
        if phase not in self.phases or not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Invalid phase measurement')
        with self.lock:
            row=self.phases[phase]; row['calls']+=1; row['seconds_sum']+=seconds
            row['seconds_max']=max(row['seconds_max'],seconds); row['errors']+=int(failed)

    def call(self, phase, fn, *args, **kwargs):
        start=time.perf_counter(); failed=True
        try:
            value=fn(*args,**kwargs); failed=False; return value
        finally:
            self.record(phase,time.perf_counter()-start,failed)

    def gpu_sample(self, torch, index):
        # Called on the inference thread only, no forced synchronization/reset.
        try:
            allocated=int(torch.cuda.memory_allocated(index)); reserved=int(torch.cuda.memory_reserved(index))
            with self.lock:
                self.gpu_allocated_max=max(self.gpu_allocated_max or 0,allocated)
                self.gpu_reserved_max=max(self.gpu_reserved_max or 0,reserved)
        except (RuntimeError,ValueError,OSError):
            with self.lock: self.sample_errors+=1

    def report(self):
        if not self.finished: raise ValueError('Profile has not finished')
        return {'schema':1,'status':'FAILED' if self.failed else 'COMPLETED','wall_seconds':self.wall,
                'process_cpu_seconds':max(0,self.cpu_seconds),'sample_interval_seconds':self.interval,
                'samples':self.samples,'sample_errors':self.sample_errors,'sampled_rss_max_bytes':self.rss_max,
                'sampled_system_available_ram_min_bytes':self.available_min,
                'sampled_cuda_allocated_max_bytes':self.gpu_allocated_max,
                'sampled_cuda_reserved_max_bytes':self.gpu_reserved_max,
                'phases':self.phases,'scientific_status':'UNADJUDICATED'}


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='action',required=True)
    q=sub.add_parser('hardware'); q.add_argument('workspace'); q.add_argument('--profile',choices=('review','cpu','cuda'),default='review'); q.add_argument('--gui',action='store_true')
    q=sub.add_parser('profile')
    for k in ('manifest','review','alphabet','model_path','report_path','output'): q.add_argument(k)
    q.add_argument('--device',choices=('auto','cpu','cuda'),default='auto'); q.add_argument('--preset',choices=(*h.PRESETS,'silent'),default=h.DEFAULT_PRESET); q.add_argument('--interval',type=float,default=.05)
    a=vars(p.parse_args()); action=a.pop('action')
    if action=='hardware':
        result=diagnostic(**a); print(json.dumps(result,indent=2,allow_nan=False)); return {'PASS':0,'NOT_MET':1,'UNVERIFIED':2}[result['preflight']['status']]
    import vrs_inference as v
    prof=Profiler(a.pop('interval'))
    try:
        with prof: v.predict(**a,profiler=prof)
    except Exception:
        print(json.dumps(prof.report(),indent=2,allow_nan=False)); return 1
    print(json.dumps(prof.report(),indent=2,allow_nan=False)); return 0


if __name__=='__main__': raise SystemExit(main())

"""Local operations, redacted evidence, and opt-in managed worker. No remote actions."""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import vrs_contract as c
from vrs_process import background_options, liveness, session_state
from vrs_core import require
from vrs_desktop_api import Desktop, ReadLedger, ReadDecisions, atomic_json, safe, pinned
from vrs_exceptions import load_page
from vrs_coordinator import scheduler_lock

VERSION='0.10.1'
BASE='workspace/vrs101'
MIB=1024**2


def limits(value):
    c.fields(value,('cpu_threads','ram_mib','disk_mib'))
    for key,n in value.items():
        require(type(n) is int and 0<=n<=2**31-1,'Invalid resource ceiling')
    require(value['cpu_threads']<=256,'CPU thread ceiling too high')
    return value


def write_session(path,value):
    # Windows readers/antivirus can temporarily prevent an atomic replace.
    # Retry only PermissionError, bounded; never report a successful write otherwise.
    deadline=time.monotonic()+3
    while True:
        try:atomic_json(path,value);return
        except PermissionError:
            if os.name!='nt' or time.monotonic()>=deadline:raise
            time.sleep(.05)


class Operations(Desktop):
    def settings_ops(self):
        p=safe(self.root,'config/vrs-operations.json')
        return limits(c.load(p)) if p.exists() else dict(cpu_threads=0,ram_mib=0,disk_mib=0)

    def save_ops(self,value):
        atomic_json(safe(self.root,'config/vrs-operations.json'),limits(value)); return value

    def jobs(self):
        if not safe(self.root,'workspace/vrs095/ledger.sqlite').exists(): return []
        l=ReadLedger(self.root); result=[]
        with l._tx() as db:
            for row in db.execute('SELECT id,control,token,generation,receipts,checkpoint,backend FROM runs ORDER BY rowid'):
                rec=json.loads(row['receipts']); stage=l._next(rec); cp=json.loads(row['checkpoint']) if row['checkpoint'] else None
                completed=sum(rec[s]['state']=='COMPLETED' for s in c.STAGES)
                result.append(dict(id=row['id'],control=row['control'],locked=row['token'] is not None,stage=stage,completed=completed,total=len(c.STAGES),backend=row['backend'],generation=row['generation'],reason=rec[stage]['reason'] if stage else 'NONE',checkpoint=bool(cp)))
        return result

    def detail(self,run):
        c.digest_ok(run); l=ReadLedger(self.root)
        with l._tx() as db:
            row=l._row(db,'runs',run); manifest,receipts,_=l._validate(row); stage=l._next(receipts)
            scope=load_page(pinned(self.root,manifest['inputs']['groups'])); pages=None
            if row['checkpoint'] and stage in c.STAGES[:3]:
                cp=json.loads(row['checkpoint']); value=load_page(pinned(self.root,cp['artifact']))
                require(value.get('run_id')==run and value.get('stage')==stage,'Checkpoint mismatch')
                pages=dict(done=len(value['pages']),total=len(scope)); require([r['page'] for r in value['pages']]==sorted(int(k) for k in scope)[:pages['done']] and pages['done']<=pages['total'],'Invalid page denominator')
            log=[]
            for event in db.execute('SELECT seq,kind,payload FROM history WHERE run_id=? ORDER BY seq DESC LIMIT 100',(run,)):
                data=json.loads(event['payload']); kind=event['kind']; item=dict(seq=event['seq'],kind=kind if re.fullmatch('[A-Z_]{1,64}',kind) else 'OTHER')
                for key in ('stage','reason','state','control'):
                    val=data.get(key)
                    if val in (*c.STAGES,*c.REASONS,*c.STATES,'READY','PAUSED','CANCELLED','PAUSE_REQUESTED','CANCEL_REQUESTED','RESOURCE_PRESSURE','PROCESSING_OR_INTEGRITY_ERROR'): item[key]=val
                log.append(item)
            return dict(run=run,control=row['control'],stage=stage,pages=pages,history=log,receipts={s:dict(state=r['state'],reason=r['reason'],counts=r['counts']) for s,r in receipts.items()})

    def evidence(self,run):
        c.digest_ok(run); l=ReadLedger(self.root)
        with l._tx() as db:
            row=l._row(db,'runs',run); manifest,receipts,_=l._validate(row)
            result=dict(schema=1,scientific_status='UNADJUDICATED',run_id=run,control=row['control'],stages={s:dict(state=r['state'],reason=r['reason'],counts=r['counts'],artifact_sha256=r['artifact']['sha256'] if r['artifact'] else None) for s,r in receipts.items()},review=None,comparisons=[])
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if {'vrs096_decisions','vrs095_queue_runs'}<=tables and db.execute('SELECT 1 FROM vrs095_queue_runs WHERE run_id=?',(run,)).fetchone():
                snap,_=ReadDecisions(l).snapshot(db,run); result['review']=snap
            r=receipts['transcription_alignment']
            if r['state']=='COMPLETED':
                index=load_page(pinned(self.root,r['artifact'])); require(index['run_id']==run and index['scientific_status']=='UNADJUDICATED','Alignment binding mismatch')
                require([e['source_sha256'] for e in index['reports']]==[v['sha256'] for v in manifest['transcriptions']],'Comparison source coverage mismatch')
                for entry in index['reports']:
                    report=load_page(pinned(self.root,entry['report'])); obs=load_page(pinned(self.root,entry['observations'])); require(report['scientific_status']=='UNADJUDICATED' and obs['source_sha256']==entry['source_sha256'],'Unexpected comparison status/source')
                    if report['regions']: require(report['observations_sha256']==entry['observations']['sha256'] and report['source']['source_sha256']==entry['source_sha256'],'Comparison provenance mismatch')
                    rows=report['regions']; require(all(x['status'] in ('COMPARED','UNRESOLVED') for x in rows),'Invalid comparison status')
                    compared=sum(x['status']=='COMPARED' for x in rows); unresolved=len(rows)-compared; exact=sum(x.get('exact_notation_agreement') is True for x in rows); ambiguous=sum(x.get('ambiguous_optimum') is True for x in rows)
                    m=report['metrics']; require(all(m.get(k,0)==v for k,v in dict(COMPARED=compared,UNRESOLVED=unresolved,exact_notation_agreement=exact,ambiguous_optimum=ambiguous).items()),'Comparison denominator mismatch')
                    result['comparisons'].append(dict(source_sha256=entry['source_sha256'],report_sha256=entry['report']['sha256'],observations_sha256=entry['observations']['sha256'],regions=len(rows),compared=compared,unresolved=unresolved,exact_notation_agreement=exact,ambiguous_optimum=ambiguous))
            return result

    def export_preview(self,run):
        # Explicit local aggregate export only; never an outbox or publication.
        value=self.evidence(run); key=c.digest(value); rel=f'{BASE}/exports/{key}.json'; p=safe(self.root,rel)
        if p.exists(): require(c.load(p)==value,'Export collision')
        else: atomic_json(p,value)
        return rel

    def control(self,interpreter,action,run):
        require(action in ('pause','resume','cancel'),'Unsupported control'); c.digest_ok(run)
        p=python_path(interpreter); script=Path(__file__).with_name('vrs_runtime.py')
        proc=subprocess.run([str(p),str(script),str(self.root),action,run],cwd=self.root,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',timeout=120,**background_options())
        require(proc.returncode==0,'Worker rejected control request; inspect run status')
        value=json.loads(proc.stdout); return dict(control=value['control'],locked=value['locked'],stage=value['next_stage'])

    def session(self):
        import psutil
        p=safe(self.root,f'{BASE}/session.json')
        if not p.exists(): return dict(state='NOT_MANAGED')
        s=c.load(p); require(type(s['pid']) is int and re.fullmatch('[0-9a-f]{32}',s['id']) is not None,'Invalid session')
        observation,rss=liveness(s['pid'],s['created'],psutil)
        state=session_state(s['state'],observation,safe(self.root,f'{BASE}/stop-{s["id"]}').exists())
        return dict(state=state,id=s['id'],pid=s['pid'] if observation=='ACTIVE' else None,rss=rss,limits=s['limits'])

    def resources(self):
        import psutil
        from vrs_hardware import snapshot
        info=snapshot(self.root,'review'); disk=shutil.disk_usage(self.root)
        return dict(cpu_percent=psutil.cpu_percent(interval=.1),logical=info['logical'],allowed=info['allowed'],ram_total=info['ram_total'],ram_available=info['ram_available'],disk_total=disk.total,disk_free=disk.free,worker=self.session(),gpu='NOT_MEASURED',limits=self.settings_ops())

    def start(self,interpreter):
        require(self.session()['state'] in ('NOT_MANAGED','STOPPED','FAILED','NOT_RUNNING'),'Managed worker active or state unknown')
        p=python_path(interpreter); cfg=self.settings_ops(); ident=uuid.uuid4().hex; base=safe(self.root,BASE); base.mkdir(parents=True,exist_ok=True)
        script=Path(__file__).resolve()
        env=os.environ.copy()
        if cfg['cpu_threads']:
            for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'): env[key]=str(cfg['cpu_threads'])
        proc=subprocess.Popen([str(p),str(script),str(self.root),'serve',ident],cwd=self.root,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=env,**background_options(managed=True))
        threading.Thread(target=proc.wait,daemon=True).start()
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            s=self.session()
            if s.get('id')==ident and s['state']=='RUNNING': return s
            if proc.poll() is not None:
                from vrs_worker_log import WorkerLog
                error=ValueError('Worker startup failed; exit code '+str(proc.returncode))
                WorkerLog(self.root).failed(error)
                raise error
            time.sleep(.1)
        # No forced kill; a slow startup can still complete. Request cooperative stop.
        safe(self.root,f'{BASE}/stop-{ident}').touch(exist_ok=True)
        raise ValueError('Startup not confirmed; stop requested for this session')

    def stop(self):
        s=self.session(); require(s['state'] in ('RUNNING','STOP_REQUESTED'),'No active managed worker')
        safe(self.root,f'{BASE}/stop-{s["id"]}').touch(exist_ok=True); return self.session()

    def diagnostics(self):
        r=self.resources(); worker=r.pop('worker'); r['worker']=dict(state=worker['state'],rss=worker.get('rss'),limits=worker.get('limits'))
        counts={}
        for row in self.jobs(): counts[row['control']]=counts.get(row['control'],0)+1
        return dict(schema=1,version=VERSION,scope='LOCAL_AGGREGATE',resources=r,run_counts=counts)

    def notice(self):
        # No glyphs, raw source paths, or reviewer identities in desktop notifications.
        waiting=[]
        for r in self.jobs():
            if r['stage']=='exception_review' and r['reason']=='REVIEW_PENDING' and r['control']=='BLOCKED': waiting.append(r['id'])
        return len(waiting),c.digest(sorted(waiting))


def python_path(value):
    p=Path(value); require(p.is_absolute() and p.is_file() and p.name.lower() in ('python','python3','python.exe','python3.exe','python3.13','python3.12'),'Select local compute Python explicitly'); return p


def serve(root,ident):
    import psutil
    from vrs_runtime import Runtime
    from vrs_hardware import ResourceBlocked
    require(re.fullmatch('[0-9a-f]{32}',ident) is not None,'Invalid session ID')
    ops=Operations(root); root=ops.root; home=safe(root,BASE); home.mkdir(parents=True,exist_ok=True)
    with scheduler_lock(safe(root,f'{BASE}/manager.lock')):
        cfg=ops.settings_ops(); app=Runtime(root); original=app._admit
        def admit(ram,disk):
            if (cfg['ram_mib'] and ram>cfg['ram_mib']*MIB) or (cfg['disk_mib'] and disk>cfg['disk_mib']*MIB): raise ResourceBlocked('Local admission ceiling')
            return original(ram,disk)
        app._admit=admit
        if cfg['cpu_threads']:
            import torch
            torch.set_num_threads(min(torch.get_num_threads(),cfg['cpu_threads']))
        session=dict(id=ident,pid=os.getpid(),created=psutil.Process().create_time(),state='RUNNING',limits=cfg)
        path=safe(root,f'{BASE}/session.json'); stop=safe(root,f'{BASE}/stop-{ident}')
        def poll():
            while not app.stop.wait(.2):
                if stop.exists(): app.stop.set(); return
        thread=threading.Thread(target=poll,daemon=True); thread.start(); write_session(path,session)
        state='STOPPED'
        from vrs_worker_log import WorkerLog
        journal=WorkerLog(root); journal.start()
        try:
            while not app.stop.is_set() and not stop.exists():
                journal.sweep(app.sweep()); app.stop.wait(1)
        except BaseException as error:
            state='FAILED'; journal.failed(error); raise
        finally:
            app.stop.set(); thread.join(timeout=1)
            if state=='STOPPED':journal.stop()
            # Final acknowledgement follows the last runtime/log write. The
            # reader still requires the process to exit before reporting STOPPED.
            write_session(path,{**session,'state':state}); stop.unlink(missing_ok=True)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('root',type=Path); p.add_argument('action',choices=('serve',)); p.add_argument('id'); a=p.parse_args(); serve(a.root,a.id)


if __name__=='__main__': main()

"""Disposable native Windows candidate assembly and qualification; never production approval."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from vrs_portable import digest, local, need, environment, active, exe, save, extract
from vrs_prepare_plan import prepare


def assemble_runtime(base, target):
    base=Path(base).resolve(strict=True)
    for rel in ('python.exe','python313.dll','Lib/venv','Lib/ensurepip','DLLs/_tkinter.pyd','tcl'):
        need((base/rel).exists(),'Full CPython 3.13 runtime required: '+rel)
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(base.rglob('*')):
            r=p.relative_to(base); parts=r.parts
            # setup-python adds python3.exe as a symbolic alias. It is not
            # a runtime dependency; never copy or dereference that alias.
            root_file=len(parts)==1 and (p.name.lower() in ('python.exe','pythonw.exe','license.txt','news.txt') or p.suffix.lower()=='.dll')
            if parts[0].lower() not in ('lib','dlls','tcl','include','libs') and not root_file:continue
            if any(x.lower() in ('site-packages','__pycache__','test','tests') for x in parts):continue
            need(not p.is_symlink() and not getattr(p,'is_junction',lambda:False)() and not getattr(p.lstat(),'st_file_attributes',0)&1024,'Runtime link refused: '+r.as_posix())
            if p.is_file():z.write(p,r.as_posix())
    return digest(target)


def source_copy(source, root):
    from vrs_portable import load
    manifest=load(source/'portable_sources.json'); need(manifest['schema']==1,'Source manifest schema')
    for name,sha in manifest['files'].items():
        data=local(source,name).read_bytes(); need(hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==sha,'Source manifest mismatch')
        dst=local(root,name); dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(data)
    shutil.copyfile(source/'portable_sources.json',root/'portable_sources.json')


def fetch_wheels(profile, folder, root):
    # Resolve candidates on explicitly selected indexes, not in end-user Setup.
    env=environment(root); env.pop('PIP_NO_INDEX',None)
    base=[sys.executable,'-m','pip','--isolated','download','--only-binary=:all:','--dest',str(folder)]
    def get(args):subprocess.run(base+args,cwd=root,env=env,check=True,timeout=1800)
    req=['Pillow==12.3.0','psutil==7.2.2','pystray==0.19.5']
    if profile!='review':
        backend='cpu' if profile=='cpu' else 'cu128'
        get(['--no-deps','--index-url','https://download.pytorch.org/whl/'+backend,'torch==2.10.0+'+backend]); torch=list(folder.glob('torch-*.whl')); need(len(torch)==1,'Torch wheel cardinality')
        req+=['numpy==2.3.5','PyMuPDF==1.26.7',str(torch[0])]
    get(['--index-url','https://pypi.org/simple',*req])


def batch(root,name,*args,timeout=1800):
    # No untrusted command fragments; only fixed script names and generated arguments.
    need(name in ('Setup','Repair','Probe','Stop','Diagnostics'),'Invalid command')
    need(all(isinstance(a,str) and not any(c in a for c in '&|<>^%\"\r\n') for a in args),'Unsafe batch argument')
    command='cmd.exe /d /s /c \"\"'+str(root/(name+'.bat'))+'\" '+subprocess.list2cmdline(list(args))+'\"'
    subprocess.run(command,cwd=root.parent,env=environment(root),check=True,timeout=timeout)


def qualify(source,profile,report):
    need(os.name=='nt' and sys.version_info[:2]==(3,13),'Native Windows CPython 3.13 required')
    source=source.resolve(strict=True); report=report.resolve(); report.parent.mkdir(parents=True,exist_ok=True)
    result={'schema':1,'profile':profile,'scope':'DISPOSABLE_NATIVE_CANDIDATE','production_approved':False,'checks':{},'elapsed_seconds':{}}
    def step(name,fn):
        t=time.monotonic(); result['checks'][name]='RUNNING'; save(report,result); print('VRS native check: '+name,flush=True)
        try:value=fn()
        except BaseException as error:
            result['checks'][name]='FAIL';result['failure']={'check':name,'type':type(error).__name__}
            # Only validated structured records from the disposable workspace.
            try:
                from vrs_portable_logs import records
                result['technical_log_tail']=records(root)[-40:]
            except Exception:pass
            raise
        else:result['checks'][name]='PASS';return value
        finally:result['elapsed_seconds'][name]=round(time.monotonic()-t,3);save(report,result)
    with tempfile.TemporaryDirectory(prefix='vrs-native-') as d:
        home=Path(d); root=home/'VRS space \u00fc'; root.mkdir(); root=root.resolve(); assets=home/'assets';assets.mkdir(); wheels=assets/'wheels';wheels.mkdir(); rt=assets/'python-runtime.zip'
        step('source_manifest',lambda:source_copy(source,root))
        from vrs_build_portable import build
        def source_zip():
            z=build(root); h=digest(z);z.unlink();z=build(root);need(digest(z)==h,'Nondeterministic source ZIP');z.unlink();return h
        result['source_zip_sha256']=step('source_zip',source_zip)
        result['runtime_sha256']=step('runtime_assembly',lambda:assemble_runtime(sys.base_prefix,rt))
        step('bootstrap_extract',lambda:((root/'bootstrap').mkdir(),extract(rt,root/'bootstrap')))
        step('hardware_before_download',lambda:batch(root,'Probe'))
        step('resolve_candidate_wheels',lambda:fetch_wheels(profile,wheels,root))
        plan=step('lock_candidate',lambda:prepare(root,profile,rt,wheels));result['plan_sha256']=plan['sha256'];result['wheel_count']=plan['wheels'];result['lock']=json.loads((root/plan['plan']).read_text())
        # Consent is limited to this disposable test, not a transferable owner approval.
        step('offline_setup',lambda:batch(root,'Setup','--profile',profile,'--plan',plan['plan'],'--approve',plan['sha256']))
        def run(code):subprocess.run([str(exe(root,profile)),'-s','-c',code],cwd=root,env=environment(root),check=True,timeout=90)
        smoke="import sys, pathlib, tkinter as t; r=pathlib.Path.cwd(); assert pathlib.Path(sys.base_prefix).resolve().is_relative_to(r); assert pathlib.Path(sys.prefix).resolve().is_relative_to(r); w=t.Tk(); w.update(); assert pathlib.Path(w.tk.eval('info library')).resolve().is_relative_to(r); w.destroy(); import PIL,psutil,pystray"
        if profile=='review':smoke+="; import importlib.util as u; assert all(u.find_spec(x) is None for x in ('torch','numpy','fitz'))"
        else:smoke+="; import torch; assert torch.ones(4).sum().item()==4"
        step('native_gui_and_profile',lambda:run(smoke))
        def desktop():
            run("""import tkinter as tk, time
from pathlib import Path
from unittest.mock import patch
from vrs_monitor import Monitor
from vrs_portable_ui import launch
from vrs_portable_logs import records
captured=[]; original=Monitor.__init__
def init(self,*a,**kw):
    original(self,*a,**kw); captured.append(self)
def exercise(w):
    app=captured[0]
    def settle():
        deadline=time.monotonic()+20
        while app.future is not None and time.monotonic()<deadline:w.update();time.sleep(.02)
        assert app.future is None
    settle(); app.show('Logs'); settle(); assert 'COMMAND_OK' in app.log_text.get('1.0','end'); app.show('Jobs'); settle(); app.close()
with patch.object(Monitor,'__init__',init),patch.object(tk.Tk,'mainloop',exercise):launch(Path.cwd(),'start')
assert not any(x['event']=='CRASH' for x in records(Path.cwd()))
""")
        step('actual_desktop_log_view',desktop)
        step('native_dpapi',lambda:run("from pathlib import Path; from vrs_portable_secrets import store,read,path; r=Path.cwd(); s='VRS_GITHUB_TOKEN_FIXTURE'; v='synthetic-test-value'; store(r,s,v); assert v.encode() not in path(r,s).read_bytes(); assert read(r,s)==v; path(r,s).unlink()"))
        def test(names):subprocess.run([str(exe(root,profile)),'-s','-m','unittest','-v',*names],cwd=root,env=environment(root),check=True,timeout=1200)
        step('portable_regression',lambda:test(['test_vrs_portable','test_vrs_prepare_plan','test_vrs_worker_log','test_vrs_native_acceptance']))
        if profile=='cpu':step('cpu_integration',lambda:test(['test_vrs_runtime','test_vrs_desktop','test_vrs_operations','test_vrs_learning','test_vrs_repository']))
        step('stop_idle_worker',lambda:batch(root,'Stop'))
        step('diagnostics',lambda:batch(root,'Diagnostics'))
        marker=root/'workspace'/'preserve.txt';marker.parent.mkdir(exist_ok=True);marker.write_text('synthetic-state'); moved=home/'VRS relocated';root.rename(moved);root=moved
        def moved_check():
            try:active(root)
            except ValueError:return
            raise AssertionError('Stale environment accepted')
        step('moved_environment_refused',moved_check);step('offline_repair',lambda:batch(root,'Repair'));step('relocated_gui',lambda:run(smoke));need((root/'workspace/preserve.txt').read_text()=='synthetic-state','State lost')
        step('delete_root',lambda:shutil.rmtree(root));need(not root.exists(),'Root not removed')
    result['status']='CANDIDATE_TEST_PASS';save(report,result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile',choices=('review','cpu','cuda'),required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--disposable-test',action='store_true',required=True);a=p.parse_args();qualify(Path(__file__).resolve().parent,a.profile,a.report)

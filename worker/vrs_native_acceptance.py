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
    req=['Pillow==13.0.0','psutil==7.2.2','pystray==0.19.5']
    if profile!='review':
        backend='cpu' if profile=='cpu' else 'cu130'
        get(['--no-deps','--index-url','https://download.pytorch.org/whl/'+backend,'torch==2.13.0+'+backend]); torch=list(folder.glob('torch-*.whl')); need(len(torch)==1,'Torch wheel cardinality')
        req+=['numpy==2.3.5','PyMuPDF==1.26.7',str(torch[0])]
    get(['--index-url','https://pypi.org/simple',*req])


def batch(root,name,*args,timeout=1800):
    # No untrusted command fragments; only fixed script names and generated arguments.
    need(name in ('Setup','Repair','Probe','Stop','Diagnostics'),'Invalid command')
    need(all(isinstance(a,str) and not any(c in a for c in '&|<>^%\"\r\n') for a in args),'Unsafe batch argument')
    command='cmd.exe /d /s /c \"\"'+str(root/(name+'.bat'))+'\" '+subprocess.list2cmdline(list(args))+'\"'
    subprocess.run(command,cwd=root.parent,env=environment(root),check=True,timeout=timeout)


def qualify(source,profile,report,owner_interactive=False,compat_source=None):
    need(os.name=='nt' and sys.version_info[:2]==(3,13),'Native Windows CPython 3.13 required')
    import ctypes
    elevated=bool(ctypes.windll.shell32.IsUserAnAdmin())
    if owner_interactive:need(not elevated,'Owner qualification requires a standard non-elevated Windows process')
    source=source.resolve(strict=True); report=report.resolve(); report.parent.mkdir(parents=True,exist_ok=True)
    result={'schema':1,'profile':profile,'scope':'DISPOSABLE_NATIVE_CANDIDATE','production_approved':False,'checks':{},'elapsed_seconds':{},'windows_process_elevated':elevated,'owner_interactive_requested':owner_interactive}
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
        def source_syntax():
            manifest=json.loads(local(root,'portable_sources.json').read_text(encoding='utf-8'))
            for name in manifest['files']:
                if name.endswith(('.py','.pyw')):
                    compile(local(root,name).read_bytes(),name,'exec')
        step('source_syntax',source_syntax)
        from vrs_build_portable import build,RELEASE_VERSION
        result['release_version']=RELEASE_VERSION;result['source_manifest_sha256']=digest(local(root,'portable_sources.json'))
        def source_zip():
            z=build(root); h=digest(z);z.unlink();z=build(root);need(digest(z)==h,'Nondeterministic source ZIP');z.unlink();return h
        result['source_zip_sha256']=step('source_zip',source_zip)
        result['runtime_sha256']=step('runtime_assembly',lambda:assemble_runtime(sys.base_prefix,rt))
        step('bootstrap_extract',lambda:((root/'bootstrap').mkdir(),extract(rt,root/'bootstrap')))
        step('hardware_before_download',lambda:batch(root,'Probe'))
        step('resolve_candidate_wheels',lambda:fetch_wheels(profile,wheels,root))
        plan=step('lock_candidate',lambda:prepare(root,profile,rt,wheels));result['plan_sha256']=plan['sha256'];result['wheel_count']=plan['wheels'];result['lock']=json.loads((root/plan['plan']).read_text())
        from vrs_license_inventory import inventory
        result['component_license_inventory']=step('component_license_inventory',lambda:inventory(root,profile,plan['plan'],plan['sha256']))
        from vrs_build_portable import build_candidate
        def candidate_zip():
            candidate=build_candidate(root,profile,plan['plan'],plan['sha256'])
            value=dict(sha256=digest(candidate),bytes=candidate.stat().st_size,redistribution_approved=False)
            destination=home/'candidate-extracted';destination.mkdir()
            extract(candidate,destination)
            package=(destination/'Voynich Research Studio').resolve(strict=True)
            need(digest(local(package,plan['plan']))==plan['sha256'],'Extracted plan hash mismatch')
            metadata=json.loads(local(package,'CANDIDATE.json').read_text(encoding='utf-8'))
            need(metadata==dict(schema=1,version=RELEASE_VERSION,profile=profile,plan_sha256=plan['sha256'],source_manifest_sha256=result['source_manifest_sha256'],redistribution_approved=False,release_approved=False),'Candidate metadata mismatch')
            value['version']=metadata['version'];value['source_manifest_sha256']=metadata['source_manifest_sha256']
            sbom=local(package,'SBOM.cdx.json').read_bytes()
            value['sbom_sha256']=hashlib.sha256(sbom).hexdigest()
            report.with_name(report.stem+'-sbom.json').write_bytes(sbom)
            candidate.unlink();return value,package
        result['candidate_zip'],package=step('locked_candidate_zip',candidate_zip)
        # Discard the assembly tree: all subsequent checks use the extracted ZIP.
        shutil.rmtree(root);root=package
        # Consent is limited to this disposable test, not a transferable owner approval.
        step('offline_setup',lambda:batch(root,'Setup','--profile',profile,'--plan',plan['plan'],'--approve',plan['sha256']))
        def run(code):subprocess.run([str(exe(root,profile)),'-s','-c',code],cwd=root,env=environment(root),check=True,timeout=90)
        smoke="import sys, pathlib, tkinter as t; r=pathlib.Path.cwd().resolve(strict=True); assert pathlib.Path(sys.base_prefix).resolve()==r/'runtime'/'"+profile+"', 'base_prefix'; assert pathlib.Path(sys.prefix).resolve()==r/'.venv'/'"+profile+"', 'prefix'; w=t.Tk(); w.update(); assert pathlib.Path(w.tk.eval('info library')).resolve().is_relative_to(r), 'Tcl library'; w.destroy(); import PIL,psutil,pystray"
        if profile=='review':smoke+="; import importlib.util as u; assert all(u.find_spec(x) is None for x in ('torch','numpy','fitz'))"
        elif profile=='cuda':smoke+="; import torch; assert torch.cuda.is_available(); assert torch.ones(4,device='cuda:0').sum().item()==4; torch.cuda.synchronize(0)"
        else:smoke+="; import torch; assert torch.version.cuda is None; assert torch.ones(4).sum().item()==4"
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
        def ui_profile():
            report_path=local(root,'workspace/ui-qualification.json')
            code="""import tkinter as tk,time,json,statistics,os
from pathlib import Path
from unittest.mock import patch
from vrs_monitor import Monitor
from vrs_portable_ui import launch
from vrs_portable import save
from vrs_operations import Operations
captured=[];original=Monitor.__init__
def init(self,*args,**kwargs):
    original(self,*args,**kwargs);captured.append(self)
def exercise(w):
    app=captured[0]
    def settle():
        deadline=time.monotonic()+20
        while app.future is not None and time.monotonic()<deadline:
            w.update();time.sleep(.01)
        assert app.future is None,'UI request timeout'
    def until(fn):
        deadline=time.monotonic()+15
        while not fn() and time.monotonic()<deadline:
            w.update();time.sleep(.01)
        assert fn(),'UI state timeout'
    settle();w.geometry('1024x650');w.update()
    geometry=[w.winfo_width(),w.winfo_height()]
    assert geometry==[1024,650]
    pages=[]
    for page in ('Sources','Settings','Review','Jobs','Evidence','Logs','Home'):
        start=time.perf_counter();app.request_view(page)
        until(lambda:app.view==page and app.pending_view is None)
        settle();w.update()
        assert app.view==page,('requested',page,'actual',app.view)
        pages.append(dict(page=page,seconds=time.perf_counter()-start,body_width=w.body.winfo_width() if hasattr(w,'body') else app.body.winfo_width()))
    # Keep the UI event loop active during real asynchronous background work.
    gaps=[];previous=time.perf_counter()
    def pulse():
        nonlocal previous
        now=time.perf_counter();gaps.append((now-previous)*1000);previous=now
        if len(gaps)<25:w.after(20,pulse)
    app.quiet_task(lambda:time.sleep(.65),lambda _:None);w.after(20,pulse);until(lambda:len(gaps)==25);settle()
    timing=dict(samples=len(gaps),p95_ms=sorted(gaps)[23],max_ms=max(gaps))
    assert timing['max_ms']<500,'Event loop stall exceeds synthetic budget'
    result=dict(scope='SYNTHETIC_UI_MEASUREMENT',geometry=geometry,screen=[w.winfo_screenwidth(),w.winfo_screenheight()],tk_scaling=float(w.tk.call('tk','scaling')),pages=pages,event_loop=timing,keyboard_bindings=all(bool(w.bind('<Control-'+str(i)+'>')) for i in range(1,8)),tray='NOT_RUN')
    assert result['keyboard_bindings']
    if os.environ.get('VRS_OWNER_TRAY_TEST')=='1':
        app.enable_tray();until(lambda:app.tray_ready);assert app.tray.visible
        app.hide();w.update();assert w.state()=='withdrawn'
        app.events.put('show');until(lambda:w.state()!='withdrawn')
        app.notice_done((1,'synthetic-qualification'))
        app.events.put('review');until(lambda:app.view=='Review');settle()
        result['tray']='API_LIFECYCLE_PASS_VISUAL_CONFIRMATION_REQUIRED'
        app.events.put('exit');until(lambda:app.closing)
    else:app.close()
    save(Path.cwd()/'workspace/ui-qualification.json',result)
with patch.object(Monitor,'__init__',init),patch.object(tk.Tk,'mainloop',exercise):
    launch(Path.cwd(),'start')
"""
            env=environment(root)
            if owner_interactive:env['VRS_OWNER_TRAY_TEST']='1'
            subprocess.run([str(exe(root,profile)),'-s','-c',code],cwd=root,env=env,check=True,timeout=180)
            return json.loads(report_path.read_text(encoding='utf-8'))
        result['ui_measurements']=step('ui_responsiveness_and_keyboard',ui_profile)
        if profile!='review':
            def runtime_benchmark():
                result=subprocess.run([str(exe(root,profile)),'-s',str(local(root,'vrs_benchmark.py')),'--runtime-candidate','--device',profile,'--repeats','2','--boxes','256'],cwd=root,env=environment(root),capture_output=True,text=True,check=True,timeout=240)
                value=json.loads(result.stdout);need(value['parity'] is True,'Classifier parity failed');return value
            result['runtime_classifier_benchmark']=step('runtime_classifier_benchmark',runtime_benchmark)
        step('native_dpapi',lambda:run("from pathlib import Path; from vrs_portable_secrets import store,read,path; r=Path.cwd(); s='VRS_GITHUB_TOKEN_FIXTURE'; v='synthetic-test-value'; store(r,s,v); assert v.encode() not in path(r,s).read_bytes(); assert read(r,s)==v; path(r,s).unlink()"))
        def test(names):
            env=environment(root);env.pop('VRS_NATIVE_CUDA_TEST',None)
            if profile=='cuda':env['VRS_NATIVE_CUDA_TEST']='1'
            subprocess.run([str(exe(root,profile)),'-s','-m','unittest','-v',*names],cwd=root,env=env,check=True,timeout=1200)
        step('portable_regression',lambda:test(['test_vrs_portable','test_vrs_prepare_plan','test_vrs_worker_log','test_vrs_native_acceptance','test_vrs_source_update','test_vrs_license_inventory','test_vrs_ui_format']))
        if profile=='cuda':step('native_cuda_candidate',lambda:test(['test_vrs_runtime.RuntimeTests.test_native_cuda_candidate','test_vrs_runtime.RuntimeTests.test_native_cuda_checkpoint_resume','test_vrs_learning.LearningTests.test_native_cuda_training_and_cpu_replay']))
        if profile=='cpu':step('cpu_integration',lambda:test(['test_vrs_runtime','test_vrs_desktop','test_vrs_operations','test_vrs_learning','test_vrs_repository','test_vrs_coordinator','test_vrs_service','test_vrs_exceptions','test_vrs_modules','test_vrs_rc_preflight','test_vrs_rc_snapshot','test_vrs_rc1_intake']))
        if profile=='cpu' and compat_source is not None:
            def cross_version():
                result=subprocess.run([str(exe(root,profile)),'-B','-s',str(local(root,'vrs_rc_cross_version.py')),'--old-source',str(compat_source)],cwd=root,env=environment(root),capture_output=True,text=True,check=True,timeout=1200)
                value=json.loads(result.stdout);need(value['status']=='PASS','Cross-version fixture failed');return value
            result['cross_version']=step('immutable_013_upgrade_rollback_replay',cross_version)
        step('stop_idle_worker',lambda:batch(root,'Stop'))
        step('diagnostics',lambda:batch(root,'Diagnostics'))
        marker=root/'workspace'/'preserve.txt';marker.parent.mkdir(exist_ok=True);marker.write_text('synthetic-state'); moved=home/'VRS relocated';root.rename(moved);root=moved.resolve(strict=True)
        def moved_check():
            try:active(root)
            except ValueError:return
            raise AssertionError('Stale environment accepted')
        step('moved_environment_refused',moved_check);step('offline_repair',lambda:batch(root,'Repair'));step('relocated_gui',lambda:run(smoke));need((root/'workspace/preserve.txt').read_text()=='synthetic-state','State lost')
        if profile=='review':
            def restored_package():
                # Actual portable installation, not just the synthetic ledger fixture.
                from vrs_rc_snapshot import snapshot,restore
                bundle=home/'private-backup';out=home/'restored-copy'
                value=snapshot(root,bundle);restore(bundle,out,value['manifest_sha256'])
                restored=out/'app'
                try:active(restored)
                except ValueError:pass
                else:raise AssertionError('Restored stale environment accepted')
                batch(restored,'Repair')
                subprocess.run([str(exe(restored,profile)),'-s','-c',smoke],cwd=restored,env=environment(restored),check=True,timeout=90)
                need((restored/'workspace/preserve.txt').read_text()=='synthetic-state','Restored state lost')
                need((root/'workspace/preserve.txt').read_text()=='synthetic-state','Original state lost')
                shutil.rmtree(bundle);shutil.rmtree(out)
                return value
            result['portable_snapshot_restore']=step('review_full_package_snapshot_restore_repair',restored_package)
        step('delete_root',lambda:shutil.rmtree(root));need(not root.exists(),'Root not removed')
    result['status']='CANDIDATE_TEST_PASS';save(report,result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile',choices=('review','cpu','cuda'),required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--disposable-test',action='store_true',required=True);p.add_argument('--owner-interactive',action='store_true');p.add_argument('--compat-source',type=Path);a=p.parse_args();qualify(Path(__file__).resolve().parent,a.profile,a.report,a.owner_interactive,a.compat_source)

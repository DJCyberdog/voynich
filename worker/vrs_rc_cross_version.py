"""VRS-140 real 0.13.x source upgrade/rollback fixture; disposable synthetic inputs only."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from vrs_build_portable import build,source_payload
from vrs_portable import digest,need
from vrs_source_update import blob,installed,update,launcher_critical,pending
from vrs_rc_preflight import inspect
from vrs_rc_snapshot import snapshot,restore

OLD_MANIFEST='21db923c821bf088d9b9cf0931cf57cc4ad722c0'
OLD_COMMIT='74eeab963a6451b63496ed8e29f7c0518b939980'

def source_copy(source,target):
    target.mkdir()
    for name,data in source_payload(source).items():
        p=target/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)

def fixture_package_copy(state,source,target):
    """Test-only full-package migration on disposable state; never used as updater."""
    old_files,_=installed(state)
    source_copy(source,target)
    # Source manifests contain relative nested paths, e.g. module_assets/*.
    # Copy only unmanaged fixture leaves, not entire source-containing folders.
    for parent,dirs,names in os.walk(state,followlinks=False):
        base=Path(parent)
        for d in dirs:
            need(not (base/d).is_symlink() and not getattr((base/d),'is_junction',lambda:False)(),'Fixture link refused')
        dirs[:]=[d for d in dirs if d!='__pycache__' and not (base==state and d=='dist')]
        for name in names:
            p=base/name;rel=p.relative_to(state).as_posix()
            if rel in old_files:continue
            dest=target/rel
            need(not p.is_symlink() and p.is_file() and not dest.exists(),'Fixture state collision: '+rel)
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    return target


def command(root,*args):
    env=os.environ.copy();env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
    out=subprocess.run([sys.executable,'-B','-s',*map(str,args)],cwd=root,env=env,capture_output=True,text=True,check=True,timeout=180)
    return json.loads(out.stdout)

def run(old_source,new_source):
    old_source=Path(old_source).resolve(strict=True);new_source=Path(new_source).resolve(strict=True)
    need(blob((old_source/'portable_sources.json').read_bytes())==OLD_MANIFEST,'Wrong immutable 0.13.x source manifest')
    with tempfile.TemporaryDirectory(prefix='vrs-cross-version-') as d:
        home=Path(d);old=home/'old-app';new=home/'new-source';backup=home/'backup';rollback=home/'rollback'
        source_copy(old_source,old);source_copy(new_source,new)
        old_zip=build(old);old_archive=home/'old.zip';old_zip.rename(old_archive)
        new_zip=build(new);new_archive=home/'new.zip';new_zip.rename(new_archive)
        old_digest=digest(old_archive);new_digest=digest(new_archive)
        _,old_pins=installed(old);_,new_pins=installed(new)
        generated=command(old,'-c',"""import json,shutil
from pathlib import Path
from test_vrs_runtime import RuntimeTests
f=RuntimeTests();f.setUp()
try:
    run=f.run_to_review();items=f.app.review_items(run,limit=1000)['items'];item=items[0]
    f.app.submit(f.decision(run,item,'deferred'))
    item=f.app.review_items(run)['items'][0];f.app.submit(f.decision(run,item,'glyph'))
    for item in f.app.review_items(run,limit=1000)['items']:f.app.submit(f.decision(run,item,'false_positive'))
    assert f.status(run)['control']=='READY'
    for p in f.root.iterdir():
        dest=Path.cwd()/p.name
        assert not dest.exists()
        if p.is_dir():shutil.copytree(p,dest)
        else:shutil.copyfile(p,dest)
    print(json.dumps(dict(run=run,worker=f.app.identity)))
finally:f.doCleanups()
""")
        run_id=generated['run'];worker=generated['worker']
        def cli(root,action,*args):return command(root,root/'vrs_runtime.py',root,action,*args)
        baseline_status=cli(old,'status',run_id);baseline_queue=cli(old,'queue',run_id)
        baseline=inspect(old,worker);need(baseline['counts']['foreign_worker']==0 and baseline['counts']['decision_revisions']>=2,'Historical fixture missing')
        h=snapshot(old,backup)['manifest_sha256']
        full_package=any(old_pins.get(n)!=new_pins.get(n) for n in set(old_pins)|set(new_pins) if launcher_critical(n))
        work=old
        if full_package:
            try:update(old,new_archive,new_digest)
            except ValueError as e:need('full package migration' in str(e),'Wrong launcher fence failure')
            else:raise ValueError('Unsafe launcher replacement allowed')
            need(not pending(old) and installed(old)[1]==old_pins and inspect(old,worker)==baseline,'Rejected update changed original')
            work=fixture_package_copy(old,new_source,home/'new-app')
        else:need(update(old,new_archive,new_digest)['status']=='UPDATED','Source upgrade failed')
        need(installed(work)[1]==new_pins and inspect(work,worker)==baseline,'Source upgrade altered historical ledger')
        need(cli(work,'status',run_id)==baseline_status and cli(work,'queue',run_id)==baseline_queue,'Historical CLI mismatch')
        registered=cli(work,'list');need(len(registered)==1 and registered[0]['worker']==worker,'Worker binding changed')
        current=command(work,'-c',"import json; from pathlib import Path; from vrs_runtime import Runtime; print(json.dumps(Runtime(Path.cwd()).identity))")
        changed=current!=worker
        if changed:
            # Changed scientific code must not resume or relabel the old run.
            need(inspect(work,current)['counts']['foreign_worker']==1,'Foreign worker not detected')
            need(cli(work,'once')==[] and inspect(work,worker)==baseline,'Changed worker executed historical evidence')
            if full_package:
                work=old
            else:need(update(old,old_archive,old_digest)['status']=='UPDATED','Source rollback failed')
            need(installed(work)[1]==old_pins and inspect(work,worker)==baseline,'Rollback changed historical ledger')
        need(cli(work,'once')[0]['stage']=='exception_review','Review resume failed')
        need(cli(work,'once')[0]['control']=='COMPLETED','Alignment resume failed')
        upgraded=cli(work,'status',run_id);completed=inspect(work,worker)
        if not changed:
            if full_package:work=fixture_package_copy(work,old_source,home/'old-resumed')
            else:need(update(old,old_archive,old_digest)['status']=='UPDATED','Source rollback failed')
        need(installed(work)[1]==old_pins and inspect(work,worker)==completed and cli(work,'status',run_id)==upgraded,'Source rollback lost new decisions or receipts')
        restore(backup,rollback,h);restored=rollback/'app'
        need(installed(restored)[1]==old_pins and inspect(restored,worker)==baseline,'Snapshot rollback mismatch')
        need(cli(restored,'status',run_id)==baseline_status and cli(restored,'queue',run_id)==baseline_queue,'Restored historical CLI mismatch')
        need(cli(restored,'once')[0]['stage']=='exception_review','Restored review resume failed')
        need(cli(restored,'once')[0]['control']=='COMPLETED','Restored alignment resume failed')
        replayed=cli(restored,'status',run_id)
        need(replayed['receipts']==upgraded['receipts'],'Cross-version deterministic receipt mismatch')
        return dict(status='PASS',scope='SYNTHETIC_IMMUTABLE_013_UPGRADE_ROLLBACK_REPLAY',old_commit=OLD_COMMIT,
                    old_source_zip_sha256=old_digest,new_source_zip_sha256=new_digest,snapshot_sha256=h,
                    initial_ledger_sha256=baseline['ledger_sha256'],completed_ledger_sha256=completed['ledger_sha256'],
                    worker_identity=worker,current_worker_identity=current,worker_identity_changed=changed,foreign_worker_fenced=changed,resume_requires_rollback=changed,decision_revisions=baseline['counts']['decision_revisions'],
                    full_package_fixture=full_package,launcher_update_fenced=full_package,
                    historical_cli_parity=True,receipt_parity=True,scientific_status='UNADJUDICATED')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--old-source',required=True,type=Path);p.add_argument('--new-source',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args()
    print(json.dumps(run(a.old_source,a.new_source),sort_keys=True))

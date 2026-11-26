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
from vrs_source_update import blob,installed,update
from vrs_rc_preflight import inspect
from vrs_rc_snapshot import snapshot,restore

OLD_MANIFEST='21db923c821bf088d9b9cf0931cf57cc4ad722c0'
OLD_COMMIT='74eeab963a6451b63496ed8e29f7c0518b939980'

def source_copy(source,target):
    target.mkdir()
    for name,data in source_payload(source).items():
        p=target/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)

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
        need(update(old,new_archive,new_digest)['status']=='UPDATED','Source upgrade failed')
        need(installed(old)[1]==new_pins and inspect(old,worker)==baseline,'Source upgrade altered historical ledger')
        need(cli(old,'status',run_id)==baseline_status and cli(old,'queue',run_id)==baseline_queue,'Historical CLI mismatch')
        registered=cli(old,'list');need(len(registered)==1 and registered[0]['worker']==worker,'Worker binding changed')
        need(cli(old,'once')[0]['stage']=='exception_review','Review resume failed')
        need(cli(old,'once')[0]['control']=='COMPLETED','Alignment resume failed')
        upgraded=cli(old,'status',run_id);completed=inspect(old,worker)
        need(update(old,old_archive,old_digest)['status']=='UPDATED','Source rollback failed')
        need(installed(old)[1]==old_pins and inspect(old,worker)==completed and cli(old,'status',run_id)==upgraded,'Source rollback lost new decisions or receipts')
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
                    worker_identity=worker,decision_revisions=baseline['counts']['decision_revisions'],
                    historical_cli_parity=True,receipt_parity=True,scientific_status='UNADJUDICATED')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--old-source',required=True,type=Path);p.add_argument('--new-source',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args()
    print(json.dumps(run(a.old_source,a.new_source),sort_keys=True))

"""Disposable exact RC1 -> current-source -> RC1 qualification, no owner distribution."""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from vrs_build_portable import source_payload
from vrs_source_update import PREFIX, RC1_BASE_BLOB, MANIFEST, blob


def exercise(old,new):
    old_files=source_payload(old);new_files=source_payload(new)
    assert blob(old_files[MANIFEST])==RC1_BASE_BLOB, 'wrong immutable RC1 source'
    sha=lambda data:hashlib.sha256(data).hexdigest()
    with tempfile.TemporaryDirectory(prefix='VRS RC2 disposable ') as directory:
        root=Path(directory)/'application';root.mkdir()
        for name,data in old_files.items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        sentinels={name:name.encode() for name in ('data/rc1/source','workspace/ledger','workspace/outbox','config/portable.json','bootstrap/python.exe','runtime/cuda/python.exe','.venv/cuda/Scripts/python.exe','cache/downloads/wheel')}
        for name,data in sentinels.items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        stage=root/'temp/rc2';stage.mkdir(parents=True)
        script=stage/'vrs_source_update.py';script.write_bytes(new_files['vrs_source_update.py'])
        archive=stage/'fixture.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in sorted(new_files.items()):z.writestr(PREFIX+name,data)
        def command(action,*args):
            result=subprocess.run([sys.executable,'-I','-B',str(script),action,'--root',str(root),*args],check=True,text=True,capture_output=True)
            return json.loads(result.stdout)
        def check(expected):
            assert source_payload(root)==expected, 'managed source byte mismatch'
            for name,data in sentinels.items():assert (root/name).read_bytes()==data, name
        applied=command('apply-rc2','--source',str(archive),'--approve',sha(archive.read_bytes()),'--base',sha(old_files[MANIFEST]),'--target',sha(new_files[MANIFEST]))
        assert applied['status']=='UPDATED' and applied['rollback_retained']
        check(new_files)
        assert command('rollback-rc2')['status']=='ROLLED_BACK'
        check(old_files)
        return {'status':'PASS','base_files':len(old_files),'target_files':len(new_files),'private_sentinels':len(sentinels),'base_manifest_sha256':sha(old_files[MANIFEST]),'target_manifest_sha256':sha(new_files[MANIFEST]),'interpreter':sys.version.split()[0],'owner_runtime_test':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--old-source',required=True,type=Path)
    p.add_argument('--new-source',type=Path,default=Path(__file__).resolve().parent)
    a=p.parse_args()
    print(json.dumps(exercise(a.old_source,a.new_source),sort_keys=True))

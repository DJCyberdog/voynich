"""Self-bootstrap owner-test setup: only local runtime, hashed assets and explicit profile."""
import argparse
import json
import os
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from vrs_build_portable import source_payload
from vrs_portable import PROFILES, digest, environment, exclusive, local, need, probe, save, setup, load, active
from vrs_prepare_plan import prepare

BOOTSTRAP=dict(version='3.13.18',release='20261026',
    file='cpython-3.13.18+20261026-x86_64-pc-windows-msvc-install_only.tar.gz',
    sha256='ebe90cc1dce2dd2d7afa1f0aa9b6c269c7c0174aeabdc6a801381602b7283424',size=48077770,
    url='https://github.com/astral-sh/python-build-standalone/releases/download/20261026/cpython-3.13.18%2B20261026-x86_64-pc-windows-msvc-install_only.tar.gz')

def profile_for(root,requested):
    p=local(root,'data/rc1/trial/run.json')
    if p.is_file():
        profile=load(p).get('backend')
        need(profile in ('cpu','cuda') and requested in (None,profile),'Prepared trial profile mismatch')
        return profile
    need(requested in PROFILES,'Explicit profile required')
    return requested

def verify_archive(root):
    p=local(root,'cache/downloads/'+BOOTSTRAP['sha256']+'/'+BOOTSTRAP['file'])
    need(p.is_file() and p.stat().st_size==BOOTSTRAP['size'] and digest(p)==BOOTSTRAP['sha256'],'Bootstrap integrity mismatch')
    return p

def runtime_zip(base,out):
    base=Path(base).resolve(strict=True)
    for name in ('python.exe','python313.dll','Lib/venv','Lib/ensurepip'):
        need(local(base,name).exists(),'Incomplete standalone runtime: '+name)
    files=[];total=0;seen=set()
    for p in sorted(base.rglob('*')):
        name=p.relative_to(base).as_posix();local(base,name);s=p.lstat()
        need(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&1024,'Runtime link refused')
        if p.is_dir():continue
        need(stat.S_ISREG(s.st_mode) and s.st_nlink==1,'Nonregular runtime file')
        need(name.casefold() not in seen,'Runtime collision');seen.add(name.casefold())
        total+=s.st_size;need(len(seen)<=100000 and total<=1024**3,'Runtime quota')
        if '__pycache__' not in p.parts:files.append((p,name))
    with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p,name in files:z.write(p,name)
    return digest(out)

def fetch_wheels(root,profile,folder):
    env=environment(root);env.pop('PIP_NO_INDEX',None)
    base=[sys.executable,'-I','-B','-m','pip','--isolated','--no-cache-dir','--disable-pip-version-check','--no-input','download','--only-binary=:all:','--dest',str(folder)]
    def get(args):subprocess.run(base+args,cwd=root,env=env,check=True,timeout=3600)
    req=['Pillow==13.0.0','psutil==7.2.2','pystray==0.19.5','setuptools==84.1.0']
    if profile!='review':
        backend='cpu' if profile=='cpu' else 'cu130'
        get(['--no-deps','--index-url','https://download.pytorch.org/whl/'+backend,'torch==2.13.0+'+backend])
        torch=list(folder.glob('torch-*.whl'));need(len(torch)==1,'Torch wheel cardinality')
        req+=['numpy==2.3.5','PyMuPDF==1.26.7',str(torch[0])]
    get(['--index-url','https://pypi.org/simple',*req])

def install(root,requested):
    root=Path(root).resolve(strict=True);source_payload(root);profile=profile_for(root,requested)
    need(os.name=='nt' and sys.version_info[:3]==(3,13,18) and sys.maxsize>2**32,'Pinned Windows x64 CPython required')
    base=local(root,'bootstrap')
    need(Path(sys.executable).resolve()==local(base,'python.exe').resolve() and Path(sys.base_prefix).resolve()==base,'Nonlocal bootstrap')
    verify_archive(root);env=environment(root)
    for key in ('TEMP','TMP','TMPDIR','HOME','USERPROFILE','APPDATA','LOCALAPPDATA'):os.environ[key]=env[key]
    info=probe(root);need(info['arch'].lower() in ('amd64','x86_64'),'Windows x64 required')
    need(profile!='cuda' or info['nvidia']!='NOT_MEASURED','NVIDIA driver not detected; no CPU fallback')
    need(info['free_bytes']>=(20 if profile=='cuda' else 5)*1024**3,'Insufficient disk space')
    rel='config/install-'+profile+'.json';lock=local(root,rel);receipt=local(root,'config/bootstrap-origin.json')
    with exclusive(root):
        if local(root,'config/portable.json').exists():
            need(active(root)['profile']==profile,'Existing profile differs')
            return dict(status='ALREADY_INSTALLED',profile=profile)
        need(not lock.exists() and not receipt.exists(),'Existing plan/receipt; preserve it and inspect state')
        subprocess.run([sys.executable,'-I','-B','-c',"import tkinter,venv,ensurepip,struct; assert struct.calcsize('P')==8; print(tkinter.Tcl().eval('info patchlevel'))"],cwd=root,env=env,check=True,timeout=60)
        created=False
        try:
            with tempfile.TemporaryDirectory(dir=local(root,'temp'),prefix='.auto-install-') as d:
                stage=Path(d);rt=stage/'python-runtime.zip';wheels=stage/'wheels';wheels.mkdir()
                runtime_zip(base,rt)
                print('Resolving '+profile+' wheels from PyPI / PyTorch...',flush=True)
                fetch_wheels(root,profile,wheels)
                plan=prepare(root,profile,rt,wheels);created=True
                save(receipt,dict(schema=1,bootstrap=BOOTSTRAP,profile=profile,plan=rel,plan_sha256=plan['sha256'],wheel_origins=['https://pypi.org/simple','https://download.pytorch.org/whl/'],release_approved=False,scientific_approval=False))
                setup(root,profile,rel,plan['sha256'],False)
        except BaseException:
            if created:lock.unlink(missing_ok=True);receipt.unlink(missing_ok=True)
            raise
    return dict(status='INSTALLED',profile=profile,plan_sha256=plan['sha256'],bootstrap_sha256=BOOTSTRAP['sha256'],release_approved=False)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--profile',choices=PROFILES,required=True)
    a=p.parse_args();print(json.dumps(install(a.root,a.profile),indent=2))
if __name__=='__main__':main()

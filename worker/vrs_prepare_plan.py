"""Build an explicitly reviewable offline lock from operator-provided Windows assets."""
import argparse
import re
import shutil
import zipfile
from email.parser import BytesParser
from pathlib import Path
from vrs_portable import local, need, digest, save, plan, PROFILES, LIMIT


def stage(root, src):
    need(src.is_file() and not src.is_symlink() and 0<src.stat().st_size<=LIMIT,'Invalid asset')
    sha=digest(src); dest=local(root,'cache/downloads/'+sha+'/'+src.name)
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():
        import tempfile, os
        fd,tmp=tempfile.mkstemp(dir=dest.parent)
        try:
            with os.fdopen(fd,'wb') as f,src.open('rb') as inp:shutil.copyfileobj(inp,f,1024**2)
            need(digest(tmp)==sha,'Source changed'); os.replace(tmp,dest)
        finally:Path(tmp).unlink(missing_ok=True)
    need(digest(dest)==sha,'Cache corruption')
    return dict(file=src.name,sha256=sha,size=dest.stat().st_size,url='')


def wheel_identity(path):
    need(re.fullmatch(r'[A-Za-z0-9_.+!-]+\.whl',path.name),'Invalid wheel name')
    parts=path.stem.split('-'); need(len(parts) in (5,6),'Invalid wheel filename')
    need(parts[-1] in ('win_amd64','any'),'Not Windows x64 or universal wheel')
    with zipfile.ZipFile(path) as z:
        members=[x for x in z.infolist() if re.fullmatch(r'[^/]+\.dist-info/METADATA',x.filename)]
        need(len(members)==1 and members[0].file_size<=1024**2,'Invalid metadata')
        m=BytesParser().parsebytes(z.read(members[0])); n=m['Name']; v=m['Version']
        need(len(m.get_all('Name',[]))==len(m.get_all('Version',[]))==1 and isinstance(n,str) and isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9_.-]+',n) and re.fullmatch(r'[A-Za-z0-9.+!-]+',v),'Invalid wheel identity')
    canon=lambda s:re.sub(r'[-_.]+','-',s).lower()
    need(canon(n)==canon(parts[0]) and v==parts[1],'Wheel metadata/filename mismatch')
    return canon(n),v


def prepare(root,profile,runtime,wheel_dir):
    root=Path(root).resolve(strict=True); need(profile in PROFILES,'Invalid profile')
    runtime=Path(runtime); wheel_dir=Path(wheel_dir)
    need(runtime.suffix=='.zip' and re.fullmatch(r'[A-Za-z0-9_.+-]+',runtime.name),'Invalid runtime filename')
    with zipfile.ZipFile(runtime) as z:need('python.exe' in z.namelist(),'Full runtime archive required')
    paths=sorted(wheel_dir.glob('*.whl')); need(0<len(paths)<=200,'Wheel count')
    req=[]; wheels=[]; seen=set()
    for p in paths:
        n,v=wheel_identity(p); need(n not in seen,'Duplicate distribution'); seen.add(n)
        item=stage(root,p); wheels.append(item); req.append(f'{n}=={v} --hash=sha256:{item["sha256"]}')
    v=dict(schema=1,profile=profile,runtime=stage(root,runtime),wheels=wheels,requirements=req,runtime_python='python.exe')
    path=local(root,'config/install-'+profile+'.json'); need(not path.exists(),'Plan exists; preserve or remove explicitly'); save(path,v)
    try:h=digest(path); plan(root,profile,'config/'+path.name,h)
    except BaseException:path.unlink(missing_ok=True);raise
    return dict(plan='config/'+path.name,sha256=h,profile=profile,wheels=len(wheels),approval='NOT_APPROVED')


if __name__=='__main__':
    import json
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('profile',choices=PROFILES);p.add_argument('runtime',type=Path);p.add_argument('wheel_dir',type=Path);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();print(json.dumps(prepare(a.root,a.profile,a.runtime,a.wheel_dir),indent=2))

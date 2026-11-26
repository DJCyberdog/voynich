"""Root-local VRS portable launcher. No implicit downloads or global installs."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

VERSION = '0.13.0'
PROFILES = ('review', 'cpu', 'cuda')
LIMIT = 16 * 1024**3
ORIGINS = ('www.python.org', 'github.com', 'release-assets.githubusercontent.com', 'files.pythonhosted.org', 'download.pytorch.org', 'download-r2.pytorch.org')
HEX = re.compile(r'[a-f0-9]{64}')
SLOTS = re.compile(r'VRS_[A-Z0-9_]{1,80}')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def local(root, rel):
    root = Path(root).resolve(strict=True)
    need(isinstance(rel, str) and rel and '\\' not in rel and ':' not in rel, 'Invalid relative path')
    parts = rel.split('/')
    need(all(p not in ('', '.', '..') and p == p.rstrip(' .') and not re.search(r'[<>"|?*\x00-\x1f]', p) and not re.fullmatch(r'(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', p) for p in parts), 'Unsafe path')
    p = root
    for name in parts:
        p = p / name
        try:
            s = p.lstat()
            need(not stat.S_ISLNK(s.st_mode) and not getattr(s, 'st_file_attributes', 0) & 1024, 'Link/reparse point refused')
        except FileNotFoundError:
            pass
    return p


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024**2), b''):
            h.update(b)
    return h.hexdigest()


def load(path, limit=2*1024**2):
    def pairs(items):
        d = dict(items); need(len(d)==len(items), 'Duplicate JSON key'); return d
    with Path(path).open('rb') as f:
        b = f.read(limit+1)
    need(len(b)<=limit, 'JSON quota')
    return json.loads(b, object_pairs_hook=pairs, parse_constant=lambda _: need(False, 'Invalid number'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.vrs-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=True, sort_keys=True); f.flush(); os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def environment(root):
    env = os.environ.copy()
    for k in list(env):
        if k.startswith(('PYTHON', 'PIP_', 'HF_', 'TORCH_', 'XDG_', 'VIRTUAL_ENV', 'CONDA_')) or k in ('TCL_LIBRARY','TK_LIBRARY') or SLOTS.fullmatch(k):
            env.pop(k)
    for k, rel in {'TEMP':'temp','TMP':'temp','TMPDIR':'temp','PIP_CACHE_DIR':'cache/pip','HF_HOME':'cache/hf','TORCH_HOME':'cache/torch','XDG_CACHE_HOME':'cache/xdg','XDG_CONFIG_HOME':'config/xdg','XDG_DATA_HOME':'data/xdg','XDG_STATE_HOME':'workspace/xdg','CUDA_CACHE_PATH':'cache/cuda','MPLCONFIGDIR':'cache/matplotlib','TRITON_CACHE_DIR':'cache/triton','TORCHINDUCTOR_CACHE_DIR':'cache/inductor','NUMBA_CACHE_DIR':'cache/numba','UV_CACHE_DIR':'cache/uv','PYTHONPYCACHEPREFIX':'cache/pyc','HOME':'data/home','USERPROFILE':'data/home','APPDATA':'config/appdata','LOCALAPPDATA':'data/localappdata'}.items():
        p=local(root,rel); p.mkdir(parents=True,exist_ok=True); env[k]=str(p)
    env['VRS_PORTABLE_LOG_ROOT']=str(root)
    env.update(PYTHONNOUSERSITE='1', PIP_CONFIG_FILE=os.devnull, PIP_DISABLE_PIP_VERSION_CHECK='1', PIP_NO_INPUT='1', PIP_NO_INDEX='1')
    return env


def probe(root):
    import platform
    ram=None
    if os.name=='nt':
        import ctypes
        class Mem(ctypes.Structure):
            _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(k,ctypes.c_ulonglong) for k in ('total','avail','page','pageavail','virtual','virtavail','extended')]
        m=Mem(); m.length=ctypes.sizeof(m)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)): ram=m.total
    elif hasattr(os,'sysconf'):
        ram=os.sysconf('SC_PHYS_PAGES')*os.sysconf('SC_PAGE_SIZE')
    gpu='NOT_MEASURED'
    try:
        p=subprocess.run(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader'],capture_output=True,timeout=5,text=True,check=True)
        gpu=p.stdout.strip()[:1024]
    except (OSError,subprocess.SubprocessError): pass
    return dict(os=platform.system(),arch=platform.machine(),threads=os.cpu_count(),ram_bytes=ram,free_bytes=shutil.disk_usage(root).free,nvidia=gpu,automatic='review',native_qualification='PENDING')


def check_url(url):
    from urllib.parse import urlsplit
    u=urlsplit(url); need(u.scheme=='https' and u.hostname in ORIGINS and u.port in (None,443) and not u.username and not u.password and not u.fragment, 'Download origin refused')
    return url


class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        check_url(newurl); return super().redirect_request(req,fp,code,msg,headers,newurl)


def acquire(root, item, online=False):
    need(set(item)=={'file','sha256','size','url'} and HEX.fullmatch(item['sha256']) and type(item['size']) is int and 0<item['size']<=LIMIT, 'Invalid asset')
    name=item['file']; need(re.fullmatch(r'[A-Za-z0-9_.+\-]+',name) and name not in ('.','..'), 'Invalid asset name')
    p=local(root,'cache/downloads/'+item['sha256']+'/'+name); p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():
        need(p.stat().st_size==item['size'] and digest(p)==item['sha256'], 'Cached asset mismatch'); return p
    need(online, 'Verified offline asset missing')
    check_url(item['url']); part=local(root,'cache/downloads/'+item['sha256']+'/'+name+'.part')
    start=part.stat().st_size if part.exists() else 0; need(start<=item['size'], 'Partial download exceeds quota')
    if start<item['size']:
        req=urllib.request.Request(item['url'],headers={'Range':f'bytes={start}-'} if start else {})
        with urllib.request.build_opener(Redirect()).open(req,timeout=30) as r:
            if start and r.status!=206: start=0
            if start: need(r.headers.get('Content-Range')==f'bytes {start}-{item["size"]-1}/{item["size"]}', 'Unexpected range')
            with part.open('ab' if start else 'wb') as f:
                n=start
                while True:
                    b=r.read(1024**2)
                    if not b: break
                    n+=len(b); need(n<=item['size'], 'Download exceeds quota'); f.write(b); print(f'{name}: {n}/{item["size"]}',flush=True)
    need(part.stat().st_size==item['size'] and digest(part)==item['sha256'], 'Download integrity failure'); os.replace(part,p); return p


def extract(archive, target):
    # Preflight all names before any extraction; reject case aliases and nonregular entries.
    with zipfile.ZipFile(archive) as z:
        seen=set(); total=0; need(len(z.infolist())<=100000,'Archive member quota')
        for i in z.infolist():
            need(i.orig_filename==i.filename,'Normalized archive member refused')
            name=i.filename.rstrip('/'); key=name.casefold(); local(target,name)
            mode=(i.external_attr>>16)&0xffff
            need(key not in seen and stat.S_IFMT(mode) in (0,stat.S_IFREG,stat.S_IFDIR) and not i.flag_bits&1 and not i.external_attr&1024, 'Unsafe archive member'); seen.add(key)
            total+=i.file_size; need(total<=LIMIT and i.file_size<=4*1024**3 and i.file_size<=max(1024**2,i.compress_size*500), 'Archive expansion quota')
        for i in z.infolist():
            p=local(target,i.filename.rstrip('/'))
            if i.is_dir(): p.mkdir(parents=True,exist_ok=True); continue
            p.parent.mkdir(parents=True,exist_ok=True)
            with z.open(i) as src,p.open('xb') as dst: shutil.copyfileobj(src,dst,1024**2)


def plan(root, profile, rel, approved):
    p=local(root,rel); need(HEX.fullmatch(approved) and digest(p)==approved,'Plan approval mismatch'); v=load(p)
    need(set(v)=={'schema','profile','runtime','wheels','requirements','runtime_python'} and v['schema']==1 and v['profile']==profile and profile in PROFILES,'Invalid install plan')
    need(v['runtime_python']=='python.exe' and v['runtime']['file'].endswith('.zip'),'Full Windows Python runtime ZIP required')
    wheels=v['wheels']; req=v['requirements']; need(isinstance(wheels,list) and 0<len(wheels)<=200 and isinstance(req,list) and len(req)==len(wheels),'Lock cardinality')
    names=set(); hashes=set(); versions={}
    need(len({x['file'].casefold() for x in wheels})==len(wheels),'Wheel filename collision')
    for line in req:
        m=re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9.+!-]+) --hash=sha256:([a-f0-9]{64})',line); need(m is not None,'Exact locked requirement required')
        name=re.sub(r'[-_.]+','-',m[1]).lower(); need(name not in names,'Duplicate package'); names.add(name); hashes.add(m[3]); versions[name]=m[2]
    need(len(hashes)==len(wheels) and {x['sha256'] for x in wheels}==hashes and all(x['file'].endswith('.whl') for x in wheels),'Wheel lock mismatch')
    need({'pillow','psutil'}<=names and (profile=='review' and not names&{'torch','numpy','pymupdf'} or profile!='review' and {'torch','numpy','pymupdf'}<=names),'Profile mismatch')
    pins={'pillow':'12.3.0','psutil':'7.2.2'}
    if profile!='review':pins.update(numpy='2.3.5',pymupdf='1.26.7',torch='2.10.0+'+('cpu' if profile=='cpu' else 'cu128'))
    need(all(versions.get(k)==v for k,v in pins.items()),'Core package pin mismatch')
    return v


def exe(root,profile): return local(root,f'.venv/{profile}/Scripts/python.exe')


def active(root):
    p=local(root,'config/portable.json'); need(p.exists(),'Run Setup first'); s=load(p); need(s['profile'] in PROFILES and s['root']==str(root) and exe(root,s['profile']).is_file(),'Environment moved or missing; run Repair'); return s


def invoke(root,args,slots=(),**kw):
    env=environment(root)
    if slots:
        from vrs_portable_secrets import read
        for slot in slots:env[slot]=read(root,slot)
    return subprocess.run([str(x) for x in args],cwd=root,env=env,check=True,**kw)


@contextmanager
def exclusive(root,allow_source_recovery=False):
    p=local(root,'workspace/portable.lock'); p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a+b') as f:
        if f.tell()==0:f.write(b'0');f.flush()
        f.seek(0)
        if os.name=='nt':
            import msvcrt
            try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            except OSError:raise ValueError('Portable launcher busy') from None
            try:
                need(allow_source_recovery or not local(root,"workspace/source-update/journal.json").exists(),"Interrupted source update; recover first");yield
            finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            try:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError:raise ValueError('Portable launcher busy') from None
            try:
                need(allow_source_recovery or not local(root,"workspace/source-update/journal.json").exists(),"Interrupted source update; recover first");yield
            finally:fcntl.flock(f.fileno(),fcntl.LOCK_UN)



def setup(root,profile,rel,approved,online):
    need(os.name=='nt','Windows installation requires native Windows'); info=probe(root); print(json.dumps(info,indent=2)); profile=info['automatic'] if profile=='auto' else profile
    v=plan(root,profile,rel,approved); need(info['arch'].lower() in ('amd64','x86_64'),'Windows x64 required'); need(profile!='cuda' or info['nvidia']!='NOT_MEASURED','CUDA hardware not detected')
    need(info['free_bytes']>=sum(x['size'] for x in [v['runtime'],*v['wheels']])*3+1024**3,'Insufficient free storage')
    install_plan(root,profile,v,rel,approved,online)


def install_plan(root,profile,v,rel,approved,online):
    previous=local(root,'config/portable.json'); need(not previous.exists() or load(previous)['profile']==profile,'Existing profile differs; explicit migration required')
    # Refuse maintenance with a live launcher/managed worker; stale OS process evidence is checked by existing runtime when available.
    need(not local(root,'workspace/vrs101/session.json').exists() or worker_stopped(root),'Stop managed worker first')
    runtime=local(root,f'runtime/{profile}'); ven=local(root,f'.venv/{profile}'); runtime.parent.mkdir(parents=True,exist_ok=True); ven.parent.mkdir(parents=True,exist_ok=True)
    from vrs_portable_logs import event
    event(root,'setup','DEBUG','SETUP_RUNTIME'); cache=acquire(root,v['runtime'],online); event(root,'setup','DEBUG','SETUP_WHEELS',count=len(v['wheels'])); wheels=[acquire(root,x,online) for x in v['wheels']]
    stage=Path(tempfile.mkdtemp(dir=local(root,'temp') if local(root,'temp').exists() else root,prefix='.install-')); backups=[]; replaced=[]
    try:
        payload=stage/'runtime'; payload.mkdir(); extract(cache,payload); need(local(payload,'python.exe').is_file(),'Runtime missing python.exe')
        wheelhouse=stage/'wheels'; wheelhouse.mkdir()
        for p in wheels: shutil.copyfile(p,wheelhouse/p.name)
        lock=stage/'requirements.lock'; lock.write_text('\n'.join(v['requirements'])+'\n',encoding='ascii')
        for p in (runtime,ven):
            backup=p.with_name(p.name+'.rollback'); need(not backup.exists(),'Unresolved prior installation backup')
            if p.exists(): p.rename(backup); backups.append((p,backup))
            replaced.append(p)
        payload.rename(runtime); py=runtime/'python.exe'; invoke(root,[py,'-s','-m','venv',ven]); vp=exe(root,profile)
        invoke(root,[vp,'-s','-m','pip','install','--no-index','--no-deps','--only-binary=:all:','--require-hashes','--find-links',wheelhouse,'-r',lock]); invoke(root,[vp,'-s','-m','pip','check'])
        test='import sys,struct,tkinter,PIL,psutil; assert sys.version_info[:2]==(3,13) and struct.calcsize("P")==8; t=tkinter.Tcl(); print(t.eval("info patchlevel"))'
        if profile!='review': test+='; import fitz,numpy,torch; assert '+('torch.cuda.is_available(); print(torch.zeros(1,device="cuda").item())' if profile=='cuda' else 'torch.version.cuda is None')
        event(root,'setup','DEBUG','SETUP_SMOKE'); invoke(root,[vp,'-s','-c',test]); save(previous,dict(schema=1,profile=profile,root=str(root),plan=rel,sha256=approved))
    except BaseException:
        for p in reversed(replaced):
            if p.exists(): shutil.rmtree(p)
        for p,b in reversed(backups): b.rename(p)
        raise
    finally: shutil.rmtree(stage,ignore_errors=True)
    for _,b in backups: shutil.rmtree(b)


def worker_stopped(root):
    # Never guess from an old PID alone; on relocation a stale runtime cannot be used to prove stop.
    s=load(local(root,'workspace/vrs101/session.json')); return s.get('state')=='STOPPED'


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('action',choices=('probe','setup','repair','update','start','stop','diagnostics','logs','repository','collaboration','learning','modules','secret-set','secret-delete')); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent); p.add_argument('--profile',choices=('auto',*PROFILES),default='auto'); p.add_argument('--plan'); p.add_argument('--approve'); p.add_argument('--online',action='store_true'); p.add_argument('--source',type=Path); p.add_argument('--recover-source',action='store_true'); p.add_argument('--slot',action='append',default=[]); a,extra=p.parse_known_args(); need(not extra or a.action in ('repository','collaboration','learning','modules') and extra[0]=='--','Unexpected arguments'); extra=extra[1:]; root=a.root.resolve(strict=True)
    environment(root)
    from vrs_portable_logs import event, export
    event(root,'setup' if a.action in ('setup','repair','update') else 'application','INFO','COMMAND_START',action=a.action)
    try:
        from vrs_source_update import pending,update as source_update,recover as source_recover
        need(not (a.source or a.recover_source) or a.action=='update','Source maintenance requires update action')
        need(not pending(root) or a.action in ('probe','diagnostics','logs','stop') or a.action=='update' and a.recover_source,'Interrupted source update; recover first')
        if a.action=='update' and (a.source or a.recover_source):
            need(not a.plan and a.profile=='auto' and not a.online and not a.slot and not (a.source and a.recover_source),'Conflicting source update arguments')
            if a.recover_source:
                need(not a.approve,'Recovery uses recorded hashes'); print(json.dumps(source_recover(root)))
            else:
                need(a.approve,'Explicit source ZIP SHA256 approval required'); print(json.dumps(source_update(root,a.source,a.approve)))
        elif a.action=='probe':
            info=probe(root); event(root,'gpu','INFO','HARDWARE_PROBE',count=int(info['nvidia']!='NOT_MEASURED')); print(json.dumps(info,indent=2))
        elif a.action in ('setup','repair','update'):
            if a.action=='repair' and not a.plan:
                s=load(local(root,'config/portable.json')); a.profile,a.plan,a.approve=s['profile'],s['plan'],s['sha256']
            need(a.plan and a.approve,'Explicit approved plan required')
            with exclusive(root):setup(root,a.profile,a.plan,a.approve,a.online)
        elif a.action=='diagnostics': print(export(root))
        elif a.action=='logs':
            from vrs_portable_logs import records
            for row in records(root): print(json.dumps(row))
        elif a.action in ('secret-set','secret-delete'):
            from vrs_portable_secrets import prompt,path
            need(len(a.slot)==1,'Exactly one credential slot required')
            if a.action=='secret-set':prompt(root,a.slot[0])
            else:path(root,a.slot[0]).unlink(missing_ok=True)
            event(root,'security','INFO','CREDENTIAL_CHANGED',action=a.action)
        elif a.action in ('repository','collaboration','learning','modules'):
            s=active(root); vp=exe(root,s['profile']); need(s['profile']!='review' or a.action=='modules','Compute profile required')
            names={'repository':'vrs_repository.py','collaboration':'vrs_collaboration.py','learning':'vrs_learning.py','modules':'vrs_modules.py'}
            module={'repository':'github','collaboration':'security','learning':'learning','modules':'modules'}[a.action]
            need(not a.slot or a.action in ('repository','collaboration') and all(x.startswith('VRS_GITHUB_TOKEN_' if a.action=='repository' else 'VRS_REVIEW_KEY_') for x in a.slot),'Credential scope refused')
            event(root,module,'INFO','MODULE_START',action=a.action)
            with exclusive(root):invoke(root,[vp,'-s',local(root,names[a.action]),root,*extra],slots=a.slot)
            event(root,module,'INFO','MODULE_OK',action=a.action)
        else:
            s=active(root); vp=exe(root,s['profile'])
            if a.action=='start':
                with exclusive(root):invoke(root,[vp,'-s',local(root,'vrs_portable_ui.py'),root,a.action])
            else:invoke(root,[vp,'-s',local(root,'vrs_portable_ui.py'),root,a.action])
        event(root,'application','INFO','COMMAND_OK',action=a.action)
    except Exception as e:
        from vrs_portable_logs import crash
        module={'setup':'setup','repair':'setup','update':'setup','repository':'github','collaboration':'security','learning':'learning','modules':'modules','secret-set':'security','secret-delete':'security'}.get(a.action,'application')
        crash(root,module,e); print('VRS operation failed; see local logs.',file=sys.stderr); return 1
    return 0


if __name__=='__main__': sys.exit(main())

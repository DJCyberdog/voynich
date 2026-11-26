"""VRS-140: explicit private local snapshot and non-destructive restore of a stopped app."""
import argparse
from contextlib import ExitStack, contextmanager
import hashlib
import json
import os
import shutil
import stat
from pathlib import Path
from vrs_portable import local, need, digest, load, exclusive, worker_stopped, HEX
from vrs_coordinator import scheduler_lock
from vrs_rc_preflight import inspect

SCHEMA=1
MAX_FILES=250000
MAX_BYTES=64*1024**3
MAX_MANIFEST=64*1024**2
LOCKS={'workspace/portable.lock','workspace/vrs095/coordinator.lock','workspace/vrs101/manager.lock'}

def existing_directory(path):
    path=Path(path).absolute()
    for p in (path,*path.parents):
        s=p.lstat()
        need(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&1024,'Directory link refused')
    need(path.is_dir(),'Directory required')
    return path.resolve(strict=True)

def destination(path,source):
    path=Path(path).absolute()
    parent=existing_directory(path.parent)
    p=local(parent,path.name)
    need(not p.exists() and not p.is_relative_to(source) and not source.is_relative_to(p),'Destination must be new and separate')
    return p

def scan(root,ignore=()):
    """Canonical byte inventory; no links, aliasing, special files or hidden omissions."""
    files={};dirs=[];seen=set();total=0
    def check(rel):
        need(rel.casefold() not in seen,'Case-colliding snapshot paths')
        seen.add(rel.casefold());need(len(seen)<=MAX_FILES,'Snapshot entry limit')
        p=local(root,rel);s=p.lstat()
        need(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&1024,'Link refused')
        return p,s
    for parent,subdirs,names in os.walk(root,followlinks=False,onerror=lambda err: (_ for _ in ()).throw(err)):
        base=Path(parent)
        for n in sorted(subdirs):
            rel=(base/n).relative_to(root).as_posix()
            need(rel.casefold()!='.git','Use a disposable app, not a Git checkout')
            p,s=check(rel);need(stat.S_ISDIR(s.st_mode),'Special directory refused');dirs.append(rel)
        for n in sorted(names):
            rel=(base/n).relative_to(root).as_posix()
            p,s=check(rel);need(stat.S_ISREG(s.st_mode) and s.st_nlink==1,'Special or hard-linked file refused')
            if rel in ignore:continue
            need(rel.casefold()!='.git','Use a disposable app, not a Git checkout')
            need(s.st_size<=MAX_BYTES-total,'Snapshot byte limit')
            total+=s.st_size;h=digest(p);end=p.stat()
            need((s.st_size,s.st_mtime_ns,s.st_ino)==(end.st_size,end.st_mtime_ns,end.st_ino),'File changed while hashing')
            files[rel]={'bytes':s.st_size,'sha256':h}
    return {'dirs':sorted(dirs),'files':files,'bytes':total}

def preflight(root):
    db=local(root,'workspace/vrs095/ledger.sqlite')
    for suffix in ('-wal','-shm','-journal'):
        need(not local(root,'workspace/vrs095/ledger.sqlite'+suffix).exists(),'SQLite sidecar requires recovery')
    if not db.exists():return None
    report=inspect(root);need(report['status']=='PREFLIGHT_PASS','Active ledger ownership or invalid ledger')
    return report['logical_sha256']

@contextmanager
def stopped(root):
    # Launcher and managed worker/coordinator locks are the existing shared locks.
    # Direct unmanaged writers still require the operator to close them first.
    with ExitStack() as stack:
        stack.enter_context(exclusive(root))
        session=local(root,'workspace/vrs101/session.json')
        need(not session.exists() or worker_stopped(root),'Stop managed worker first')
        for name in ('workspace/vrs101/manager.lock','workspace/vrs095/coordinator.lock'):
            p=local(root,name)
            if p.parent.exists():stack.enter_context(scheduler_lock(p))
        need(not session.exists() or worker_stopped(root),'Stop managed worker first')
        yield

def copy_tree(source,target,inventory):
    need(shutil.disk_usage(target.parent).free>=inventory['bytes'],'Insufficient destination disk space')
    target.mkdir()
    for rel in sorted(inventory['dirs'],key=lambda n:(n.count('/'),n)):
        local(target,rel).mkdir()
    for rel,item in sorted(inventory['files'].items()):
        src=local(source,rel);dst=local(target,rel)
        need(src.is_file() and src.stat().st_nlink==1,'Source changed')
        h=hashlib.sha256();count=0
        with src.open('rb') as i,dst.open('xb') as o:
            for chunk in iter(lambda:i.read(1024**2),b''):
                count+=len(chunk);need(count<=item['bytes'],'Source grew while copying')
                h.update(chunk);o.write(chunk)
            o.flush();os.fsync(o.fileno())
        need(count==item['bytes'] and h.hexdigest()==item['sha256'],'Source bytes changed while copying')
    need(scan(target)==inventory,'Destination inventory mismatch')

def private_directory(path):
    # Restrictive POSIX creation; on Windows inherited ACLs remain the owner's responsibility.
    path.mkdir(mode=0o700)

def write_new(path,data):
    with path.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())

def encode(value):
    data=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
    need(len(data)<=MAX_MANIFEST,'Snapshot manifest limit');return data

def snapshot(root,out):
    root=existing_directory(root);out=destination(out,root)
    with stopped(root):
        logical=preflight(root);inventory=scan(root,LOCKS)
        private_directory(out)
        try:
            copy_tree(root,out/'payload',inventory)
            need(scan(root,LOCKS)==inventory and preflight(root)==logical,'Source changed during snapshot')
            manifest=dict(schema=SCHEMA,scope='PRIVATE_LOCAL_FULL_APP_BYTES',inventory=inventory,ledger_logical_sha256=logical,excluded_transient_locks=sorted(LOCKS))
            raw=encode(manifest);write_new(out/'snapshot.json',raw)
        except BaseException:
            # Never remove an existing directory; only our newly reserved output.
            shutil.rmtree(out);raise
    return dict(status='SNAPSHOT_PASS',manifest_sha256=hashlib.sha256(raw).hexdigest(),files=len(inventory['files']),bytes=inventory['bytes'],private=True)

def verify(bundle,approved):
    bundle=existing_directory(bundle)
    need(isinstance(approved,str) and HEX.fullmatch(approved),'Exact snapshot manifest approval required')
    p=local(bundle,'snapshot.json');need(p.is_file() and p.stat().st_size<=MAX_MANIFEST,'Snapshot manifest missing or too large')
    need(digest(p)==approved,'Snapshot manifest approval mismatch')
    manifest=load(p,MAX_MANIFEST);need(digest(p)==approved and hashlib.sha256(encode(manifest)).hexdigest()==approved,'Snapshot manifest changed or noncanonical')
    need(set(manifest)=={'schema','scope','inventory','ledger_logical_sha256','excluded_transient_locks'} and type(manifest['schema']) is int and manifest['schema']==SCHEMA and manifest['scope']=='PRIVATE_LOCAL_FULL_APP_BYTES' and manifest['excluded_transient_locks']==sorted(LOCKS),'Unsupported snapshot manifest')
    need({p.name for p in bundle.iterdir()}=={'snapshot.json','payload'},'Unexpected snapshot members')
    payload=local(bundle,'payload');need(payload.is_dir(),'Missing snapshot payload')
    need(scan(payload)==manifest['inventory'],'Snapshot payload mismatch')
    need(preflight(payload)==manifest['ledger_logical_sha256'],'Snapshot ledger mismatch')
    return manifest

def restore(bundle,out,approved):
    bundle=existing_directory(bundle);out=destination(out,bundle);manifest=verify(bundle,approved)
    private_directory(out)
    try:
        # A crash leaves only .partial; never present it as an accepted application.
        partial=out/'.partial'
        copy_tree(bundle/'payload',partial,manifest['inventory'])
        need(preflight(partial)==manifest['ledger_logical_sha256'],'Restored ledger mismatch')
        need(verify(bundle,approved)==manifest,'Snapshot changed during restore')
        partial.rename(out/'app')
        write_new(out/'restore.json',encode(dict(schema=1,snapshot_sha256=approved,status='RESTORE_PASS',execution_authorized=False)))
    except BaseException:
        shutil.rmtree(out);raise
    return dict(status='RESTORE_PASS',files=len(manifest['inventory']['files']),bytes=manifest['inventory']['bytes'],execution_authorized=False,repair_required=True,private=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='action',required=True)
    for action in ('snapshot','restore','verify'):
        q=sub.add_parser(action);q.add_argument('source',type=Path);q.add_argument('--private-local',action='store_true',required=True)
        if action!='verify':q.add_argument('destination',type=Path)
        if action!='snapshot':q.add_argument('--approve',required=True)
    a=p.parse_args()
    try:
        if a.action=='snapshot':value=snapshot(a.source,a.destination)
        elif a.action=='restore':value=restore(a.source,a.destination,a.approve)
        else:
            m=verify(a.source,a.approve);value=dict(status='VERIFY_PASS',files=len(m['inventory']['files']),bytes=m['inventory']['bytes'])
    except (ValueError,OSError,RuntimeError,TypeError,KeyError) as exc:
        print(json.dumps(dict(status='BLOCKED',error_type=type(exc).__name__)));return 1
    print(json.dumps(value,sort_keys=True,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())

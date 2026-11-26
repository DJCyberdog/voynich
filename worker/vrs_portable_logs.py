"""Bounded technical logs. Never persist arbitrary messages, argv or exception text."""
import datetime as dt
import json
import os
import re
import time
import threading
import traceback
import uuid
import zipfile
from pathlib import Path
from vrs_portable import local, need, load, save

MODULES=('application','debug','worker','gpu','learning','modules','github','setup','security')
LEVELS=('TRACE','DEBUG','INFO','WARNING','ERROR','CRITICAL')
SESSION=uuid.uuid4().hex[:12]
CAP=2*1024**2
NAME=re.compile(r'('+'|'.join(MODULES)+r')-[0-9a-f]{12}(?:\.[1-3])?\.jsonl')
CODES=('COMMAND_START','COMMAND_OK','CRASH','CREDENTIAL_CHANGED','MODULE_START','MODULE_OK','GUI_OPEN','GUI_CLOSE','STOP_REQUESTED','WORKER_START','WORKER_STOP','WORKER_FAILED','HARDWARE_PROBE','JOB_STATE','SETUP_RUNTIME','SETUP_WHEELS','SETUP_SMOKE')
LOCK=threading.RLock()
ACTIONS=('probe','setup','repair','update','start','stop','diagnostics','logs','repository','collaboration','learning','modules','secret-set','secret-delete')


def settings(root):
    p=local(root,'config/logging.json')
    v=load(p) if p.exists() else {'schema':1,'level':'INFO','days':14}
    need(set(v)=={'schema','level','days'} and v['schema']==1 and v['level'] in LEVELS and type(v['days']) is int and 1<=v['days']<=90,'Invalid logging settings'); return v


def valid(row):
    if not isinstance(row,dict) or set(row)-{'utc','module','level','event','action','run','state','count','exception','frames','stage'}: return False
    if not (isinstance(row.get('utc'),str) and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?\+00:00',row['utc']) and row.get('module') in MODULES and row.get('level') in LEVELS and row.get('event') in CODES): return False
    if 'action' in row and row['action'] not in ACTIONS:return False
    if 'run' in row and not re.fullmatch(r'[a-f0-9]{64}',str(row['run'])):return False
    if 'state' in row and row['state'] not in ('RUNNING','STOPPED','FAILED','BLOCKED','READY','COMPLETED','PAUSED','CANCELLED','STOP_REQUESTED','NOT_MANAGED'):return False
    if 'stage' in row and row['stage'] not in ('script_regions','glyph_segmentation','glyph_classification','exception_review','transcription_alignment'):return False
    if 'count' in row and not(type(row['count']) is int and 0<=row['count']<=10**9):return False
    if 'exception' in row and row['exception'] not in ('ValueError','OSError','RuntimeError','CalledProcessError','TimeoutExpired','KeyError','TypeError','PermissionError','FileNotFoundError','OtherError'):return False
    if 'frames' in row:
        if not isinstance(row['frames'],list) or len(row['frames'])>20:return False
        for f in row['frames']:
            if not isinstance(f,list) or len(f)!=2 or not re.fullmatch(r'(?:vrs_[a-z0-9_]+\.py|external)',str(f[0])) or type(f[1]) is not int or not 0<f[1]<10**7:return False
    return True


def event(root,module,level,code,**fields):
    with LOCK:return _event(root,module,level,code,**fields)

def _event(root,module,level,code,**fields):
    cfg=settings(root)
    row=dict(utc=dt.datetime.now(dt.timezone.utc).isoformat(),module=module,level=level,event=code,**fields)
    need(valid(row),'Unsafe log record')
    if LEVELS.index(level)<LEVELS.index(cfg['level']):return
    home=local(root,'logs'); home.mkdir(exist_ok=True); p=local(root,f'logs/{module}-{SESSION}.jsonl')
    data=(json.dumps(row,ensure_ascii=True,sort_keys=True)+'\n').encode('ascii')
    if p.exists() and p.stat().st_size+len(data)>CAP:
        for i in (3,2,1):
            src=p if i==1 else local(root,f'logs/{module}-{SESSION}.{i-1}.jsonl')
            dst=local(root,f'logs/{module}-{SESSION}.{i}.jsonl')
            if src.exists():os.replace(src,dst)
    with p.open('ab') as f:f.write(data)
    # Per-process rotation; old inactive log sessions expire. Scientific evidence untouched.
    cutoff=time.time()-cfg['days']*86400
    for q in home.iterdir():
        if NAME.fullmatch(q.name) and SESSION not in q.name:
            try:
                safe=local(root,'logs/'+q.name)
                if safe.is_file() and safe.stat().st_mtime<cutoff:safe.unlink(missing_ok=True)
            except (OSError,ValueError):pass


def crash(root,module,error):
    frames=[]
    for frame in traceback.extract_tb(error.__traceback__)[-20:]:
        name=Path(frame.filename).name
        if not name.startswith('vrs_') or not re.fullmatch(r'vrs_[a-z0-9_]+\.py',name) or Path(frame.filename).resolve().parent!=Path(__file__).resolve().parent:name='external'
        frames.append([name,frame.lineno])
    name=type(error).__name__
    if name not in ('ValueError','OSError','RuntimeError','CalledProcessError','TimeoutExpired','KeyError','TypeError','PermissionError','FileNotFoundError'):name='OtherError'
    row=dict(utc=dt.datetime.now(dt.timezone.utc).isoformat(),module=module,level='ERROR',event='CRASH',exception=name,frames=frames)
    event(root,module,'ERROR','CRASH',exception=name,frames=frames)
    home=local(root,'logs/crashes'); home.mkdir(parents=True,exist_ok=True)
    save(local(root,'logs/crashes/'+uuid.uuid4().hex+'.json'),row)
    files=sorted((p for p in home.iterdir() if re.fullmatch(r'[a-f0-9]{32}\.json',p.name) and not p.is_symlink()),key=lambda p:p.stat().st_mtime,reverse=True)
    for p in files[30:]:p.unlink(missing_ok=True)


def records(root,level='TRACE',module=None,search=''):
    need(level in LEVELS and (module is None or module in MODULES),'Invalid filter')
    home=local(root,'logs'); out=[]; budget=16*1024**2
    if not home.exists():return out
    paths=sorted((p for p in home.iterdir() if NAME.fullmatch(p.name) and not p.is_symlink() and p.is_file()),key=lambda p:p.stat().st_mtime,reverse=True)
    for p in paths[:100]:
        size=p.stat().st_size
        if size>CAP or size>budget:continue
        budget-=size
        with local(root,'logs/'+p.name).open('rb') as f:
            for line in f:
                if len(line)>4096:continue
                try:r=json.loads(line)
                except (ValueError,UnicodeError):continue
                try:
                    if valid(r) and LEVELS.index(r['level'])>=LEVELS.index(level) and (module is None or module==r['module']) and search.casefold() in json.dumps(r).casefold():out.append(r)
                except (TypeError,ValueError):continue
    return sorted(out,key=lambda r:r['utc'])[-2000:]


def export(root):
    home=local(root,'logs/diagnostics'); home.mkdir(parents=True,exist_ok=True)
    p=local(root,'logs/diagnostics/'+uuid.uuid4().hex+'.zip')
    with zipfile.ZipFile(p,'x',zipfile.ZIP_DEFLATED) as z:
        z.writestr('technical.jsonl',''.join(json.dumps(r,ensure_ascii=True)+'\n' for r in records(root)))
        z.writestr('README.txt','Redacted technical events only. No raw output, configuration, environment, source data, or scientific evidence. Bounded recent sample.\n')
    return p

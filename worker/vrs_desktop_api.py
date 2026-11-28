"""Lightweight desktop boundary. Read-only ledger; all authoritative writes via runtime CLI."""
import json
import os
import shutil
import sqlite3
import subprocess
from vrs_process import background_options
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

import vrs_contract as c
from vrs_core import require, sha
from vrs_ledger import Ledger
from vrs_exceptions import ExceptionQueue, load_page
from vrs_decisions import Decisions

VERSION = '0.10.0'


def safe(root, rel):
    p = Path(root).resolve(strict=True)
    require(isinstance(rel, str) and rel and not any(x in rel for x in ('\\', ':', '\x00')), 'Invalid local path')
    for part in rel.split('/'):
        require(part not in ('', '.', '..'), 'Invalid local path')
        p = p / part
        require(not p.is_symlink() and not getattr(p, 'is_junction', lambda: False)(), 'Workspace link forbidden')
    require(p.resolve().is_relative_to(root), 'Workspace escape')
    return p


def pinned(root, ref):
    safe(root, ref['path'])
    return c.artifact(root, ref)


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('.' + path.name + '-' + uuid.uuid4().hex)
    try:
        with tmp.open('x', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=True, allow_nan=False, indent=2)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


class ReadLedger(Ledger):
    def __init__(self, root):
        self.root = root; self.db = safe(root, 'workspace/vrs095/ledger.sqlite')
        require(self.db.is_file(), 'No local run ledger yet')

    @contextmanager
    def _tx(self):
        conn = sqlite3.connect(self.db.as_uri() + '?mode=ro', uri=True, timeout=3, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute('PRAGMA query_only=ON'); conn.execute('BEGIN')
            require(conn.execute('PRAGMA user_version').fetchone()[0] == 1, 'Unsupported ledger schema')
            yield conn
        finally: conn.close()


class ReadQueue(ExceptionQueue):
    def __init__(self, ledger): self.ledger = ledger; self.root = ledger.root


class ReadDecisions(Decisions):
    def __init__(self, ledger): self.ledger = ledger; self.root = ledger.root; self.queue = ReadQueue(ledger)


class Desktop:
    def __init__(self, root): self.root = Path(root).resolve(strict=True)

    def _validate_settings(self, v):
        c.fields(v, ('schema','theme','language','reviewer','interpreter','catalog','geometry','project'))
        require(type(v['schema']) is int and v['schema']==1 and v['theme'] in ('dark','light') and v['language'] in ('de','en') and all(type(v[k]) is str and len(v[k])<=512 for k in ('reviewer','interpreter','catalog','geometry','project')), 'Invalid UI settings')
        import re
        require(re.fullmatch(r'\d{3,5}x\d{3,5}',v['geometry']) is not None, 'Invalid window geometry')
        if v['catalog']: safe(self.root,v['catalog'])
        return v

    def settings(self):
        p = safe(self.root, 'config/vrs-desktop.json')
        if not p.exists(): return dict(schema=1, theme='dark', language='de', reviewer='', interpreter='', catalog='', geometry='1280x800', project='')
        return self._validate_settings(c.load(p))

    def save_settings(self, value):
        # No secrets or raw source bytes in settings.
        self._validate_settings(value); p = safe(self.root, 'config/vrs-desktop.json'); atomic_json(p, value)
        return self.settings()

    def runs(self):
        db = safe(self.root, 'workspace/vrs095/ledger.sqlite')
        if not db.exists(): return []
        ledger = ReadLedger(self.root)
        with ledger._tx() as conn:
            return [dict(id=r['id'], control=r['control'], stage=ledger._next(json.loads(r['receipts'])), locked=r['token'] is not None) for r in conn.execute('SELECT * FROM runs ORDER BY rowid')]

    def review(self, run, offset=0, limit=24):
        c.digest_ok(run); c.number(offset); c.number(limit,100); require(limit>0,'Invalid page size')
        l=ReadLedger(self.root); d=ReadDecisions(l)
        with l._tx() as conn:
            r=l._row(conn,'runs',run); manifest,receipts,_=l._validate(r)
            refs=load_page(pinned(self.root,manifest['inputs']['references'])); c.fields(refs,('schema','inventories'))
            require(refs['schema']==1 and 1<=len(refs['inventories'])<=12,'Invalid inventory bundle')
            inv={}
            for item in refs['inventories']:
                c.fields(item,('alphabet',)); value=load_page(pinned(self.root,item['alphabet'])); name=value['convention']; labels=value['labels']
                require(type(name) is str and name and name not in inv and type(labels) is list and 2<=len(labels)<=256 and all(type(x) is str and x and x!='unknown' for x in labels) and len(set(labels))==len(labels),'Invalid inventory')
                inv[name]=labels
            tables={x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'vrs096_decisions' not in tables or 'vrs095_queue_runs' not in tables or not conn.execute('SELECT 1 FROM vrs095_queue_runs WHERE run_id=?',(run,)).fetchone():
                return dict(items=[],snapshot=None,inventory=inv,next_offset=None,control=r['control'])
            snap, latest=d.snapshot(conn,run); items=[]; skipped=0; more=False
            for row in conn.execute('SELECT id,payload FROM vrs095_queue_items WHERE run_id=? ORDER BY position',(run,)):
                decision=latest.get(row['id'])
                if decision and decision['kind'] in ('glyph','false_positive'): continue
                if skipped<offset: skipped+=1; continue
                if len(items)==limit: more=True; break
                item=json.loads(row['payload']); pinned(self.root,item['crop']); item['revision']=decision['expected_revision']+1 if decision else 0; item['deferred']=bool(decision); items.append(item)
            return dict(items=items,snapshot=snap,inventory=inv,next_offset=offset+len(items) if more else None,control=r['control'])

    def crop(self, item):
        from PIL import Image
        with Image.open(pinned(self.root,item['crop'])) as source:
            require(source.width*source.height<=16_000_000,'Crop too large for review')
            box=item['box']; require(0<=box[0]<box[2]<=source.width and 0<=box[1]<box[3]<=source.height,'Invalid glyph geometry')
            return source.convert('RGB'),box

    def catalog(self, rel):
        # Explicit scheme IDs only, no inferred cross-convention mappings.
        if not rel: return {}
        path=safe(self.root,rel); obj=load_page(path); require(obj['schema']==1 and type(obj['schemes']) is list and len(obj['schemes'])<=12,'Invalid visual catalog')
        out={}
        for scheme in obj['schemes']:
            key=scheme['id']; require(type(key) is str and key and key not in out and all(type(scheme[x]) is str and scheme[x] for x in ('name','version','source')),'Invalid catalog provenance')
            entries={}
            for entry in scheme['entries']:
                label=entry['label']; require(type(label) is str and label and label not in entries and 1<=len(entry['samples'])<=8,'Invalid visual entry')
                refs=[]
                for sample in entry['samples']:
                    relpath=(path.parent.relative_to(self.root)/sample['file']).as_posix()
                    ref=dict(path=relpath,sha256=sample['sha256']); pinned(self.root,ref)
                    require(type(sample['source']) is str and sample['source'],'Missing sample provenance')
                    refs.append((ref,sample['source']))
                entries[label]=refs
            require(0<len(entries)<=1024,'Invalid visual catalog coverage')
            out[key]=dict(entries=entries,version=scheme['version'],source=scheme['source'],coverage=scheme.get('coverage','not established'),preview=obj.get('preview',True))
        return out

    def reference_image(self, ref):
        from PIL import Image
        with Image.open(pinned(self.root,ref)) as im:
            require(im.width*im.height<=4_000_000,'Reference too large'); im=im.convert('RGB'); im.thumbnail((240,140)); return im

    def stage_decision(self, item, snapshot, inventory, reviewer, kind, mappings):
        require(type(reviewer) is str and 0<len(reviewer.strip())<=128,'Reviewer required')
        require(kind in ('glyph','false_positive','compound','deferred'),'Invalid decision')
        if kind=='glyph':
            require(set(mappings)==set(inventory),'Every inventory requires a decision')
            for name,row in mappings.items():
                c.fields(row,('state','label')); require(row['state'] in ('mapped','absent','unknown') and (row['label'] in inventory[name] if row['state']=='mapped' else row['label'] is None),'Invalid label/disposition')
        else: require(not mappings,'Non-glyph decision cannot map labels')
        decision=dict(schema=1,run_id=item['run_id'],queue_sha256=snapshot['queue_sha256'],candidate_id=item['id'],expected_revision=item['revision'],reviewer=reviewer.strip(),kind=kind,mappings=mappings)
        path=safe(self.root,'workspace/vrs-desktop/drafts/'+c.digest(decision)+'.json')
        if path.exists(): require(c.load(path)==decision,'Draft collision')
        else: atomic_json(path,decision)
        return path.relative_to(self.root).as_posix()

    def drafts(self):
        base=safe(self.root,'workspace/vrs-desktop/drafts')
        if not base.exists(): return []
        result=[]
        for p in sorted(base.glob('*.json')):
            rel=p.relative_to(self.root).as_posix(); value=c.load(safe(self.root,rel)); require(p.stem==c.digest(value),'Draft integrity mismatch')
            result.append(dict(path=rel,run_id=value['run_id'],candidate_id=value['candidate_id'],kind=value['kind'],revision=value['expected_revision']))
        return result

    def submit_draft(self,interpreter,rel):
        require(rel in {x['path'] for x in self.drafts()},'Unknown local draft')
        return self.command(interpreter,'decide',rel)

    def file_ref(self,rel):
        p=safe(self.root,rel); require(p.is_file(),'Missing local file')
        return dict(path=rel,sha256=sha(p))

    def make_manifest(self,roles,transcriptions,seed=7):
        c.fields(roles,c.ROLES); c.number(seed,2**32-1)
        manifest=dict(schema=1,module=c.MODULE,protocol=c.PROTOCOL,backend='cpu',seed=seed,run_nonce=uuid.uuid4().hex,inputs={k:self.file_ref(v) for k,v in roles.items()},transcriptions=[self.file_ref(v) for v in transcriptions])
        c.manifest(self.root,manifest)
        import vrs_recognition
        vrs_recognition.inputs(self.root,manifest)
        # Validate the local page scope and supported transcription syntax before recording.
        groups=c.load(pinned(self.root,manifest['inputs']['groups']))
        require(type(groups) is dict and 1<=len(groups)<=213 and all(type(k) is str and k.isdecimal() and str(int(k))==k and int(k)>0 and type(v) is str and v.strip() for k,v in groups.items()),'Invalid page scope')
        import fitz, alignment
        with fitz.open(pinned(self.root,manifest['inputs']['manuscript'])) as doc:
            require(doc.is_pdf and not doc.needs_pass and all(int(k)<=len(doc) for k in groups),'Invalid manuscript or page scope')
        for entry in manifest['transcriptions']: alignment.load_source(pinned(self.root,entry),entry['sha256'])
        rel='config/runs/'+manifest['run_nonce']+'.json'; p=safe(self.root,rel); require(not p.exists(),'Manifest collision'); atomic_json(p,manifest)
        return dict(path=rel,**self.manifest_info(rel))

    def build_catalog(self,pdf,plan,preview=False):
        import reference_import
        source=safe(self.root,pdf); approved=safe(self.root,plan); rel='data/catalogs/'+uuid.uuid4().hex
        target=safe(self.root,rel); target.parent.mkdir(parents=True,exist_ok=True)
        try:
            details=reference_import.build(source,approved,target,preview=preview)
            self.catalog(rel+'/references.json')
            return dict(path=rel+'/references.json',details=details,preview=preview)
        except BaseException:
            if target.exists(): shutil.rmtree(target)
            raise

    def command(self, interpreter, action, arg):
        require(action in ('decide','register'),'Unapproved command')
        p=Path(interpreter)
        require(p.is_absolute() and p.is_file() and p.name.lower() in ('python','python3','python.exe','python3.exe','python3.13','python3.12'),'Select local compute Python explicitly')
        script=Path(__file__).with_name('vrs_runtime.py').resolve(strict=True); safe(self.root,arg)
        result=subprocess.run([str(p),str(script),str(self.root),action,arg],cwd=self.root,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120,**background_options())
        require(result.returncode==0, 'Worker rejected request: '+(result.stdout or result.stderr)[-800:])
        return json.loads(result.stdout)

    def import_source(self, path, role):
        """Explicit local copy only. Content addressed; no external file mutated."""
        source=Path(path).resolve(strict=True); require(source.is_file(),'Source not a file')
        require(role in ('manuscript','reference_pdf','transcription','json'),'Invalid source role')
        require(0<source.stat().st_size<=1024**3,'Source outside size limit')
        digest=sha(source); suffix={'manuscript':'.pdf','reference_pdf':'.pdf','transcription':'.txt','json':'.json'}[role]
        target=safe(self.root,f'data/imports/{digest}{suffix}'); target.parent.mkdir(parents=True,exist_ok=True)
        tmp=target.with_name('.'+uuid.uuid4().hex+'.part')
        try:
            if not target.exists():
                with source.open('rb') as f,tmp.open('xb') as out: shutil.copyfileobj(f,out,1024*1024); out.flush(); os.fsync(out.fileno())
                require(sha(tmp)==digest,'Source changed during import'); inspect=tmp
            else: require(sha(target)==digest,'Existing import corrupt'); inspect=target
            if role in ('manuscript','reference_pdf'):
                import fitz
                with fitz.open(inspect,filetype='pdf') as doc: require(doc.is_pdf and not doc.needs_pass and 0<len(doc)<=10000,'Invalid or encrypted PDF'); details=dict(pages=len(doc))
            elif role=='transcription':
                import alignment
                _,_,details=alignment.load_source(inspect,digest)
            else: details=dict(keys=sorted(c.load(inspect).keys()))
            if inspect==tmp:
                # No replace, concurrent same-content import safe.
                try: os.link(tmp,target)
                except FileExistsError: require(sha(target)==digest,'Import collision')
            result=dict(role=role,path=target.relative_to(self.root).as_posix(),sha256=digest,details=details)
            record=safe(self.root,'data/imports/index/'+role+'-'+digest+'.json'); atomic_json(record,result)
            return result
        finally: tmp.unlink(missing_ok=True)

    def sources(self):
        base=safe(self.root,'data/imports/index')
        if not base.exists(): return []
        result=[]
        for p in sorted(base.glob('*.json')):
            value=c.load(safe(self.root,p.relative_to(self.root).as_posix())); pinned(self.root,dict(path=value['path'],sha256=value['sha256'])); result.append(value)
        return result

    def manifest_info(self, rel):
        value=c.load(safe(self.root,rel)); run=c.manifest(self.root,value)
        # Verify source roles, bundles and nested pins via the existing lightweight input validator.
        import vrs_recognition
        inv,models,approval,mapping=vrs_recognition.inputs(self.root,value)
        return dict(run_id=run,backend=value['backend'],inventories={k:len(v[0]) for k,v in inv.items()},models=list(models),approved=approval is not None,mapping=mapping is not None,transcriptions=len(value['transcriptions']))

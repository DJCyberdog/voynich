"""VRS-095 increment 1: local headless scheduler and proposal stages.
No remote jobs, publication, certified recognition or automatic model promotion.
"""
import argparse
import importlib.metadata
import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import vrs_contract as c
import vrs_core as core
import vrs_hardware as h
from vrs_ledger import Ledger

VERSION = '0.9.5-alpha.1'
SOURCE_FILES = ('vrs_coordinator.py', 'vrs_ledger.py', 'vrs_contract.py', 'vrs_core.py',
                'vrs_hardware.py', 'regions.py', 'vrs_surface.py', 'glyphs.py', 'worker.py')


class StopRequested(Exception):
    pass


def worker_identity():
    root = Path(__file__).resolve().parent
    return c.digest({'version': VERSION, 'sources': {n: core.sha(root/n) for n in SOURCE_FILES},
                     'python': list(sys.version_info[:3]),
                     'packages': {n: importlib.metadata.version(n) for n in ('Pillow','PyMuPDF','numpy','psutil')}})


def inside(root, rel):
    path = root
    for part in Path(rel).parts:
        core.require(part not in ('..', '.', '') and not Path(part).is_absolute(), 'Unsafe workspace path')
        path = path/part
        core.require(not path.is_symlink() and not getattr(path,'is_junction',lambda:False)(), 'Workspace link forbidden')
    core.require(path.resolve().is_relative_to(root), 'Workspace escape')
    return path


def ref(root, path):
    value = {'path': Path(path).resolve(strict=True).relative_to(root).as_posix(), 'sha256': core.sha(path)}
    c.artifact(root,value)
    return value


def write_new(path, value):
    # Unique attempt directories; no replacement of existing immutable outputs.
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,sort_keys=True,indent=2,allow_nan=False); f.write('\n')
        f.flush(); os.fsync(f.fileno())


@contextmanager
def scheduler_lock(path):
    """OS-owned lock, released on process death; ledger recovery is separate."""
    with path.open('a+b') as f:
        if os.fstat(f.fileno()).st_size == 0:
            f.write(b'0'); f.flush()
        f.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            yield
        finally:
            f.seek(0)
            if os.name == 'nt': msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else: fcntl.flock(f.fileno(),fcntl.LOCK_UN)


class CoordinatorLedger(Ledger):
    """Read-only extensions using the existing schema-1 transaction/ownership contract."""
    def registered(self):
        with self._tx() as conn:
            return [dict(run_id=r['id'],control=r['control'],locked=r['token'] is not None,worker=r['worker'])
                    for r in conn.execute('SELECT id,control,token,worker FROM runs ORDER BY rowid')]

    def context(self, run, token, identity):
        with self._tx() as conn:
            row = self._owned(conn,run,token)
            core.require(row['worker']==identity and row['backend'] in ('cpu','cuda'),'Coordinator identity/backend changed')
            manifest,receipts,_ = self._validate(row)
            core.require(row['backend']==('cuda' if manifest['backend']=='cuda' else 'cpu'),'Frozen backend mismatch')
            return manifest,receipts


class Coordinator:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        self.home = inside(self.root,'workspace/vrs095')
        self.home.mkdir(parents=True,exist_ok=True)
        self.lock = inside(self.root,'workspace/vrs095/coordinator.lock')
        self.ledger = CoordinatorLedger(self.root,inside(self.root,'workspace/vrs095/ledger.sqlite'))
        self.identity = worker_identity()

    def register(self, manifest):
        c.manifest(self.root,manifest)
        # This increment executes CPU proposal stages only. No CUDA-labelled partial runs.
        core.require(manifest['backend'] in ('cpu','auto'),'CUDA stage adapter not yet enabled')
        return self.ledger.register(manifest,'cpu',self.identity)

    def _boundary(self, run):
        if self.ledger.status(run)['control'] != 'READY': raise StopRequested()

    def _admit(self, ram, disk):
        info = h.snapshot(self.home,'cpu')
        work = dict(ram_base=0,ram_item=ram,vram_base=0,vram_item=0,disk=disk,items=1)
        plan = h.plan(info,work,'cpu')
        h.admit_next(info,plan,ram,disk_bytes=disk)

    def _page_manifests(self, index):
        for row in index['pages']:
            path = c.artifact(self.root,row['manifest']); m = core.read(path)
            core.require(set(m['page_dimensions'])=={str(row['page'])},'Page binding mismatch')
            core.require(len(m['regions'])==row['regions'],'Region count mismatch')
            if m.get('surface_policy') is not None:
                import vrs_surface as surface
                core.require(m['surface_policy']==surface.POLICY and m['source_sha256']==surface.YALE_SHA256 and set(m['surfaces'])=={str(row['page'])},'Surface policy binding mismatch')
                s=m['surfaces'][str(row['page'])];b=s['pixel_box']
                core.require(s['page']==row['page'] and s['source_sha256']==m['source_sha256'] and s['policy']==surface.POLICY and s['proposals']==len(m['regions']) and s['screened']==m['screened'],'Surface accounting mismatch')
                core.require((b is None and not m['regions'] and s['status']=='METADATA_ONLY' and row['page']==1) or (isinstance(b,list) and len(b)==4 and s['status']=='IMAGE_ENVELOPE' and all(b[0]<=r['pixel_box'][0]<r['pixel_box'][2]<=b[2] and b[1]<=r['pixel_box'][1]<r['pixel_box'][3]<=b[3] for r in m['regions'])),'Region outside approved surface')
            core.require(len({r['id'] for r in m['regions']})==len(m['regions']),'Duplicate region')
            for region in m['regions']:
                core.require(region['page']==row['page'],'Region page mismatch')
                rel = (path.parent.relative_to(self.root)/region['file']).as_posix()
                c.artifact(self.root,{'path':rel,'sha256':region['sha256']})
            yield row,path,m

    def _validate_output(self, run, item, receipts):
        if item['artifact'] is None: return
        data = core.read(c.artifact(self.root,item['artifact']))
        core.require(data['schema']==1 and data['run_id']==run and data['stage']==item['stage'] and data['scientific_status']=='UNADJUDICATED','Stage output binding mismatch')
        if item['stage']=='script_regions':
            core.require(data['kind']=='INK_PROPOSALS_ONLY','Unvalidated script assertion')
            pages=[row['page'] for row in data['pages']]
            core.require(pages and pages==sorted(set(pages)),'Invalid page index')
            for _ in self._page_manifests(data): pass
        elif item['stage']=='glyph_segmentation':
            core.require(data['kind']=='UNREVIEWED_BOX_PROPOSALS_ONLY','Unvalidated segmentation assertion')
            source=receipts['script_regions']['artifact']
            core.require(data['source']==source,'Segmentation source binding mismatch')
            old=core.read(c.artifact(self.root,source))
            core.require([r['page'] for r in data['pages']]==[r['page'] for r in old['pages']],'Segmentation page coverage mismatch')
            for row, prior in zip(data['pages'],old['pages']):
                value=core.read(c.artifact(self.root,row['proposals']))
                core.require(value['source']==prior['manifest'],'Page source mismatch')
                manifest=core.read(c.artifact(self.root,prior['manifest']))
                core.require([r['id'] for r in value['regions']]==[r['id'] for r in manifest['regions']],'Region coverage mismatch')
                core.require(all(r['status']=='unreviewed' for r in value['regions']),'Unexpected review status')
                core.require(sum(len(r['boxes']) for r in value['regions'])==row['candidates'],'Candidate count mismatch')
        else:
            raise ValueError('No validated output adapter for stage')

    def _regions(self, run, manifest, attempt):
        import fitz
        import math
        import regions
        import vrs_surface as surface
        pdf = c.artifact(self.root,manifest['inputs']['manuscript'])
        groups = c.artifact(self.root,manifest['inputs']['groups'])
        mapping = core.read(groups)
        isolate=manifest['inputs']['manuscript']['sha256']==surface.YALE_SHA256
        core.require(type(mapping) is dict and mapping and len(mapping)<=(surface.YALE_PAGES if isolate else 213),'Invalid page scope')
        pages=sorted(int(k) for k in mapping)
        core.require(set(mapping)=={str(p) for p in pages} and all(type(v) is str and v.strip() for v in mapping.values()),'Invalid page mapping')
        output=[]
        with fitz.open(pdf) as doc:
            core.require(all(1<=p<=len(doc) for p in pages),'Page outside PDF')
            for page in pages:
                self._boundary(run)
                rect=doc[page-1].rect
                width,height=math.ceil(rect.width*200/72)+2,math.ceil(rect.height*200/72)+2
                # Conservative planning estimate, not measured peak or hard OS cap.
                ram=256*h.MIB+64*width*height
                disk=h.MIB
                for wf,hf in regions.SCALES:
                    bw,bh=max(1,round(width*wf)),max(1,round(height*hf))
                    disk+=len(regions.starts(width,bw))*len(regions.starts(height,bh))*(4*bw*bh+4096)
                self._admit(ram,disk)
                dest=attempt/f'page-{page:04d}'
                h.bounded_call(regions.propose,pdf,manifest['inputs']['manuscript']['sha256'],groups,dest,pages=[page],isolate_yale=isolate)
                m=core.read(dest/'manifest.json')
                output.append({'page':page,'manifest':ref(self.root,dest/'manifest.json'),'regions':len(m['regions'])})
        return {'kind':'INK_PROPOSALS_ONLY','pages':output}

    def _segment(self, run, receipts, attempt):
        import glyphs
        from PIL import Image
        source=receipts['script_regions']['artifact']
        index=core.read(c.artifact(self.root,source)); output=[]
        for row,path,m in self._page_manifests(index):
            self._boundary(run)
            # A page is the unit of temporary work. Each box is only a proposal.
            n=len(m['regions']); max_width=max((r['pixel_box'][2]-r['pixel_box'][0] for r in m['regions']),default=1)
            self._admit(256*h.MIB+n*max_width*256,max(h.MIB,n*max_width*128))
            proposals=[]
            for region in m['regions']:
                self._boundary(run)
                with Image.open(path.parent/region['file']) as im:
                    boxes=h.bounded_call(glyphs.boxes,im)
                proposals.append({'id':region['id'],'status':'unreviewed','boxes':boxes})
            dest=attempt/f'page-{row["page"]:04d}.json'
            write_new(dest,{'source':row['manifest'],'regions':proposals})
            output.append({'page':row['page'],'proposals':ref(self.root,dest),'candidates':sum(len(r['boxes']) for r in proposals)})
        return {'kind':'UNREVIEWED_BOX_PROPOSALS_ONLY','source':source,'pages':output}

    def _execute(self, run, stage, manifest, receipts, attempt):
        if stage=='script_regions': value=self._regions(run,manifest,attempt)
        elif stage=='glyph_segmentation': value=self._segment(run,receipts,attempt)
        else:
            # The contract intentionally stops before unvalidated recognition/review.
            return self._item(run,stage,'BLOCKED','UNSUPPORTED')
        value.update(schema=1,run_id=run,stage=stage,scientific_status='UNADJUDICATED')
        path=attempt/'index.json'; write_new(path,value)
        return self._item(run,stage,'COMPLETED','NONE',ref(self.root,path))

    @staticmethod
    def _item(run,stage,state,reason,artifact=None):
        return dict(schema=1,run_id=run,stage=stage,state=state,reason=reason,artifact=artifact,counts=None)

    def _step(self, run):
        token=self.ledger.claim(run)
        owned=True
        try:
            status=self.ledger.status(run); stage=status['next_stage']
            manifest,receipts=self.ledger.context(run,token,self.identity)
            for previous in c.STAGES[:c.STAGES.index(stage)]: self._validate_output(run,receipts[previous],receipts)
            cp=status['checkpoint']
            if cp:
                stored=c.load(c.artifact(self.root,cp['artifact']))
                c.fields(stored,('schema','worker','item'))
                core.require(stored['schema']==1 and stored['worker']==self.identity,'Checkpoint identity mismatch')
                item=stored['item']; c.receipt(self.root,item,run,stage)
                core.require(item['state']=='COMPLETED','Invalid completed-stage checkpoint')
            else:
                self._boundary(run)
                attempt=inside(self.root,f'workspace/vrs095/runs/{run}/{stage}/g-{status["generation"]}')
                attempt.mkdir(parents=True,exist_ok=False)
                try:
                    item=self._execute(run,stage,manifest,receipts,attempt)
                except h.ResourceBlocked:
                    item=self._item(run,stage,'BLOCKED','DEPENDENCY')
                except (ValueError,OSError,RuntimeError,MemoryError,ImportError,KeyError,TypeError):
                    item=self._item(run,stage,'FAILED','PROCESSING_ERROR')
                if item['state']=='COMPLETED':
                    self._validate_output(run,item,receipts)
                    journal=attempt/'checkpoint.json'; write_new(journal,{'schema':1,'worker':self.identity,'item':item})
                    self.ledger.checkpoint(run,token,stage,ref(self.root,journal))
            self._validate_output(run,item,receipts)
            self._boundary(run)
            try:
                control=self.ledger.record(run,token,item)
            except ValueError:
                self._boundary(run)  # stop may race with record transaction
                raise
            owned=control=='READY'
            return {'run_id':run,'stage':stage,'control':control,'reason':item['reason']}
        except StopRequested:
            return {'run_id':run,'control':'STOP_REQUESTED'}
        finally:
            if owned: self.ledger.release(run,token)

    def sweep(self):
        """One stage per ready run, no polling of remote jobs or blocked runs."""
        with scheduler_lock(self.lock):
            output=[]
            for row in self.ledger.registered():
                if row['control']!='READY' or row['locked'] or row['worker']!=self.identity: continue
                run=row['run_id']
                try: output.append(self._step(run))
                except (ValueError,OSError,RuntimeError,KeyError,TypeError) as exc:
                    # Integrity faults cannot be committed through a failing ledger validator.
                    status=self.ledger.status(run)
                    if status['control']=='READY' and not status['locked']: self.ledger.request_stop(run)
                    output.append({'run_id':run,'control':'ERROR','reason':type(exc).__name__})
            return output

    def recover(self, run, generation, *, confirm_stopped=False):
        with scheduler_lock(self.lock):
            self.ledger.recover(run,generation,worker_confirmed_stopped=confirm_stopped)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('root',type=Path)
    sub=p.add_subparsers(dest='action',required=True)
    q=sub.add_parser('register'); q.add_argument('manifest',type=Path)
    sub.add_parser('list'); sub.add_parser('once')
    q=sub.add_parser('watch'); q.add_argument('--interval',type=int,default=5)
    for name in ('status','pause','cancel','resume','recover'):
        q=sub.add_parser(name); q.add_argument('run')
        if name=='recover': q.add_argument('generation',type=int); q.add_argument('--confirm-stopped',action='store_true')
    a=p.parse_args(); co=Coordinator(a.root); action=a.action
    try:
        if action=='register':
            manifest=inside(co.root,a.manifest); result={'run_id':co.register(c.load(manifest))}
        elif action=='list': result=co.ledger.registered()
        elif action=='once': result=co.sweep()
        elif action=='watch':
            h.positive(a.interval,'interval'); core.require(a.interval<=3600,'Interval too long')
            while True:
                for row in co.sweep(): print(json.dumps(row,sort_keys=True),flush=True)
                time.sleep(a.interval)
        elif action=='status': result=co.ledger.status(a.run)
        else:
            if action=='recover': co.recover(a.run,a.generation,confirm_stopped=a.confirm_stopped)
            elif action=='resume': co.ledger.resume(a.run)
            else: co.ledger.request_stop(a.run,cancel=action=='cancel')
            result=co.ledger.status(a.run)
        print(json.dumps(result,sort_keys=True,indent=2)); return 0
    except KeyboardInterrupt: return 130
    except (ValueError,OSError,RuntimeError,KeyError,TypeError,ImportError) as exc:
        print(json.dumps({'status':'ERROR','reason':type(exc).__name__+': '+str(exc)})); return 1


if __name__=='__main__': raise SystemExit(main())

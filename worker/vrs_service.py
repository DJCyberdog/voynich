"""VRS-095 alpha.3–5: local lifecycle and resumable page stages.
Recognition and correction producers remain separate, explicit future interfaces.
"""
import argparse
import json
import math
import signal
import threading
from pathlib import Path

import vrs_contract as c
import vrs_core as core
import vrs_hardware as h
from vrs_coordinator import Coordinator, CoordinatorLedger, StopRequested, inside, ref, scheduler_lock, write_new
from vrs_exceptions import ExceptionQueue, box_key, load_page

VERSION = '0.9.5-alpha.5'
PAGE_STAGES = c.STAGES[:2]


class ServiceLedger(CoordinatorLedger):
    def register_many(self, manifests, identity, *, allow_cuda=False):
        c.digest_ok(identity)
        rows = []
        for manifest in manifests:
            run = c.manifest(self.root, manifest)
            core.require(manifest['backend'] in ('cpu', 'auto') or allow_cuda and manifest['backend']=='cuda', 'CUDA stage adapter not yet enabled')
            receipts = {s: dict(schema=1, run_id=run, stage=s, state='PENDING', reason='NOT_STARTED', artifact=None, counts=None) for s in c.STAGES}
            rows.append((run, self._encode(manifest), 'cuda' if manifest['backend']=='cuda' else 'cpu', identity, self._encode(receipts), 'READY'))
        core.require(len({r[0] for r in rows}) == len(rows), 'Duplicate planned run')
        with self._tx() as conn:
            for row in rows:
                old = conn.execute('SELECT manifest,backend,worker FROM runs WHERE id=?', (row[0],)).fetchone()
                if old:
                    core.require(tuple(old) == row[1:4], 'Run identity conflict')
                else:
                    conn.execute('INSERT INTO runs (id,manifest,backend,worker,receipts,control) VALUES (?,?,?,?,?,?)', row)
        return [r[0] for r in rows]

    def pause_fault(self, run, token, stage, reason):
        with self._tx() as conn:
            row = self._owned(conn, run, token)
            if row['control'] == 'READY':
                self._event(conn, run, 'STAGE_PAUSED', dict(stage=stage, reason=reason))
                conn.execute('UPDATE runs SET control=? WHERE id=?', ('PAUSE_REQUESTED', run))
                return 'PAUSED'
            return 'STOP_REQUESTED'

    def pause_unclaimed(self, run, identity, reason):
        with self._tx() as conn:
            row=self._row(conn,'runs',run)
            if row['control']=='READY' and row['token'] is None and row['worker']==identity:
                stage=self._next(json.loads(row['receipts']))
                self._event(conn,run,'STAGE_PAUSED',dict(stage=stage,reason=reason))
                conn.execute('UPDATE runs SET control=? WHERE id=?',('PAUSED',run))

    def resume_service(self, run, identity):
        with self._tx() as conn:
            row = self._row(conn, 'runs', run)
            core.require(row['worker'] == identity, 'Run belongs to a different worker version')
            core.require(row['token'] is None and row['control'] in ('BLOCKED','PAUSED','FAILED'), 'Run not resumable')
            _, receipts, _ = self._validate(row)
            review = receipts['exception_review']
            core.require(review['reason'] != 'REVIEW_PENDING', 'Authorized correction handoff required (VRS-097)')
            if review['reason'] == 'DEPENDENCY' or review['state'] == 'COMPLETED':
                core.require(not receipts['glyph_classification']['counts']['failed'], 'Failed classification requires a new authorized run')
            stage = self._next(receipts)
            core.require(receipts[stage]['reason'] != 'UNSUPPORTED', 'Stage adapter not enabled; do not retry')
            conn.execute('UPDATE runs SET control=? WHERE id=?', ('READY', run))


class Service(Coordinator):
    def __init__(self, root, *, hybrid_evidence=False):
        super().__init__(root)
        core.require(type(hybrid_evidence) is bool,'Invalid hybrid qualification mode')
        self.hybrid_evidence=hybrid_evidence
        source = Path(__file__).resolve().parent
        self.identity = c.digest(dict(version=VERSION, parent=self.identity,
                                      hybrid_evidence=hybrid_evidence,
                                      sources={n:core.sha(source/n) for n in ('vrs_service.py','vrs_exceptions.py','vrs_hybrid_page.py','vrs_hybrid_grouping.py','vrs_ink.py','vrs_binarize.py','vrs_artifacts.py','vrs_region_evidence.py','vrs_vectors.py')}))
        self.ledger = ServiceLedger(self.root, self.ledger.db)
        self.queue = ExceptionQueue(self.ledger)
        self.stop = threading.Event()

    def register_plan(self, plan):
        c.fields(plan, ('schema','manifests'))
        core.require(type(plan['schema']) is int and plan['schema']==1 and type(plan['manifests']) is list and 1<=len(plan['manifests'])<=213,'Invalid local schedule')
        manifests = [c.load(c.artifact(self.root, entry)) for entry in plan['manifests']]
        return self.ledger.register_many(manifests, self.identity)

    def _boundary(self, run):
        if self.stop.is_set(): raise StopRequested()
        super()._boundary(run)

    def _scope(self, stage, manifest, receipts):
        if stage == 'script_regions':
            import fitz
            import vrs_surface as surface
            groups = c.artifact(self.root, manifest['inputs']['groups'])
            pdf = c.artifact(self.root, manifest['inputs']['manuscript'])
            mapping = c.load(groups)
            isolate=manifest['inputs']['manuscript']['sha256']==surface.YALE_SHA256
            core.require(not self.hybrid_evidence or isolate,'Hybrid qualification requires the pinned Yale source')
            core.require(type(mapping) is dict and 1<=len(mapping)<=(surface.YALE_PAGES if isolate else 213),'Invalid page scope')
            pages = sorted(int(k) for k in mapping)
            core.require(set(mapping)=={str(p) for p in pages} and all(type(v) is str and v.strip() for v in mapping.values()),'Invalid page mapping')
            with fitz.open(pdf) as doc:
                core.require(not isolate or len(doc)==surface.YALE_PAGES,'Yale PDF page count mismatch')
                core.require(all(1<=p<=len(doc) for p in pages),'Page outside PDF')
            return pages, (pdf, groups, manifest['inputs']['manuscript']['sha256'])
        self._validate_output(receipts['script_regions']['run_id'],receipts['script_regions'],receipts)
        source = core.read(c.artifact(self.root,receipts['script_regions']['artifact']))
        if self.hybrid_evidence:
            import vrs_surface as surface
            core.require(manifest['inputs']['manuscript']['sha256']==surface.YALE_SHA256,'Hybrid qualification requires the pinned Yale source')
            source=dict(source,native_source=manifest['inputs']['manuscript'])
        return [r['page'] for r in source['pages']], source

    def _check_prefix(self, stage, pages, expected, source):
        core.require(type(pages) is list and len(pages)<=len(expected) and [x['page'] for x in pages]==expected[:len(pages)],'Invalid checkpoint page prefix')
        if stage=='script_regions':
            import vrs_surface as surface
            _,groups,expected_sha=source
            group_sha=core.sha(groups)
            for _,_,m in self._page_manifests({'pages':pages}):
                core.require(m['source_sha256']==expected_sha and m['groups_sha256']==group_sha,'Checkpoint source or groups mismatch')
                if expected_sha==surface.YALE_SHA256:
                    core.require(m.get('surface_policy')==surface.POLICY,'Yale checkpoint missing mandatory surface isolation')
        else:
            for row,prior in zip(pages,source['pages']):
                c.fields(row,('page','proposals','candidates'))
                value=load_page(c.artifact(self.root,row['proposals']))
                core.require(value['source']==prior['manifest'],'Page source mismatch')
                m=load_page(c.artifact(self.root,prior['manifest']))
                import vrs_segmentation as segmentation
                segmentation.validate(m,value,required=True)
                import vrs_hybrid_page as hybrid
                hybrid.validate_ref(self.root,value,m,expected_source=source.get('native_source'),required=self.hybrid_evidence)
                core.require([r['id'] for r in value['regions']]==[r['id'] for r in m['regions']],'Region coverage mismatch')
                count=0
                for r, original in zip(value['regions'],m['regions']):
                    core.require(r['status']=='unreviewed','Unexpected review status')
                    px=box_key(original['pixel_box']); boxes=[box_key(b) for b in r['boxes']]
                    core.require(len(set(boxes))==len(boxes) and all(b[2]<=px[2]-px[0] and b[3]<=px[3]-px[1] for b in boxes),'Invalid proposal geometry')
                    count+=len(boxes)
                core.require(count==row['candidates'],'Candidate count mismatch')

    def _page(self, run, stage, page, source, attempt):
        if stage=='script_regions':
            import fitz
            import regions
            import vrs_surface as surface
            pdf,groups,expected_sha=source
            with fitz.open(pdf) as doc:
                rect=doc[page-1].rect
                width,height=math.ceil(rect.width*200/72)+2,math.ceil(rect.height*200/72)+2
            ram=256*h.MIB+64*width*height; disk=h.MIB
            for wf,hf in regions.SCALES:
                bw,bh=max(1,round(width*wf)),max(1,round(height*hf))
                disk+=len(regions.starts(width,bw))*len(regions.starts(height,bh))*(4*bw*bh+4096)
            self._admit(ram,disk)
            dest=attempt/f'page-{page:04d}'
            h.bounded_call(regions.propose,pdf,expected_sha,groups,dest,pages=[page],
                           isolate_yale=expected_sha==surface.YALE_SHA256)
            path=dest/'manifest.json'; m=core.read(path)
            return dict(page=page,manifest=ref(self.root,path),regions=len(m['regions']))
        import vrs_segmentation as segmentation
        from PIL import Image
        row=next(r for r in source['pages'] if r['page']==page)
        _,path,m=next(self._page_manifests({'pages':[row]}))
        n=len(m['regions']); width=max((r['pixel_box'][2]-r['pixel_box'][0] for r in m['regions']),default=1)
        self._admit(256*h.MIB+n*width*256,max(h.MIB,n*width*128))
        proposals,lineage=h.bounded_call(segmentation.generate,m,
            lambda region:Image.open(path.parent/region['file']),lambda:self._boundary(run))
        dest=attempt/f'page-{page:04d}.json'
        value=dict(source=row['manifest'],regions=proposals,dedup=lineage)
        if self.hybrid_evidence:
            import vrs_hybrid_page as hybrid
            native_source=source['native_source']; pdf=c.artifact(self.root,native_source)
            # Provisional conservative admission estimate, not a hard process cap.
            self._admit(1536*h.MIB,64*h.MIB)
            evidence=h.bounded_call(hybrid.produce,pdf,native_source,page,row['manifest'],m,proposals,lambda:self._boundary(run))
            side=attempt/f'hybrid-{page:04d}.json'; hybrid.write(side,evidence)
            value['hybrid_evidence']=ref(self.root,side)
            self._boundary(run)
        write_new(dest,value)
        return dict(page=page,proposals=ref(self.root,dest),candidates=sum(len(r['boxes']) for r in proposals))

    def _attempt(self,run,stage,generation):
        path=inside(self.root,f'workspace/vrs095/runs/{run}/{stage}/g-{generation}')
        path.mkdir(parents=True,exist_ok=False)
        return path

    def _page_step(self, run, token, stage, status, manifest, receipts):
        expected, source=self._scope(stage,manifest,receipts)
        cp=status['checkpoint']; pages=[]
        if cp:
            saved=c.load(c.artifact(self.root,cp['artifact']))
            c.fields(saved,('schema','worker','run_id','stage','pages'))
            core.require(saved['schema']==1 and saved['worker']==self.identity and saved['run_id']==run and saved['stage']==stage,'Page checkpoint identity mismatch')
            pages=saved['pages']
            self._check_prefix(stage,pages,expected,source)
        attempt=self._attempt(run,stage,status['generation'])
        for page in expected[len(pages):]:
            self._boundary(run)
            # Input files are immutable by contract; recheck pinned originals before each page.
            c.manifest(self.root,manifest)
            row=self._page(run,stage,page,source,attempt)
            index=len(pages)
            page_source=source if stage=='script_regions' else dict(source,pages=source['pages'][index:index+1])
            self._check_prefix(stage,[row],expected[index:index+1],page_source)
            pages.append(row)
            journal=attempt/f'checkpoint-{page:04d}.json'
            write_new(journal,dict(schema=1,worker=self.identity,run_id=run,stage=stage,pages=pages))
            self.ledger.checkpoint(run,token,stage,ref(self.root,journal))
        self._boundary(run)
        self._check_prefix(stage,pages,expected,source)
        data=dict(schema=1,run_id=run,stage=stage,scientific_status='UNADJUDICATED',pages=pages,
                  kind='INK_PROPOSALS_ONLY' if stage=='script_regions' else 'UNREVIEWED_BOX_PROPOSALS_ONLY')
        if stage=='glyph_segmentation': data['source']=receipts['script_regions']['artifact']
        path=attempt/'index.json'; write_new(path,data)
        item=self._item(run,stage,'COMPLETED','NONE',ref(self.root,path))
        self._validate_output(run,item,receipts)
        return item

    @staticmethod
    def _review_data(info, receipt):
        return dict(schema=1,run_id=info['run_id'],stage='exception_review',scientific_status='UNADJUDICATED',
                    kind='EXCEPTION_QUEUE_SNAPSHOT_V1',classification_receipt_sha256=c.digest(receipt),
                    queue_sha256=info['queue_sha256'],classification=info['classification'],pending=info['pending'],resolved=0,deferred=0)

    def _review_step(self, run, status, receipts, info):
        classified=receipts['glyph_classification']
        core.require(classified['counts']==info['classification'],'Queue classification changed')
        if not info['pending'] and classified['counts']['failed']:
            return self._item(run,'exception_review','BLOCKED','DEPENDENCY')
        data=self._review_data(info,classified)
        attempt=self._attempt(run,'exception_review',status['generation'])
        path=attempt/'review.json'; write_new(path,data)
        item=self._item(run,'exception_review','BLOCKED' if info['pending'] else 'COMPLETED','REVIEW_PENDING' if info['pending'] else 'NONE',ref(self.root,path))
        item['counts']=dict(resolved=0,pending=info['pending'],deferred=0)
        return item

    def _alignment_gate(self,run,receipts,info):
        review=receipts['exception_review']; classified=receipts['glyph_classification']
        core.require(review['state']=='COMPLETED' and not info['pending'] and not classified['counts']['failed'],'Review dependency not satisfied')
        core.require(c.load(c.artifact(self.root,review['artifact']))==self._review_data(info,classified),'Review snapshot mismatch')
        return self._item(run,'transcription_alignment','BLOCKED','UNSUPPORTED')

    def _step(self, run):
        status=self.ledger.status(run); stage=status['next_stage']
        if stage not in (*PAGE_STAGES,'exception_review','transcription_alignment'):
            return super()._step(run)
        # Queue import is transactional and idempotent. Crash between import and claim is safe.
        info=None
        if stage in ('exception_review','transcription_alignment'):
            counts=status['receipts']['glyph_classification']['counts']
            # Advisory import budget, not a hard SQLite or process limit.
            self._admit(512*h.MIB+min(counts['total'],500000)*1024,max(h.MIB,counts['abstained']*8192))
            info=self.queue.seed(run)
        token=self.ledger.claim(run); owned=True
        try:
            status=self.ledger.status(run)
            core.require(status['next_stage']==stage,'Run stage changed before claim')
            manifest,receipts=self.ledger.context(run,token,self.identity)
            self._boundary(run)
            if stage in PAGE_STAGES:
                item=self._page_step(run,token,stage,status,manifest,receipts)
            elif stage=='exception_review':
                item=self._review_step(run,status,receipts,info)
            else:
                item=self._alignment_gate(run,receipts,info)
            self._boundary(run)
            try: control=self.ledger.record(run,token,item)
            except ValueError:
                self._boundary(run); raise
            owned=control=='READY'
            return dict(run_id=run,stage=stage,control=control,reason=item['reason'])
        except StopRequested:
            return dict(run_id=run,stage=stage,control='STOP_REQUESTED')
        except (h.ResourceBlocked,MemoryError) as exc:
            control=self.ledger.pause_fault(run,token,stage,'RESOURCE_PRESSURE')
            return dict(run_id=run,stage=stage,control=control,reason='RESOURCE_PRESSURE')
        except (ValueError,OSError,RuntimeError,KeyError,TypeError,ImportError) as exc:
            control=self.ledger.pause_fault(run,token,stage,'PROCESSING_OR_INTEGRITY_ERROR')
            return dict(run_id=run,stage=stage,control=control,reason=type(exc).__name__)
        finally:
            if owned: self.ledger.release(run,token)

    def sweep(self):
        with scheduler_lock(self.lock):
            result=[]
            for row in self.ledger.registered():
                if self.stop.is_set(): break
                if row['control']!='READY' or row['locked'] or row['worker']!=self.identity: continue
                run=row['run_id']
                try: result.append(self._step(run))
                except (ValueError,OSError,RuntimeError,KeyError,TypeError,ImportError) as exc:
                    reason='RESOURCE_PRESSURE' if isinstance(exc,h.ResourceBlocked) else 'PROCESSING_OR_INTEGRITY_ERROR'
                    self.ledger.pause_unclaimed(run,self.identity,reason)
                    result.append(dict(run_id=run,control='ERROR',reason=type(exc).__name__))
            return result


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('root',type=Path)
    p.add_argument('--hybrid-evidence',action='store_true',help='Explicit pinned-Yale qualification sidecar; legacy proposals unchanged')
    sub=p.add_subparsers(dest='action',required=True)
    for name in ('register','register-plan'):
        q=sub.add_parser(name); q.add_argument('path',type=Path)
    sub.add_parser('list'); sub.add_parser('once')
    q=sub.add_parser('watch'); q.add_argument('--interval',type=int,default=5); q.add_argument('--plan',type=Path); q.add_argument('--stop-file',type=Path,help='Explicit root-local cooperative stop sentinel')
    for name in ('status','pause','cancel','resume','recover','queue'):
        q=sub.add_parser(name); q.add_argument('run')
        if name=='recover': q.add_argument('generation',type=int); q.add_argument('--confirm-stopped',action='store_true')
    a=p.parse_args()
    try:
        app=Service(a.root,hybrid_evidence=a.hybrid_evidence); action=a.action
        if action=='register': result=dict(run_id=app.register(c.load(inside(app.root,a.path))))
        elif action=='register-plan': result=dict(run_ids=app.register_plan(c.load(inside(app.root,a.path))))
        elif action=='list': result=app.ledger.registered()
        elif action=='once': result=app.sweep()
        elif action=='watch':
            h.positive(a.interval,'interval'); core.require(a.interval<=3600,'Interval too long')
            if a.plan is not None: app.register_plan(c.load(inside(app.root,a.plan)))
            for sig in (signal.SIGINT,signal.SIGTERM): signal.signal(sig,lambda *_:app.stop.set())
            stopper=None
            if a.stop_file is not None:
                # Same cooperative boundary semantics as managed desktop stop.
                # The caller owns this explicit local sentinel and its lifecycle.
                sentinel=inside(app.root,a.stop_file)
                core.require(not sentinel.exists(),'Stale stop sentinel')
                def poll_stop():
                    while not app.stop.wait(.2):
                        try:
                            if inside(app.root,a.stop_file).exists(): app.stop.set(); return
                        except (OSError,ValueError):
                            app.stop.set(); return
                stopper=threading.Thread(target=poll_stop,daemon=True); stopper.start()
            try:
                while not app.stop.is_set():
                    for row in app.sweep(): print(json.dumps(row,sort_keys=True),flush=True)
                    app.stop.wait(a.interval)
            finally:
                app.stop.set()
                if stopper is not None: stopper.join(timeout=1)
            return 0
        elif action=='status': result=app.ledger.status(a.run)
        elif action=='queue': result=app.queue.summary(a.run)
        else:
            if action=='resume': app.ledger.resume_service(a.run,app.identity)
            elif action=='recover': app.recover(a.run,a.generation,confirm_stopped=a.confirm_stopped)
            else: app.ledger.request_stop(a.run,cancel=action=='cancel')
            result=app.ledger.status(a.run)
        print(json.dumps(result,indent=2,sort_keys=True)); return 0
    except KeyboardInterrupt: return 130
    except (ValueError,OSError,RuntimeError,KeyError,TypeError,ImportError) as exc:
        print(json.dumps(dict(status='ERROR',reason=type(exc).__name__+': '+str(exc)))); return 1


if __name__=='__main__': raise SystemExit(main())

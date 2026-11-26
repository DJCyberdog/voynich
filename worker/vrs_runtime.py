"""VRS 0.9.6 local recognition, review and explicit physical mapping comparison."""
import argparse
import importlib.metadata
import json
import signal
from pathlib import Path

import vrs_contract as c
import vrs_core as core
import vrs_hardware as h
import vrs_recognition as rec
from vrs_coordinator import StopRequested, inside, ref, write_new
from vrs_exceptions import load_page, outcomes, candidate_id, box_key
from vrs_service import Service
from vrs_decisions import Decisions

VERSION='0.13.1-cuda-candidate.3'


class Runtime(Service):
    def __init__(self,root):
        super().__init__(root)
        path=Path(__file__).resolve().parent
        self.identity=c.digest(dict(parent=self.identity,version=VERSION,torch=importlib.metadata.version('torch'),sources={n:core.sha(path/n) for n in ('vrs_runtime.py','vrs_recognition.py','vrs_decisions.py','alignment.py')}))
        self.decisions=Decisions(self.ledger)

    def _backend(self,manifest):
        if manifest['backend']!='cuda': return 'cpu'
        info=h.snapshot(self.home,'cuda',0)
        if not (info.get('gpu') or {}).get('ok'):
            raise h.ResourceBlocked('Explicit CUDA unavailable; no CPU fallback')
        h.cuda_binding(info)
        return 'cuda'

    def register(self,manifest):
        c.manifest(self.root,manifest); rec.inputs(self.root,manifest)
        backend=self._backend(manifest)
        return self.ledger.register(manifest,backend,self.identity)

    def register_plan(self,plan):
        c.fields(plan,('schema','manifests')); core.require(type(plan['schema']) is int and plan['schema']==1 and type(plan['manifests']) is list and 1<=len(plan['manifests'])<=213,'Invalid local schedule')
        manifests=[]
        for entry in plan['manifests']:
            manifest=c.load(c.artifact(self.root,entry)); c.manifest(self.root,manifest); rec.inputs(self.root,manifest)
            self._backend(manifest); manifests.append(manifest)
        return self.ledger.register_many(manifests,self.identity,allow_cuda=True)

    def _classification_pages(self,receipts):
        self._validate_output(receipts['script_regions']['run_id'],receipts['script_regions'],receipts)
        self._validate_output(receipts['glyph_segmentation']['run_id'],receipts['glyph_segmentation'],receipts)
        ri=load_page(c.artifact(self.root,receipts['script_regions']['artifact']))
        si=load_page(c.artifact(self.root,receipts['glyph_segmentation']['artifact']))
        return ri,si

    def _page_outcome(self,run,rr,ss,inv,models,approval,attempt,backend='cpu',cuda_binding=None):
        from PIL import Image
        mp=c.artifact(self.root,rr['manifest']); m=load_page(mp); proposals=load_page(c.artifact(self.root,ss['proposals']))
        rows=[]; total=ss['candidates']; largest=max(len(x[0]) for x in inv.values())
        self._admit(256*h.MIB+total*4096+64*largest*1024*8,max(h.MIB,total*8192))
        for region,proposal in zip(m['regions'],proposals['regions']):
            self._boundary(run); crop=mp.parent/region['file']
            with Image.open(c.artifact(self.root,dict(path=crop.relative_to(self.root).as_posix(),sha256=region['sha256']))) as im:
                start=0
                while start<len(proposal['boxes']):
                    self._boundary(run)
                    batch=min(64,len(proposal['boxes'])-start)
                    if backend=='cuda':
                        core.require(approval is None,'CUDA policy must abstain without separate calibration')
                        # Estimates are incremental, not hard driver/OS quotas.
                        info=h.snapshot(self.home,'cuda',0)
                        core.require(h.cuda_binding(info)==cuda_binding,'CUDA device/build changed during classification')
                        ram_base=256*h.MIB+len(rows)*4096
                        ram_item=max(4096,largest*1024*16)
                        vram_base=64*h.MIB+largest*1024*4
                        vram_item=max(4096,largest*1024*16)
                        selected=h.plan(info,dict(ram_base=ram_base,ram_item=ram_item,vram_base=vram_base,vram_item=vram_item,disk=h.MIB,items=batch),'cuda')
                        batch=selected['batch_ceiling']
                        h.admit_next(info,selected,ram_base+batch*ram_item,vram_base+batch*vram_item,h.MIB)
                    boxes=proposal['boxes'][start:start+batch]
                    self._admit(256*h.MIB+batch*largest*1024*16+len(rows)*4096,h.MIB)
                    results=h.bounded_call(rec.candidate if backend=='cuda' else rec.classify,boxes,im,inv,models)
                    start+=len(boxes)
                    core.require(len(results)==len(boxes),'Classifier denominator mismatch')
                    for box,pred in zip(boxes,results):
                        key=(rr['page'],region['id'],region['sha256'],box_key(box))
                        outcome,reason=rec.route(pred,inv,approval,key)
                        rows.append(dict(region_id=region['id'],box=box,outcome=outcome,reason=reason,uncertainty=None,predictions=pred))
        path=attempt/f'outcomes-{rr["page"]:04d}.json'
        write_new(path,dict(schema=1,run_id=run,page=rr['page'],source=ss['proposals'],rows=rows))
        return dict(page=rr['page'],outcomes=ref(self.root,path))

    def _verify_page(self,run,rr,ss,pp,inv,approval,models):
        core.require(rr['page']==ss['page']==pp['page'],'Page binding mismatch')
        mp=c.artifact(self.root,rr['manifest']); m=load_page(mp); proposal=load_page(c.artifact(self.root,ss['proposals'])); data=load_page(c.artifact(self.root,pp['outcomes']))
        c.fields(data,('schema','run_id','page','source','rows')); core.require(data['schema']==1 and data['run_id']==run and data['page']==rr['page'] and data['source']==ss['proposals'],'Prediction binding mismatch')
        expected=[(r['id'],r['sha256'],b) for r,p in zip(m['regions'],proposal['regions']) for b in p['boxes']]
        core.require(len(expected)==len(data['rows'])==ss['candidates'],'Prediction denominator mismatch')
        counts=dict(total=0,accepted=0,abstained=0,failed=0)
        for (rid,digest,box),row in zip(expected,data['rows']):
            c.fields(row,('region_id','box','outcome','reason','uncertainty','predictions'))
            core.require(row['region_id']==rid and row['box']==box and row['uncertainty'] is None,'Prediction occurrence mismatch')
            core.require(set(row['predictions'])==set(models),'Missing model prediction')
            actual=rec.route(row['predictions'],inv,approval,(rr['page'],rid,digest,box_key(box)))
            core.require(actual==(row['outcome'],row['reason']),'Policy outcome mismatch')
            counts['total']+=1; counts[row['outcome'].lower()]+=1
        return counts

    def _verify_classification(self,run,manifest,receipts,inv,approval,models):
        ri,si=self._classification_pages(receipts); data=load_page(c.artifact(self.root,receipts['glyph_classification']['artifact']))
        core.require(data['kind']=='OCCURRENCE_OUTCOMES_V2' and len(data['pages'])==len(ri['pages']),'Invalid classification index')
        counts=dict(total=0,accepted=0,abstained=0,failed=0)
        for rr,ss,pp in zip(ri['pages'],si['pages'],data['pages']):
            for k,n in self._verify_page(run,rr,ss,pp,inv,approval,models).items(): counts[k]+=n
        core.require(counts==receipts['glyph_classification']['counts'],'Classification counts changed')
        # Full legacy occurrence and artifact validation, including source/model/policy hashes.
        for _ in outcomes(self.root,run,manifest,receipts): pass
        return ri,si,data

    def _classify(self,run,token,status,manifest,receipts,inv,models,approval):
        stage='glyph_classification'; backend=self._backend(manifest); ri,si=self._classification_pages(receipts); pages=[]; counts=dict(total=0,accepted=0,abstained=0,failed=0)
        binding=h.cuda_binding(h.snapshot(self.home,'cuda',0)) if backend=='cuda' else None
        provenance={'cuda_binding':binding} if binding is not None else {}
        if status['checkpoint']:
            cp=c.load(c.artifact(self.root,status['checkpoint']['artifact'])); c.fields(cp,('schema','worker','run_id','stage','pages')+tuple(provenance))
            core.require(cp.get('cuda_binding')==binding,'CUDA checkpoint device/build changed')
            core.require(cp['schema']==1 and cp['worker']==self.identity and cp['run_id']==run and cp['stage']==stage,'Classification checkpoint mismatch'); pages=cp['pages']
            core.require(len(pages)<=len(ri['pages']),'Checkpoint exceeds scope')
        attempt=self._attempt(run,stage,status['generation'])
        import torch
        previous=torch.get_num_threads()
        try:
            torch.set_num_threads(max(1,min(previous,4)))
            for idx,(rr,ss) in enumerate(zip(ri['pages'],si['pages'])):
                self._boundary(run)
                if idx>=len(pages):
                    pages.append(self._page_outcome(run,rr,ss,inv,models,approval,attempt,backend,binding))
                    self._verify_page(run,rr,ss,pages[idx],inv,approval,models)
                    path=attempt/f'checkpoint-{rr["page"]:04d}.json'
                    write_new(path,dict(schema=1,worker=self.identity,run_id=run,stage=stage,pages=pages,**provenance))
                    self.ledger.checkpoint(run,token,stage,ref(self.root,path))
                for k,n in self._verify_page(run,rr,ss,pages[idx],inv,approval,models).items(): counts[k]+=n
        finally: torch.set_num_threads(previous)
        # Recheck device binding and nested dependency bytes before publication.
        if binding is not None:
            core.require(h.cuda_binding(h.snapshot(self.home,'cuda',0))==binding,'CUDA device/build changed before receipt')
        rec.inputs(self.root,manifest)
        path=attempt/'index.json'; i=manifest['inputs']
        write_new(path,dict(schema=1,run_id=run,stage=stage,scientific_status='UNADJUDICATED',kind='OCCURRENCE_OUTCOMES_V2',source=receipts['glyph_segmentation']['artifact'],model_sha256=i['model']['sha256'],policy_sha256=i['recognition_policy']['sha256'],references_sha256=i['references']['sha256'],pages=pages,**provenance))
        item=self._item(run,stage,'COMPLETED','NONE',ref(self.root,path)); item['counts']=counts
        self._verify_classification(run,manifest,{**receipts,stage:item},inv,approval,models)
        return item

    def _review(self,run,status,receipts,snap):
        counts={k:snap[k] for k in ('resolved','pending','deferred')}
        blocked=bool(counts['pending']+counts['deferred'])
        if not blocked and receipts['glyph_classification']['counts']['failed']: return self._item(run,'exception_review','BLOCKED','DEPENDENCY')
        attempt=self._attempt(run,'exception_review',status['generation']); path=attempt/'review.json'
        write_new(path,dict(schema=1,run_id=run,classification_receipt_sha256=c.digest(receipts['glyph_classification']),snapshot=snap,scientific_status='UNADJUDICATED'))
        item=self._item(run,'exception_review','BLOCKED' if blocked else 'COMPLETED','REVIEW_PENDING' if blocked else 'NONE',ref(self.root,path)); item['counts']=counts
        return item

    def _align(self,run,status,manifest,receipts,inv,approval,models,mapping,snap,decisions):
        import alignment as a
        core.require(not snap['pending'] and not snap['deferred'] and not receipts['glyph_classification']['counts']['failed'],'Review dependency unresolved')
        review=c.load(c.artifact(self.root,receipts['exception_review']['artifact']))
        core.require(review['snapshot']==snap and review['classification_receipt_sha256']==c.digest(receipts['glyph_classification']),'Review receipt changed')
        if mapping is None: return self._item(run,'transcription_alignment','BLOCKED','DEPENDENCY')
        maps=load_page(c.artifact(self.root,mapping)); c.fields(maps,('schema','manuscript_sha256','sources'))
        core.require(maps['schema']==1 and maps['manuscript_sha256']==manifest['inputs']['manuscript']['sha256'],'Mapping source mismatch')
        core.require(set(maps['sources'])=={x['sha256'] for x in manifest['transcriptions']},'Mapping must account for every transcription')
        ri,si,ci=self._verify_classification(run,manifest,receipts,inv,approval,models)
        attempt=self._attempt(run,'transcription_alignment',status['generation']); reports=[]
        for n,source in enumerate(manifest['transcriptions']):
            self._boundary(run); self._admit(512*h.MIB,32*h.MIB)
            path=c.artifact(self.root,source); scheme,_,_=a.load_source(path,source['sha256']); entries=maps['sources'][source['sha256']]; core.require(type(entries) is dict,'Invalid locus map')
            observations=[]; seen=set(); loci=set()
            for rr,pp in zip(ri['pages'],ci['pages']):
                mp=c.artifact(self.root,rr['manifest']); m=load_page(mp); data=load_page(c.artifact(self.root,pp['outcomes'])); by={r['id']:[] for r in m['regions']}
                for row in data['rows']: by[row['region_id']].append(row)
                for region in m['regions']:
                    rid=region['id']; key=f'{rr["page"]}:{rid}'; entry=entries.get(key); seq=[]; false=0
                    crop=dict(path=(mp.parent.relative_to(self.root)/region['file']).as_posix(),sha256=region['sha256']); c.artifact(self.root,crop)
                    for row in sorted(by[rid],key=lambda r:r['box']):
                        label=None
                        if row['outcome']=='ACCEPTED': label=row['predictions'].get(scheme,{}).get('label')
                        else:
                            d=decisions[candidate_id(run,rr['page'],rid,crop,row['box'])]
                            if d['kind']=='false_positive': false+=1; continue
                            value=d['mappings'].get(scheme,{}); label=value.get('label') if value.get('state')=='mapped' else None
                        if label is not None:
                            try: a.units(label,scheme)
                            except ValueError: label=None
                        seq.append([label] if label else [])
                    obs=dict(region_id=key,locus=None,subtype=None,mapping_status='unconfirmed',scope=None,mapper=None,candidates=seq,excluded_false_positives=false,unresolved_compounds=0)
                    if entry is not None:
                        seen.add(key); c.fields(entry,('crop_sha256','locus','subtype','mapper')); core.require(entry['crop_sha256']==region['sha256'] and all(type(entry[k]) is str and entry[k].strip() for k in ('locus','subtype','mapper')),'Invalid physical mapping')
                        core.require(entry['locus'] not in loci,'Duplicate mapped locus'); loci.add(entry['locus'])
                        obs.update(locus=entry['locus'],subtype=entry['subtype'],mapper=entry['mapper'],scope='complete_locus',mapping_status='confirmed')
                    observations.append(obs)
            core.require(seen==set(entries),'Extra physical mapping entries')
            # No comparison is promoted to scientific truth, including zero-region scopes.
            obsfile=attempt/f'observations-{n}.json'; report=attempt/f'comparison-{n}.json'
            write_new(obsfile,dict(schema=1,scheme=scheme,source_sha256=source['sha256'],manifest_sha256=receipts['script_regions']['artifact']['sha256'],prediction_sha256=receipts['glyph_classification']['artifact']['sha256'],regions=observations))
            if observations: h.bounded_call(a.compare,path,source['sha256'],obsfile,report)
            else: write_new(report,dict(scientific_status='UNADJUDICATED',metrics=dict(COMPARED=0,UNRESOLVED=0),regions=[]))
            reports.append(dict(source_sha256=source['sha256'],observations=ref(self.root,obsfile),report=ref(self.root,report)))
        path=attempt/'index.json'; write_new(path,dict(schema=1,run_id=run,stage='transcription_alignment',scientific_status='UNADJUDICATED',review=receipts['exception_review']['artifact'],mapping=mapping,reports=reports))
        return self._item(run,'transcription_alignment','COMPLETED','NONE',ref(self.root,path))

    def _step(self,run):
        status=self.ledger.status(run); stage=status['next_stage']
        if stage in c.STAGES[:2]: return super()._step(run)
        # Revalidate all nested classification evidence before using the immutable queue.
        with self.ledger._tx() as conn:
            row=self.ledger._row(conn,'runs',run); manifest,receipts,_=self.ledger._validate(row)
        inv,models,approval,mapping=rec.inputs(self.root,manifest)
        if stage!='glyph_classification':
            counts=receipts['glyph_classification']['counts']; self._admit(512*h.MIB+min(counts['total'],500000)*1024,max(h.MIB,counts['abstained']*8192))
            self._verify_classification(run,manifest,receipts,inv,approval,models); self.queue.seed(run)
        token=self.ledger.claim(run); owned=True
        try:
            status=self.ledger.status(run); core.require(status['next_stage']==stage,'Stage changed before claim')
            manifest,receipts=self.ledger.context(run,token,self.identity); self._boundary(run)
            if stage=='glyph_classification': item=self._classify(run,token,status,manifest,receipts,inv,models,approval)
            else:
                with self.ledger._tx() as conn: snap,decisions=self.decisions.snapshot(conn,run)
                item=self._review(run,status,receipts,snap) if stage=='exception_review' else self._align(run,status,manifest,receipts,inv,approval,models,mapping,snap,decisions)
            self._boundary(run)
            try: control=self.ledger.record(run,token,item)
            except ValueError: self._boundary(run); raise
            owned=control=='READY'; return dict(run_id=run,stage=stage,control=control,reason=item['reason'])
        except StopRequested: return dict(run_id=run,stage=stage,control='STOP_REQUESTED')
        except (h.ResourceBlocked,MemoryError):
            control=self.ledger.pause_fault(run,token,stage,'RESOURCE_PRESSURE'); return dict(run_id=run,stage=stage,control=control,reason='RESOURCE_PRESSURE')
        except (ValueError,OSError,RuntimeError,KeyError,TypeError,ImportError):
            control=self.ledger.pause_fault(run,token,stage,'PROCESSING_OR_INTEGRITY_ERROR'); return dict(run_id=run,stage=stage,control=control,reason='PROCESSING_OR_INTEGRITY_ERROR')
        finally:
            if owned: self.ledger.release(run,token)

    def submit(self,decision):
        # A decision for a parked run must not acquire the scheduler-wide lock.
        # The ledger transaction and compare-and-swap revision fence mutations.
        run=decision['run_id']
        with self.ledger._tx() as conn:
            row=self.ledger._row(conn,'runs',run); manifest,receipts,_=self.ledger._validate(row)
        inv,models,approval,_=rec.inputs(self.root,manifest); self._verify_classification(run,manifest,receipts,inv,approval,models)
        return self.decisions.submit(decision,inv,self.identity)

    def resume(self,run):
        with self.ledger._tx() as conn:
            row=self.ledger._row(conn,'runs',run); _,receipts,_=self.ledger._validate(row)
            core.require(row['worker']==self.identity and row['token'] is None and row['control'] in ('PAUSED','BLOCKED'),'Run not resumable')
            if receipts['exception_review']['reason']=='REVIEW_PENDING':
                snap,_=self.decisions.snapshot(conn,run); core.require(not snap['pending'] and not snap['deferred'],'Review still pending')
            stage=self.ledger._next(receipts); core.require(stage is not None,'Run completed')
            core.require(not (receipts[stage]['reason']=='DEPENDENCY' and stage in ('exception_review','transcription_alignment')),'Frozen dependency missing; new authorized run required')
            conn.execute("UPDATE runs SET control='READY' WHERE id=?",(run,))

    def review_items(self,run,offset=0,limit=100):
        c.number(offset); c.number(limit,1000); core.require(limit>0,'Invalid limit')
        with self.ledger._tx() as conn:
            snap,latest=self.decisions.snapshot(conn,run); rows=[]; skipped=0; more=False
            for row in conn.execute('SELECT id,payload FROM vrs095_queue_items WHERE run_id=? ORDER BY position',(run,)):
                d=latest.get(row['id'])
                if d and d['kind'] in ('glyph','false_positive'): continue
                if skipped<offset: skipped+=1; continue
                if len(rows)==limit: more=True; break
                item=json.loads(row['payload']); c.artifact(self.root,item['crop']); item['revision']=d['expected_revision']+1 if d else 0; item['deferred']=bool(d); rows.append(item)
            return dict(snapshot=snap,items=rows,next_offset=offset+len(rows) if more else None)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('root',type=Path); sub=p.add_subparsers(dest='action',required=True)
    for name in ('register','register-plan','decide'):
        q=sub.add_parser(name); q.add_argument('path',type=Path)
    sub.add_parser('list'); sub.add_parser('once'); q=sub.add_parser('watch'); q.add_argument('--interval',type=int,default=5); q.add_argument('--plan',type=Path)
    for name in ('status','queue','pause','cancel','resume','recover'):
        q=sub.add_parser(name); q.add_argument('run')
        if name=='queue': q.add_argument('--offset',type=int,default=0); q.add_argument('--limit',type=int,default=100)
        if name=='recover': q.add_argument('generation',type=int); q.add_argument('--confirm-stopped',action='store_true')
    args=p.parse_args()
    try:
        app=Runtime(args.root); action=args.action
        if action in ('register','register-plan','decide'):
            value=c.load(inside(app.root,args.path)); result={'run_id':app.register(value)} if action=='register' else {'run_ids':app.register_plan(value)} if action=='register-plan' else app.submit(value)
        elif action=='list': result=app.ledger.registered()
        elif action=='once': result=app.sweep()
        elif action=='watch':
            h.positive(args.interval,'interval'); core.require(args.interval<=3600,'Interval too long')
            if args.plan: app.register_plan(c.load(inside(app.root,args.plan)))
            for sig in (signal.SIGINT,signal.SIGTERM): signal.signal(sig,lambda *_:app.stop.set())
            while not app.stop.is_set():
                for row in app.sweep(): print(json.dumps(row,sort_keys=True),flush=True)
                app.stop.wait(args.interval)
            return 0
        elif action=='status': result=app.ledger.status(args.run)
        elif action=='queue': result=app.review_items(args.run,args.offset,args.limit)
        else:
            if action=='recover': app.recover(args.run,args.generation,confirm_stopped=args.confirm_stopped)
            elif action=='resume': app.resume(args.run)
            else: app.ledger.request_stop(args.run,cancel=action=='cancel')
            result=app.ledger.status(args.run)
        print(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)); return 0
    except KeyboardInterrupt: return 130
    except (ValueError,OSError,RuntimeError,KeyError,TypeError,ImportError) as exc:
        print(json.dumps(dict(status='ERROR',reason=type(exc).__name__+': '+str(exc)))); return 1


if __name__=='__main__': raise SystemExit(main())

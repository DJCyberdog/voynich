"""Explicit real-source RC2-02g qualification; no scientific approval or data publication."""
import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
import glyphs as g
import vrs_contract as c
import vrs_core as core
import vrs_hybrid_page as hybrid
import vrs_segmentation as segmentation
import vrs_surface as surface
from vrs_coordinator import ref
from vrs_exceptions import load_page
from vrs_runtime import Runtime


@unittest.skipUnless(os.environ.get('VRS_RC2_PRIVATE_YALE_PDF'), 'Explicit pinned Yale PDF not supplied')
class HybridRuntimeQualification(unittest.TestCase):
    def test_native_segmentation_checkpoint_and_replay(self):
        start=time.perf_counter()
        pdf=Path(os.environ['VRS_RC2_PRIVATE_YALE_PDF']).resolve(strict=True)
        self.assertEqual(core.sha(pdf),surface.YALE_SHA256)
        with tempfile.TemporaryDirectory(prefix='vrs-hybrid-qualification-') as tmp:
            root=Path(tmp).resolve()
            shutil.copyfile(pdf,root/'source.pdf')
            source=ref(root,root/'source.pdf')
            def file(name,obj):
                p=root/name
                p.write_text(json.dumps(obj,sort_keys=True),encoding='utf-8')
                return ref(root,p)
            # Deliberately synthetic unapproved inventories; all actual candidates must abstain.
            alphabet=file('alphabet.json',dict(convention='Eva-',labels=['a','b']))
            model=file('model.json',dict(version=g.VERSION,labels=['a','b'],
                inventory_sha256=alphabet['sha256'],code_sha256=core.sha(g.__file__),
                thresholds=[.12,.005],prototypes=[[0.]*1024,[1.]*1024]))
            report=file('report.json',dict(model_sha256=model['sha256']))
            (root/'transcription.txt').write_text('synthetic qualification fixture\n',encoding='utf-8')
            manifest=dict(schema=1,module=c.MODULE,protocol=c.PROTOCOL,backend='cpu',seed=271126,
                run_nonce='7'*32,inputs=dict(manuscript=source,
                    groups=file('groups.json',{'1':'metadata','4':'f1r','12':'qualification-page-12','127':'qualification-page-127','214':'qualification-page-214'}),
                    references=file('references.json',dict(schema=1,inventories=[dict(alphabet=alphabet)])),
                    model=file('models.json',dict(schema=1,models=[dict(convention='Eva-',model=model,report=report)])),
                    recognition_policy=file('policy.json',dict(schema=1,approval=None,mapping=None))),
                transcriptions=[ref(root,root/'transcription.txt')])
            import sys
            from vrs_operations import Operations
            from vrs_desktop_api import page_evidence_summary
            ops=Operations(root);ops.save_settings(dict(ops.settings(),evidence_mode='hybrid'))
            ops.save_ops(dict(cpu_threads=2,ram_mib=0,disk_mib=0))
            file('run.json',manifest)
            run=ops.command(sys.executable,'register','run.json')['run_id']
            app=Runtime(root,hybrid_evidence=True)
            self.assertEqual(app.register(manifest),run)
            self.assertEqual(app.sweep(),[dict(run_id=run,stage='script_regions',control='READY',reason='NONE')])
            print('script_regions completed',round(time.perf_counter()-start,2),flush=True)
            checkpoint=app.ledger.checkpoint
            def stop_after_real_page(*args):
                checkpoint(*args)
                cp=app.ledger.status(run)['checkpoint']
                data=c.load(c.artifact(root,cp['artifact']))
                if len(data['pages'])==2:
                    app.stop.set()
            with patch.object(app.ledger,'checkpoint',side_effect=stop_after_real_page):
                result=app.sweep()
            self.assertEqual(result[0]['control'],'STOP_REQUESTED',result)
            status=app.ledger.status(run)
            self.assertFalse(status['locked'])
            self.assertEqual(status['next_stage'],'glyph_segmentation')
            cp=c.load(c.artifact(root,status['checkpoint']['artifact']))
            self.assertEqual([r['page'] for r in cp['pages']],[1,4])
            # The sidecar is an actual immutable attachment, not a new candidate ID.
            value=load_page(c.artifact(root,cp['pages'][1]['proposals']))
            side=c.artifact(root,value['hybrid_evidence'])
            side_bytes=side.read_bytes()
            self.assertEqual(side_bytes[:2],b'\x1f\x8b')
            # Deliberate test-only corruption in the disposable workspace.
            try:
                side.write_bytes(side_bytes+b'bad')
                with self.assertRaisesRegex(ValueError,'Artifact hash mismatch'):
                    c.artifact(root,value['hybrid_evidence'])
            finally:
                side.write_bytes(side_bytes)
            print('real-page stop, immutable attachment and corruption control PASS',flush=True)
            resumed=Runtime(root,hybrid_evidence=True)
            self.assertEqual(resumed.identity,app.identity)
            calls=[]; original=resumed._page
            def observe(run,stage,page,source,attempt):
                calls.append(page)
                return original(run,stage,page,source,attempt)
            with patch.object(resumed,'_page',side_effect=observe):
                result=resumed.sweep()
            self.assertEqual(result[0]['control'],'READY',result)
            self.assertEqual(calls,[12,127,214])
            status=resumed.ledger.status(run)
            self.assertEqual(status['next_stage'],'glyph_classification')
            self.assertIsNone(status['checkpoint'])
            data=load_page(c.artifact(root,status['receipts']['glyph_segmentation']['artifact']))
            self.assertEqual(data['pages'][:2],cp['pages'])
            self.assertEqual([r['page'] for r in data['pages']],[1,4,12,127,214])
            for row in data['pages']:
                replay_started=time.perf_counter()
                value=load_page(c.artifact(root,row['proposals']))
                mp=c.artifact(root,value['source']); m=load_page(mp)
                # Recompute the unchanged raster baseline from original receipt crops.
                legacy,lineage=segmentation.generate(m,lambda region:Image.open(mp.parent/region['file']))
                self.assertEqual(legacy,value['regions'])
                self.assertEqual(lineage,value['dedup'])
                evidence=hybrid.validate_ref(root,value,m,expected_source=source,required=True)
                self.assertEqual(evidence['comparison']['legacy'],row['candidates'])
                self.assertEqual(evidence['scientific_status'],'UNADJUDICATED')
                self.assertFalse(evidence['exclusion_authorized'])
                stored=c.artifact(root,value['hybrid_evidence']).stat().st_size
                decoded=len(hybrid.canonical(evidence))+1
                comparison=evidence['comparison']; expected=evidence['id']
                if row['page']!=1:
                    # Real persisted evidence, actual source pixels, same helper as desktop.
                    # No classification or queue insertion is performed in this test.
                    import fitz
                    import vrs_ink as ink
                    from vrs_desktop_api import vector_window
                    with fitz.open(root/'source.pdf') as doc:
                        image,meta=ink.native_page(doc[row['page']-1])
                    self.assertEqual(meta,evidence['native'])
                    summary=page_evidence_summary(evidence)
                    self.assertEqual(summary['total_pixels'],image.width*image.height)
                    self.assertEqual(summary['method_count'],6)
                    self.assertFalse(summary['exclusion_authorized'])
                    targets=[]
                    for region,proposal in zip(m['regions'],legacy):
                        ox,oy,_,_=region['pixel_box']
                        for l,t,r,b in proposal['boxes']:
                            target=ink.native_box(meta,[ox+l,oy+t,ox+r,oy+b])
                            if target and max(target[2]-target[0],target[3]-target[1])<=64:
                                targets.append(target)
                    self.assertTrue(targets,'No bounded real-source candidates')
                    checks=0;budget_refusals=0;hypotheses=0;clipped_previews=0;refusal_reasons={}
                    group=evidence['hybrid']['grouping']
                    samples=[targets[i] for i in sorted({0,len(targets)//2,len(targets)-1})]
                    for target in samples:
                        for mask in hybrid.MASKS:
                            data_mask=group['masks'][mask]
                            try:
                                preview,box,paths,count,layers=vector_window(image,target,data_mask['components'],data_mask['pairs'],group['alternatives']['by_mask'][mask])
                            except ValueError as exc:
                                # Bounds are explicit failure, not a pass or silent omission.
                                if 'budget exceeded' not in str(exc):raise
                                budget_refusals+=1;reason=str(exc);refusal_reasons[reason]=refusal_reasons.get(reason,0)+1;continue
                            self.assertEqual(preview.crop(box).tobytes(),image.crop(target).tobytes())
                            self.assertEqual(count,sum(max(q['box'][0],target[0])<min(q['box'][2],target[2]) and max(q['box'][1],target[1])<min(q['box'][3],target[3]) for q in data_mask['components']))
                            for path in paths+layers['skeleton']:
                                self.assertTrue(all(0<=x<=preview.width and 0<=y<=preview.height for x,y in path))
                            for x,y,degree in layers['nodes']:
                                self.assertTrue(0<=x<preview.width and 0<=y<preview.height and 0<=degree<=8)
                            for kind,options in layers['hypotheses'].items():
                                for ident,boxes in options:
                                    self.assertTrue(ident)
                                    self.assertTrue(all(0<=l<r<=preview.width and 0<=t<b<=preview.height for l,t,r,b in boxes))
                                hypotheses+=len(options)
                            clipped_previews+=int(any(layers.get('clipping',{}).values()))
                            checks+=1
                    print(json.dumps(dict(review_page=row['page'],preview_pass=checks,preview_budget_refusals=budget_refusals,refusal_reasons=refusal_reasons,clipped_previews=clipped_previews,hypotheses=hypotheses)),flush=True)
                    self.assertEqual(checks+budget_refusals,len(samples)*len(hybrid.MASKS))
                    self.assertGreater(checks,0,'All previews refused: '+str(refusal_reasons))
                del evidence
                self.assertEqual(hybrid.qualify_ref(root,value,m,expected_source=source),expected)
                print(json.dumps(dict(page=row['page'],legacy_candidates=row['candidates'],
                    stored_bytes=stored,decoded_bytes=decoded,comparison=comparison,
                    replay_seconds=round(time.perf_counter()-replay_started,2))),flush=True)
            # Continue through the actual managed portable worker and durable queue.
            # No manual ground truth and no approved recognition model are involved.
            expected_total=sum(r['candidates'] for r in data['pages'])
            self.assertGreater(expected_total,0)
            try:
                session=ops.start(sys.executable)
                self.assertEqual(session['evidence_mode'],'hybrid')
                deadline=time.monotonic()+600
                while time.monotonic()<deadline:
                    job=next(x for x in ops.jobs() if x['id']==run)
                    if job['control'] in ('BLOCKED','PAUSED','CANCELLED'):break
                    self.assertEqual(ops.session()['state'],'RUNNING')
                    time.sleep(.5)
                self.assertEqual((job['control'],job['stage'],job['reason']),('BLOCKED','exception_review','REVIEW_PENDING'),job)
                q=ops.review(run,limit=1)
                self.assertEqual(q['snapshot']['pending'],expected_total)
                self.assertEqual(q['snapshot']['resolved'],0)
                self.assertEqual(q['snapshot']['deferred'],0)
                counts=app.ledger.status(run)['receipts']['glyph_classification']['counts']
                self.assertEqual(counts,dict(total=expected_total,accepted=0,abstained=expected_total,failed=0))
                # Actual persisted queue identity + source/crop replay + native sidecar.
                # Use predetermined sampled page offsets, not cherry-picked successful views.
                offset=0;checked=0
                for row in data['pages']:
                    if row['candidates']:
                        sample=ops.review(run,offset=offset,limit=1)['items'][0]
                        self.assertEqual(sample['page'],row['page'])
                        for mask in hybrid.MASKS:
                            result=ops.vector_context(sample,mask)
                            self.assertEqual(result[4]['page_evidence']['page'],row['page'])
                            checked+=1
                    offset+=row['candidates']
                self.assertEqual(checked,3*sum(bool(row['candidates']) for row in data['pages']))
                item=q['items'][0]
                # A synthetic deferred disposition is a transport test, not scientific annotation.
                draft=ops.stage_decision(item,q['snapshot'],q['inventory'],'qualification-fixture','deferred',{})
                ack=ops.submit_draft(sys.executable,draft)
                self.assertEqual(ack['pending'],expected_total-1)
                self.assertEqual(ack['deferred'],1)
                self.assertEqual(ack['resolved'],0)
                self.assertEqual(app.ledger.outbox(),[])
                print(json.dumps(dict(managed_review_candidates=expected_total,accepted=0,desktop_api_previews=checked,deferred_transport_test=1,scientific_status='UNADJUDICATED')),flush=True)
            finally:
                if ops.session()['state'] in ('RUNNING','STOP_REQUESTED'):ops.stop()
                deadline=time.monotonic()+30
                while ops.session()['state']=='STOP_REQUESTED' and time.monotonic()<deadline:time.sleep(.2)
                self.assertEqual(ops.session()['state'],'STOPPED')
            print('elapsed_seconds',round(time.perf_counter()-start,2),flush=True)
            # Linux reports peak process RSS in KiB; no cross-platform assumption.
            if os.name!='nt':
                import resource
                print('peak_rss_platform_units',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,flush=True)


if __name__=='__main__':unittest.main()

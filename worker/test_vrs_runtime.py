import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz
import glyphs as g
import regions
from PIL import Image
import vrs_contract as c
import vrs_recognition as rec
from vrs_coordinator import ref
from vrs_runtime import Runtime
from vrs_core import sha


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.root=Path(tmp.name)
        with fitz.open() as doc:
            page=doc.new_page(width=90,height=90)
            page.draw_rect(fitz.Rect(1,1,2,2),color=None,fill=(0,0,0))
            doc.new_page(width=90,height=90); doc.save(self.root/'source.pdf')
        groups=self.file('groups.json',{'1':'leaf-a'}); self.source=ref(self.root,self.root/'source.pdf')
        # Test-only geometry precomputation. No actual manuscript or approval evidence.
        dest=self.root/'fixture-proposals'; regions.propose(self.root/'source.pdf',self.source['sha256'],self.root/'groups.json',dest,pages=[1]); m=json.loads((dest/'manifest.json').read_text())
        self.eligible=[]; feature=None
        for region in m['regions']:
            with Image.open(dest/region['file']) as im:
                for box in g.boxes(im):
                    self.eligible.append(dict(page=1,region_id=region['id'],crop_sha256=region['sha256'],box=box))
                    if feature is None: feature=g.feature(im.crop(box)).tolist()
        self.assertTrue(self.eligible)
        alphabets=[]; models=[]
        for name,labels in [('Eva-',['a','b']),('STA1',['A1','B1'])]:
            inv=self.file(f'{name}-alphabet.json',dict(convention=name,labels=labels)); alphabets.append(dict(alphabet=inv))
            model=self.file(f'{name}-model.json',dict(version=g.VERSION,labels=labels,inventory_sha256=inv['sha256'],code_sha256=sha(g.__file__),thresholds=[.12,.005],prototypes=[feature,[1-x for x in feature]]))
            report=self.file(f'{name}-report.json',dict(model_sha256=model['sha256'])); models.append(dict(convention=name,model=model,report=report))
        self.refs=self.file('references.json',dict(schema=1,inventories=alphabets)); self.models=self.file('models.json',dict(schema=1,models=models))
        (self.root/'eva.txt').write_text('#=IVTFF Eva- 2.0 M 1\n<f1r.1,@P0> a\n',encoding='utf-8'); (self.root/'sta.txt').write_text('#=IVTFF STA1 2.0 M 1\n<f1r.1,@P0> A1\n',encoding='utf-8')
        trans=[ref(self.root,self.root/x) for x in ('eva.txt','sta.txt')]; first=self.eligible[0]
        self.mapping=self.file('map.json',dict(schema=1,manuscript_sha256=self.source['sha256'],sources={t['sha256']:{f"1:{first['region_id']}":dict(crop_sha256=first['crop_sha256'],locus='f1r.1',subtype='@P0',mapper='synthetic fixture')} for t in trans}))
        self.m=dict(schema=1,module=c.MODULE,protocol=c.PROTOCOL,backend='cpu',seed=7,run_nonce='1'*32,inputs=dict(manuscript=self.source,groups=groups,references=self.refs,model=self.models,recognition_policy=self.file('policy.json',dict(schema=1,approval=None,mapping=self.mapping))),transcriptions=trans)
        self.app=Runtime(self.root)

    def file(self,name,obj):
        p=self.root/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,sort_keys=True),encoding='utf-8'); return ref(self.root,p)

    def status(self,run): return self.app.ledger.status(run)

    def run_to_review(self,manifest=None):
        run=self.app.register(manifest or self.m)
        for stage in c.STAGES[:4]:
            result=self.app.sweep()[0]; self.assertEqual(result['stage'],stage); self.assertIn(result['control'],('READY','BLOCKED'),result)
        return run

    def decision(self,run,item,kind='glyph',revision=None):
        return dict(schema=1,run_id=run,queue_sha256=self.app.review_items(run)['snapshot']['queue_sha256'],candidate_id=item['id'],expected_revision=item['revision'] if revision is None else revision,reviewer='local fixture',kind=kind,mappings={'Eva-':dict(state='mapped',label='a'),'STA1':dict(state='absent',label=None)} if kind=='glyph' else {})

    def approve(self, errors=False, trust=True):
        binding=dict(model_sha256=self.models['sha256'],references_sha256=self.refs['sha256'],classifier_sha256=sha(g.__file__),backend='cpu')
        cal=self.file('cal.json',dict(schema=1,**binding,train_groups=['train'],holdout_groups=['test'],reviewers=['fixture-1','fixture-2'],rows=[dict(id='fixture',convention=n,group='test',truth=b if errors else a,prediction=a,distance=0.,margin=.9) for n,a,b in [('Eva-','a','b'),('STA1','A1','B1')]]))
        geo=self.file('geo.json',dict(schema=1,manuscript_sha256=self.source['sha256'],occurrences=[self.eligible[0]]))
        approval=self.file('approval.json',dict(schema=1,**binding,calibration=cal,geometry=geo,limits={n:dict(distance=.12,margin=.005,minimum_accepted=1,maximum_errors=0) for n in ('Eva-','STA1')}))
        if trust: self.file('config/vrs096-approved.json',dict(schema=1,approvals=[approval['sha256']]))
        return dict(self.m,inputs=dict(self.m['inputs'],recognition_policy=self.file('approved-policy.json',dict(schema=1,approval=approval,mapping=self.mapping))))

    def test_real_end_to_end_no_calibration_and_correction_alignment(self):
        run=self.run_to_review(); st=self.status(run); counts=st['receipts']['glyph_classification']['counts']; self.assertEqual(counts['accepted'],0); self.assertGreater(counts['abstained'],0)
        page=c.load(c.artifact(self.root,st['receipts']['glyph_classification']['artifact']))['pages'][0]
        data=rec.load_page(c.artifact(self.root,page['outcomes'])); self.assertTrue(all(set(r['predictions'])=={'Eva-','STA1'} and r['uncertainty'] is None for r in data['rows']))
        original=st['receipts']['glyph_classification']['artifact']; q=self.app.review_items(run,limit=1000); self.assertEqual(len(q['items']),counts['abstained'])
        for i,item in enumerate(q['items']):
            d=self.decision(run,item,kind='glyph' if i==0 else 'false_positive'); snap=self.app.submit(d)
            if i<len(q['items'])-1: self.assertEqual(self.status(run)['control'],'BLOCKED')
        self.assertEqual(snap['resolved'],counts['abstained']); self.assertEqual(self.status(run)['control'],'READY'); self.assertEqual(self.app.submit(d),snap)
        reopened=Runtime(self.root); self.assertEqual(reopened.sweep()[0]['stage'],'exception_review'); self.assertEqual(reopened.sweep()[0]['control'],'COMPLETED')
        st=self.status(run); self.assertEqual(st['receipts']['glyph_classification']['artifact'],original)
        result=c.load(c.artifact(self.root,st['receipts']['transcription_alignment']['artifact'])); self.assertEqual(result['scientific_status'],'UNADJUDICATED'); self.assertEqual(len(result['reports']),2)
        for row in result['reports']:
            report=c.load(c.artifact(self.root,row['report'])); self.assertEqual(report['metrics']['unique_compared_loci'],1)
        self.assertEqual(self.app.ledger.outbox(),[]); self.assertEqual(reopened.submit(d),snap)

    def test_defer_revision_stale_and_paused_wakeup(self):
        run=self.run_to_review(); q=self.app.review_items(run,limit=1000); item=q['items'][0]; d=self.decision(run,item,'compound'); self.app.submit(d); self.assertEqual(self.app.submit(d)['deferred'],1)
        conflict=dict(d,kind='deferred')
        with self.assertRaisesRegex(ValueError,'Stale'): self.app.submit(conflict)
        self.app.ledger.request_stop(run); self.assertEqual(self.status(run)['control'],'PAUSED')
        for item in self.app.review_items(run,limit=1000)['items']: self.app.submit(self.decision(run,item,'false_positive'))
        self.assertEqual(self.status(run)['control'],'PAUSED'); self.app.resume(run); self.assertEqual(self.status(run)['control'],'READY')
        self.assertEqual(self.app.sweep()[0]['stage'],'exception_review')

    def test_approved_policy_accepts_only_certified_occurrence(self):
        run=self.run_to_review(self.approve()); counts=self.status(run)['receipts']['glyph_classification']['counts']
        self.assertEqual(counts['accepted'],1); self.assertEqual(counts['abstained'],counts['total']-1)
        self.assertEqual(self.app.review_items(run)['snapshot']['pending'],counts['abstained'])

    def test_unapproved_or_failed_calibration_denied(self):
        with self.assertRaises((ValueError,OSError)): self.app.register(self.approve(trust=False))
        with self.assertRaisesRegex(ValueError,'Calibration gate'): self.app.register(self.approve(errors=True))
        self.assertEqual(self.app.ledger.registered(),[])

    def test_missing_inventory_model_and_mapping_dependency(self):
        models=json.loads((self.root/'models.json').read_text()); models['models'].pop(); m=dict(self.m,inputs=dict(self.m['inputs'],model=self.file('one-model.json',models),recognition_policy=self.file('no-map.json',dict(schema=1,approval=None,mapping=None))))
        run=self.run_to_review(m); items=self.app.review_items(run,limit=1000)['items']; self.assertTrue(items); self.assertEqual({x['reason'] for x in items},{'UNSUPPORTED_INVENTORY'})
        for item in items: self.app.submit(self.decision(run,item,'false_positive'))
        self.app.sweep(); self.assertEqual(self.app.sweep()[0]['reason'],'DEPENDENCY'); self.assertEqual(self.status(run)['control'],'BLOCKED')
        with self.assertRaisesRegex(ValueError,'Frozen dependency'): self.app.resume(run)

    def test_invalid_decision_wrong_scope_and_tamper(self):
        run=self.run_to_review(); item=self.app.review_items(run)['items'][0]; d=self.decision(run,item)
        with self.assertRaises(ValueError): self.app.submit(dict(d,queue_sha256='a'*64))
        with self.assertRaises(ValueError): self.app.submit(dict(d,mappings={'Eva-':dict(state='mapped',label='z')}))
        with self.assertRaises(ValueError): self.app.submit(dict(d,candidate_id='f'*64))
        (self.root/item['crop']['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError): self.app.submit(d)

    def test_classifier_checkpoint_process_death(self):
        m=dict(self.m,inputs=dict(self.m['inputs'],groups=self.file('both.json',{'1':'leaf-a','2':'leaf-b'}),recognition_policy=self.file('no-map.json',dict(schema=1,approval=None,mapping=None))))
        run=self.app.register(m); self.app.sweep(); self.app.sweep()
        code="import os,sys; from vrs_runtime import Runtime; a=Runtime(sys.argv[1]); old=a.ledger.checkpoint; a.ledger.checkpoint=lambda *x:(old(*x),os._exit(77)); a.sweep()"
        proc=subprocess.run([sys.executable,'-c',code,str(self.root)],cwd=Path(__file__).parent,timeout=30); self.assertEqual(proc.returncode,77)
        status=self.status(run); cp=c.load(c.artifact(self.root,status['checkpoint']['artifact'])); self.assertEqual([r['page'] for r in cp['pages']],[1]); self.app.recover(run,status['generation'],confirm_stopped=True)
        other=Runtime(self.root); original=other._page_outcome; calls=[]
        def observe(run,rr,*args): calls.append(rr['page']); return original(run,rr,*args)
        with patch.object(other,'_page_outcome',side_effect=observe): self.assertEqual(other.sweep()[0]['control'],'READY')
        self.assertEqual(calls,[2]); self.assertEqual(self.status(run)['next_stage'],'exception_review')

    def test_waiting_run_independent_blank_and_cancel(self):
        a=self.run_to_review(); m=dict(self.m,run_nonce='2'*32,inputs=dict(self.m['inputs'],groups=self.file('blank.json',{'2':'leaf-b'}),recognition_policy=self.file('blank-policy.json',dict(schema=1,approval=None,mapping=None))))
        b=self.app.register(m); generation=self.status(a)['generation']
        for stage in c.STAGES:
            self.assertEqual(self.app.sweep()[0]['stage'],stage)
        self.assertEqual(self.status(b)['receipts']['glyph_classification']['counts']['total'],0)
        self.assertEqual(self.status(a)['generation'],generation)
        item=self.app.review_items(a)['items'][0]; self.app.ledger.request_stop(a,cancel=True)
        with self.assertRaisesRegex(ValueError,'not waiting'): self.app.submit(self.decision(a,item,'false_positive'))

    def test_approved_policy_revocation_blocks_execution(self):
        m=self.approve(); run=self.app.register(m); self.app.sweep(); self.app.sweep()
        self.file('config/vrs096-approved.json',dict(schema=1,approvals=[]))
        self.assertEqual(self.app.sweep()[0]['control'],'ERROR'); self.assertEqual(self.status(run)['control'],'PAUSED')
        self.assertIsNone(self.status(run)['receipts']['glyph_classification']['counts'])

    def test_local_concurrent_conflicting_decisions(self):
        from concurrent.futures import ThreadPoolExecutor
        run=self.run_to_review(); item=self.app.review_items(run)['items'][0]; d=self.decision(run,item,'compound')
        def submit(value):
            try: return self.app.submit(value)
            except (ValueError,OSError): return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(submit,[d,dict(d,kind='deferred')]))
        self.assertEqual(sum(r is not None for r in results),1)
        self.assertEqual(self.app.review_items(run)['snapshot']['deferred'],1)
        self.assertEqual(sum(r['kind']=='REVIEW_DECISION' for r in self.app.ledger.history(run)),1)

    def test_review_submission_while_unrelated_scheduler_lock_held(self):
        from vrs_coordinator import scheduler_lock
        run=self.run_to_review(); item=self.app.review_items(run)['items'][0]
        with scheduler_lock(self.app.lock):
            other=Runtime(self.root)
            snap=other.submit(self.decision(run,item,'false_positive'))
        self.assertEqual(snap['resolved'],1)
        self.assertEqual(self.status(run)['control'],'BLOCKED')


    def test_cuda_explicit_unavailable_never_falls_back(self):
        m=dict(self.m,backend='cuda')
        with patch('vrs_runtime.h.snapshot',return_value={'gpu':{'ok':False}}):
            with self.assertRaisesRegex(RuntimeError,'no CPU fallback'):self.app.register(m)
            entry=self.file('cuda-run.json',m)
            with self.assertRaisesRegex(RuntimeError,'no CPU fallback'):self.app.register_plan({'schema':1,'manifests':[entry]})
        self.assertEqual(self.app.ledger.registered(),[])

    def test_cuda_rejects_cpu_calibration(self):
        m=dict(self.approve(),backend='cuda')
        with self.assertRaisesRegex(ValueError,'CPU calibration'):self.app.register(m)
        self.assertEqual(self.app.ledger.registered(),[])

    def test_cuda_candidate_parity_guards(self):
        inv={'Eva-':(['a','b'],'0'*64)}
        a=[{'Eva-':dict(label='a',distance=.1,margin=.02)}]
        b=copy.deepcopy(a)
        b[0]['Eva-']['distance']+=.0000001
        self.assertEqual(rec.compare_candidate(a,b,inv),b)
        for change in (dict(label='b'),dict(distance=.11),dict(margin=.01)):
            b=copy.deepcopy(a);b[0]['Eva-'].update(change)
            with self.assertRaises(ValueError):rec.compare_candidate(a,b,inv)
        a[0]['Eva-']['distance']=.12
        b=copy.deepcopy(a);b[0]['Eva-']['distance']+=.0000001
        with self.assertRaisesRegex(ValueError,'routing parity'):rec.compare_candidate(a,b,inv)

    def test_cuda_binding_rejects_missing_and_distinguishes_devices(self):
        import vrs_hardware as h
        gpu=dict(ok=True,index=0,device_uuid='GPU-12345678-1234-1234-1234-123456789abc',
                 name='fixture',capability=[12,0],total=16*h.GIB,free=4*h.GIB,torch='fixture',cuda_build='12.8')
        a=h.cuda_binding({'gpu':gpu})
        self.assertEqual(a,h.cuda_binding({'gpu':dict(gpu,free=1)}))
        self.assertNotEqual(a,h.cuda_binding({'gpu':dict(gpu,device_uuid='12345678-1234-1234-1234-123456789abd')}))
        self.assertNotEqual(a,h.cuda_binding({'gpu':dict(gpu,torch='different')}))
        with self.assertRaises(h.ResourceBlocked):h.cuda_binding({'gpu':dict(gpu,device_uuid='')})

    def test_cuda_checkpoint_device_change_guard(self):
        # No GPU claim: inject an existing immutable checkpoint and a different binding.
        m=dict(self.m,backend='cuda')
        with patch.object(self.app,'_backend',return_value='cuda'):
            run=self.app.register(m)
        self.app.sweep(); self.app.sweep()
        token=self.app.ledger.claim(run)
        cp=self.file('mock-cuda-checkpoint.json',dict(schema=1,worker=self.app.identity,
            run_id=run,stage='glyph_classification',pages=[],cuda_binding='1'*64))
        self.app.ledger.checkpoint(run,token,'glyph_classification',cp)
        self.app.ledger.release(run,token)
        with patch.object(self.app,'_backend',return_value='cuda'),patch('vrs_runtime.h.cuda_binding',return_value='2'*64),patch.object(self.app,'_page_outcome') as compute:
            result=self.app.sweep()[0]
            compute.assert_not_called()
        self.assertEqual(result['reason'],'PROCESSING_OR_INTEGRITY_ERROR')
        self.assertEqual(self.status(run)['control'],'PAUSED')
        self.assertEqual(self.status(run)['checkpoint']['artifact'],cp)

    def test_native_cuda_checkpoint_resume(self):
        if os.environ.get('VRS_NATIVE_CUDA_TEST')!='1':
            self.skipTest('Explicit native CUDA qualification required')
        m=dict(self.m,backend='cuda',inputs=dict(self.m['inputs'],
            groups=self.file('cuda-both.json',{'1':'leaf-a','2':'leaf-b'}),
            recognition_policy=self.file('cuda-no-map.json',dict(schema=1,approval=None,mapping=None))))
        run=self.app.register(m);self.app.sweep();self.app.sweep()
        code="import os,sys; from vrs_runtime import Runtime; a=Runtime(sys.argv[1]); old=a.ledger.checkpoint; a.ledger.checkpoint=lambda *x:(old(*x),os._exit(77)); a.sweep()"
        proc=subprocess.run([sys.executable,'-c',code,str(self.root)],cwd=Path(__file__).parent,timeout=120)
        self.assertEqual(proc.returncode,77)
        status=self.status(run);cp=c.load(c.artifact(self.root,status['checkpoint']['artifact']))
        self.assertEqual([r['page'] for r in cp['pages']],[1]);c.digest_ok(cp['cuda_binding'])
        self.app.recover(run,status['generation'],confirm_stopped=True)
        other=Runtime(self.root);original=other._page_outcome;calls=[]
        def observe(run,rr,*args):
            calls.append(rr['page']);return original(run,rr,*args)
        with patch.object(other,'_page_outcome',side_effect=observe):
            self.assertEqual(other.sweep()[0]['control'],'READY')
        self.assertEqual(calls,[2])
        index=c.load(c.artifact(self.root,self.status(run)['receipts']['glyph_classification']['artifact']))
        self.assertEqual(index['cuda_binding'],cp['cuda_binding'])
        self.assertEqual(index['pages'][0],cp['pages'][0])

    def test_native_cuda_candidate(self):
        if os.environ.get('VRS_NATIVE_CUDA_TEST')!='1':
            self.skipTest('Explicit native CUDA qualification required')
        import torch
        self.assertTrue(torch.cuda.is_available(),'CUDA required, no skip or CPU fallback')
        m=dict(self.m,backend='cuda')
        run=self.run_to_review(m)
        st=self.status(run)
        self.assertEqual(st['receipts']['glyph_classification']['counts']['accepted'],0)
        self.assertGreater(st['receipts']['glyph_classification']['counts']['abstained'],0)
        with self.app.ledger._tx() as conn:
            row=self.app.ledger._row(conn,'runs',run)
            self.assertEqual(row['backend'],'cuda')
        index=c.load(c.artifact(self.root,st['receipts']['glyph_classification']['artifact']))
        c.digest_ok(index['cuda_binding'])
        q=self.app.review_items(run,limit=1000)
        for item in q['items']:self.app.submit(self.decision(run,item,'false_positive'))
        self.assertEqual(self.app.sweep()[0]['stage'],'exception_review')
        self.assertEqual(self.app.sweep()[0]['control'],'COMPLETED')
        self.assertEqual(self.app.ledger.outbox(),[])


if __name__=='__main__': unittest.main()

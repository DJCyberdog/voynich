import copy
import json
import unittest
from pathlib import Path

import fitz
from PIL import Image, ImageDraw
import glyphs as g
import vrs_contract as c
import vrs_learning as learn
from vrs_coordinator import ref
from vrs_exceptions import load_page
from vrs_core import sha
import test_vrs_runtime as fixture_runtime


class LearningTests(unittest.TestCase):
    def setUp(self):
        fixture=fixture_runtime.RuntimeTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        self.f=fixture; self.root=fixture.root; self.app=fixture.app
        with fitz.open(self.root/'source.pdf') as doc:
            doc.new_page(width=90,height=90); doc.save(self.root/'three.pdf')
        source=ref(self.root,self.root/'three.pdf'); m=dict(fixture.m,inputs=dict(fixture.m['inputs'],manuscript=source,recognition_policy=fixture.file('learn-policy.json',dict(schema=1,approval=None,mapping=None))))
        self.run=fixture.run_to_review(m); q=self.app.review_items(self.run,limit=1000); item=q['items'][0]; self.item=item
        self.app.submit(fixture.decision(self.run,item))
        data=learn.corrections(self.root,self.run,'Eva-'); self.assertEqual(len(data['items']),1)
        self.assertEqual(learn.corrections(self.root,self.run,'STA1')['items'],[])
        status=self.app.ledger.status(self.run); ri=c.load(c.artifact(self.root,status['receipts']['script_regions']['artifact'])); mp=c.artifact(self.root,ri['pages'][0]['manifest']); raw=c.load(mp); region=next(r for r in raw['regions'] if r['id']==item['region_id'])
        # Curated subset of actual proposal plus independent synthetic labeled crops.
        # All fixtures are declared synthetic; no real manuscript or human evidence.
        subset=fixture.file(str((mp.parent/'selected.json').relative_to(self.root)),dict(source_sha256=source['sha256'],regions=[region]))
        with Image.open(c.artifact(self.root,item['crop'])) as im:
            fp=__import__('hashlib').sha256(g.feature(im.crop(item['box'])).tobytes()).hexdigest(); base=im.crop(item['box']).convert('L'); base=base.resize((base.width*8,base.height*8)); a=g.feature(im.crop(item['box'])).tolist()
        # Complement class; perturb distinct pixels in each split, avoid duplicate features.
        rows=[dict(page=1,region_id=item['region_id'],box=item['box'],votes=['a','a'])]; regions=[]; b=None
        for p,leaf,side in [(1,'leaf-a','train'),(2,'leaf-b','calibration'),(3,'leaf-c','holdout')]:
            for label in ('a','b'):
                if p==1 and label=='a': continue
                im=base.copy()
                if label=='b': im=im.point(lambda v:255-v)
                im.putpixel((p%im.width,0),127+p); name=f'fixture-{p}-{label}.png'; path=self.root/name; im.save(path)
                if p==1: b=g.feature(im).tolist()
                regions.append(dict(page=p,id=name,group=leaf,file=name,sha256=sha(path)))
                rows.append(dict(page=p,region_id=name,box=[0,0,im.width,im.height],votes=[label,label]))
        # Add a genuine unresolved label row to the holdout denominator.
        im=Image.new('L',(32,32),255); ImageDraw.Draw(im).line((0,0,31,31),fill=0,width=2); name='unknown.png'; im.save(self.root/name); regions.append(dict(page=3,id=name,group='leaf-c',file=name,sha256=sha(self.root/name))); rows.append(dict(page=3,region_id=name,box=[0,0,32,32],votes=['unknown','unknown']))
        extra=fixture.file('curated.json',dict(source_sha256=source['sha256'],regions=regions))
        alphabet=ref(self.root,self.root/'Eva--alphabet.json')
        baseline=fixture.file('baseline.json',dict(version=g.VERSION,labels=['a','b'],inventory_sha256=alphabet['sha256'],code_sha256=sha(g.__file__),thresholds=[.12,.005],prototypes=[[min(1,x+.01) for x in a],b]))
        self.plan=dict(schema=1,manuscript=source,alphabet=alphabet,leaf_map=fixture.file('leaves.json',dict(schema=1,manuscript_sha256=source['sha256'],pages={str(p):dict(leaf=leaf,split=side) for p,leaf,side in [(1,'leaf-a','train'),(2,'leaf-b','calibration'),(3,'leaf-c','holdout')]},curators=['curator1','curator2'])),regions=[subset,extra],annotations=fixture.file('annotations.json',dict(schema=1,reviewers=['independent1','independent2'],blind_declared=True,rows=rows)),corrections=[dict(run_id=self.run,decision_sha256=data['decision_sha256'],candidate_ids=[item['id']])],limits=dict(distance=.05,margin=.005,min_accepted=2,max_risk=0,min_coverage=2/3),baseline=baseline,baseline_report=fixture.file('baseline-report.json',dict(model_sha256=baseline['sha256'])),baseline_provenance=fixture.file('baseline-provenance.json',dict(schema=1,model_sha256=baseline['sha256'],manuscript_sha256=source['sha256'],training_leaves=['leaf-a'],training_feature_sha256=[fp],curator='fixture')))

    def approve(self,plan=None): self.f.file('config/vrs120-training.json',dict(schema=1,plans=[c.digest(plan or self.plan)]))

    def alter(self,role,fn):
        p=copy.deepcopy(self.plan); v=learn.read(self.root,p[role]); fn(v); p[role]=self.f.file('altered-'+role+'.json',v); return p

    def test_actual_correction_frozen_and_one_shot_replay(self):
        audit=learn.audit_run(self.root,self.run); self.assertEqual(audit['receipts'],self.app.ledger.status(self.run)['receipts']); self.assertEqual(audit['review']['resolved'],1)
        frozen=learn.freeze(self.root,self.plan); self.assertEqual(sum(r['correction'] for r in frozen['rows']),1)
        with self.assertRaises((ValueError,OSError)): learn.evaluate(self.root,self.plan)
        self.approve(); rr=learn.evaluate(self.root,self.plan); report=learn.read(self.root,rr); self.assertEqual(report['gate'],'ELIGIBLE_FOR_MANUAL_REVIEW',report['partitions'])
        self.assertEqual(report['partitions']['holdout']['candidate']['eligible'],3); self.assertEqual(report['partitions']['holdout']['candidate']['accepted'],2)
        self.assertEqual(learn.compare(self.root,self.plan,rr)['status'],'PASS')
        with self.assertRaises(FileExistsError): learn.evaluate(self.root,self.plan)
        with self.assertRaises((ValueError,OSError)): learn.selection(self.root,rr,'select')
        self.f.file('config/vrs120-approved.json',dict(schema=1,reports=[rr['sha256']]))
        selected=learn.selection(self.root,rr,'select'); self.assertEqual(selected['bundle_entry']['model'],report['model']); self.assertEqual(learn.selection(self.root,rr,'rollback')['bundle_entry']['report'],self.plan['baseline_report'])
        self.assertEqual(self.app.ledger.status(self.run)['receipts'],audit['receipts']); self.assertFalse((self.root/'config/vrs096-approved.json').exists())

    def test_physical_leaf_and_baseline_leakage(self):
        with self.assertRaisesRegex(ValueError,'Physical-leaf leakage'): learn.freeze(self.root,self.alter('leaf_map',lambda v:v['pages']['2'].update(leaf='leaf-a')))
        with self.assertRaisesRegex(ValueError,'Baseline training leaf'): learn.freeze(self.root,self.alter('baseline_provenance',lambda v:v.update(training_leaves=['leaf-b'])))
        frozen=learn.freeze(self.root,self.plan); fp=next(r['feature_sha256'] for r in frozen['rows'] if r['split']=='holdout')
        with self.assertRaisesRegex(ValueError,'Baseline feature leakage'): learn.freeze(self.root,self.alter('baseline_provenance',lambda v:v.update(training_feature_sha256=[fp])))

    def test_disagreement_stale_and_no_self_label(self):
        with self.assertRaisesRegex(ValueError,'independent train-only'): learn.freeze(self.root,self.alter('annotations',lambda v:v['rows'][0].update(votes=['a','b'])))
        with self.assertRaisesRegex(ValueError,'independent train-only'): learn.freeze(self.root,self.alter('annotations',lambda v:v.update(reviewers=['local fixture','independent2'])))
        p=copy.deepcopy(self.plan); p['corrections'][0]['decision_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'provenance changed'): learn.freeze(self.root,p)

    def test_failed_calibration_no_holdout_and_no_selection(self):
        p=copy.deepcopy(self.plan); p['limits']['min_accepted']=100; self.approve(p); r=learn.evaluate(self.root,p); report=learn.read(self.root,r)
        self.assertEqual(report['gate'],'NOT_MET'); self.assertEqual(set(report['partitions']),{'calibration'})
        with self.assertRaisesRegex(ValueError,'not eligible'): learn.selection(self.root,r,'select')
        self.approve()
        with self.assertRaises(FileExistsError): learn.evaluate(self.root,self.plan)

    def test_duplicate_features_and_tamper(self):
        def duplicate(v):
            v['regions'][1]['file']=v['regions'][0]['file']; v['regions'][1]['sha256']=v['regions'][0]['sha256']
        p=copy.deepcopy(self.plan); v=learn.read(self.root,p['regions'][1]); duplicate(v); p['regions'][1]=self.f.file('duplicated.json',v)
        with self.assertRaisesRegex(ValueError,'crop leakage'): learn.freeze(self.root,p)
        self.approve(); r=learn.evaluate(self.root,self.plan); model=learn.read(self.root,r)['model']; (self.root/model['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError,'hash mismatch'): learn.compare(self.root,self.plan,r)

    def test_native_cuda_training_and_cpu_replay(self):
        import os
        if os.environ.get('VRS_NATIVE_CUDA_TEST')!='1':
            self.skipTest('Explicit native CUDA training qualification required')
        import torch
        import vrs_hardware as h
        self.assertTrue(torch.cuda.is_available(),'CUDA required')
        binding=h.cuda_binding(dict(gpu=h.cuda_probe(torch,0)))
        self.approve()
        original=self.app.ledger.status(self.run)['receipts']
        torch.cuda.reset_peak_memory_stats(0)
        import time
        start=time.perf_counter()
        rr=learn.evaluate(self.root,self.plan,'cuda')
        torch.cuda.synchronize(0)
        seconds=time.perf_counter()-start
        peak=torch.cuda.max_memory_allocated(0)
        report=learn.read(self.root,rr)
        self.assertEqual(report['backend']['device'],'cuda')
        self.assertEqual(report['gate'],'ELIGIBLE_FOR_MANUAL_REVIEW')
        self.assertEqual(report['partitions']['holdout']['candidate']['eligible'],3)
        self.assertGreater(peak,0)
        for backend in ('cuda','cpu'):
            result=learn.compare(self.root,self.plan,rr,backend)
            self.assertEqual(result['status'],'PASS',result)
            self.assertGreater(result['rows'],0)
        self.assertEqual(binding,h.cuda_binding(dict(gpu=h.cuda_probe(torch,0))))
        self.assertEqual(original,self.app.ledger.status(self.run)['receipts'])
        self.assertFalse((self.root/'config/vrs120-approved.json').exists())
        print(json.dumps(dict(scope='SYNTHETIC_NATIVE_TRAINING_ONLY',cuda_binding=binding,
            seconds=seconds,peak_allocated_bytes=peak,report_sha256=rr['sha256'],
            scientific_status='UNADJUDICATED'),sort_keys=True))

    def test_cpu_cuda_is_explicit(self):
        import torch
        if not torch.cuda.is_available():
            with self.assertRaises(RuntimeError): learn.evaluate(self.root,self.plan,'cuda')
        else: self.assertEqual(learn.metrics([])['eligible'],0)


class ReplayTests(unittest.TestCase):
    def test_actual_complete_run_replay(self):
        f=fixture_runtime.RuntimeTests(); f.setUp(); self.addCleanup(f.doCleanups)
        run=f.run_to_review()
        for i,item in enumerate(f.app.review_items(run,limit=1000)['items']): f.app.submit(f.decision(run,item,'glyph' if i==0 else 'false_positive'))
        f.app.sweep(); f.app.sweep(); audit=learn.audit_run(f.root,run); self.assertEqual(len(audit['comparisons']),2)
        result=learn.replay_run(f.root,run); self.assertEqual(result['status'],'PASS'); self.assertGreater(result['scores'],0); self.assertEqual(result['comparisons'],2)
        self.assertEqual(learn.audit_run(f.root,run),audit)


if __name__=='__main__': unittest.main()

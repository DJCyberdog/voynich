import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz
import vrs_contract as c
import vrs_core as core
import vrs_hardware as h
from vrs_coordinator import ref
from vrs_service import Service


class ServiceTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name); self.app=Service(self.root)
        with fitz.open() as doc:
            for _ in range(3):
                page=doc.new_page(width=90,height=90)
                for x in (15,24,33): page.draw_rect(fitz.Rect(x,22,x+1,32),color=None,fill=(0,0,0))
            doc.new_page(width=90,height=90)
            doc.save(self.root/'source.pdf')
        for name in ('references','model','recognition_policy','transcription'):
            (self.root/name).write_text('synthetic fixture '+name)

    def file(self,name,value):
        path=self.root/name; path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,sort_keys=True),encoding='utf-8')
        return ref(self.root,path)

    def manifest(self,nonce,pages):
        groups=self.file(f'groups-{nonce}.json',{str(p):f'leaf-{p}' for p in pages})
        inputs={role:ref(self.root,self.root/name) for role,name in [('manuscript','source.pdf'),('references','references'),('model','model'),('recognition_policy','recognition_policy')]}
        inputs['groups']=groups
        return dict(schema=1,module=c.MODULE,protocol=c.PROTOCOL,backend='cpu',seed=7,run_nonce=nonce*32,inputs=inputs,transcriptions=[ref(self.root,self.root/'transcription')])

    def register(self,nonce,pages): return self.app.register(self.manifest(nonce,pages))
    def status(self,run): return self.app.ledger.status(run)

    def stage_data(self,run,stage):
        return c.load(c.artifact(self.root,self.status(run)['receipts'][stage]['artifact']))

    def proposals(self,run):
        self.assertEqual(self.app.sweep()[0]['stage'],'script_regions')
        self.assertEqual(self.app.sweep()[0]['stage'],'glyph_segmentation')
        self.assertEqual(self.status(run)['next_stage'],'glyph_classification')

    def fixture_outcomes(self,run,kind):
        # Test-only producer: use actual page/box proposals, never a scientific classifier.
        token=self.app.ledger.claim(run)
        manifest,receipts=self.app.ledger.context(run,token,self.app.identity)
        seg=receipts['glyph_segmentation']['artifact']; index=c.load(c.artifact(self.root,seg))
        counts=dict(total=0,accepted=0,abstained=0,failed=0); pages=[]
        for row in index['pages']:
            data=c.load(c.artifact(self.root,row['proposals'])); rows=[]
            for region in data['regions']:
                for box in region['boxes']:
                    outcome=kind; reason={'ACCEPTED':'NONE','ABSTAINED':'UNKNOWN','FAILED':'PROCESSING_ERROR'}[kind]
                    rows.append(dict(region_id=region['id'],box=box,outcome=outcome,reason=reason,uncertainty=None))
                    counts['total']+=1; counts[outcome.lower()]+=1
            out=self.file(f'fixture/{run}/p{row["page"]}.json',dict(schema=1,run_id=run,page=row['page'],source=row['proposals'],rows=rows))
            pages.append(dict(page=row['page'],outcomes=out))
        out=self.file(f'fixture/{run}/index.json',dict(schema=1,run_id=run,stage='glyph_classification',scientific_status='UNADJUDICATED',kind='OCCURRENCE_OUTCOMES_V1',source=seg,pages=pages,model_sha256=manifest['inputs']['model']['sha256'],policy_sha256=manifest['inputs']['recognition_policy']['sha256'],references_sha256=manifest['inputs']['references']['sha256']))
        item=self.app._item(run,'glyph_classification','COMPLETED','NONE',out); item['counts']=counts
        self.app.ledger.record(run,token,item); self.app.ledger.release(run,token)
        return counts

    def test_real_headless_waiting_review_and_independent_pages(self):
        a=self.register('1',[1]); self.proposals(a)
        counts=self.fixture_outcomes(a,'ABSTAINED'); self.assertGreater(counts['abstained'],0)
        b=self.register('2',[2]); sentinel=self.root/'workspace'/'fixture-stop'
        proc=subprocess.Popen([sys.executable,str(Path(__file__).with_name('vrs_service.py').resolve()),str(self.root),'watch','--interval','1','--stop-file',sentinel.relative_to(self.root).as_posix()],cwd=self.root,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            deadline=time.monotonic()+20
            while time.monotonic()<deadline and proc.poll() is None:
                if self.status(a)['control']=='BLOCKED' and self.status(b)['control']=='BLOCKED': break
                time.sleep(.1)
            sa=self.status(a); sb=self.status(b)
            self.assertEqual(sa['receipts']['exception_review']['reason'],'REVIEW_PENDING')
            self.assertEqual(sa['receipts']['exception_review']['counts']['pending'],counts['abstained'])
            self.assertEqual(sa['next_stage'],'exception_review')
            self.assertEqual(sb['next_stage'],'glyph_classification'); self.assertEqual(sb['control'],'BLOCKED')
            self.assertEqual(self.app.queue.summary(a)['pending'],counts['abstained'])
            generation=sa['generation']; time.sleep(1.2)
            self.assertEqual(self.status(a)['generation'],generation)
        finally:
            sentinel.touch()
            try: _,err=proc.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.communicate()
                self.fail('Cooperative watch stop timed out')
        self.assertEqual(proc.returncode,0,err.decode(errors='replace'))
        self.assertFalse(self.status(a)['locked']); self.assertFalse(self.status(b)['locked'])
        self.assertEqual(self.app.ledger.outbox(),[])
        with self.assertRaisesRegex(ValueError,'correction handoff'): self.app.ledger.resume_service(a,self.app.identity)

    def test_hybrid_mode_identity_and_missing_attachment(self):
        run=self.register('1',[1]); self.proposals(run)
        mode=Service(self.root,hybrid_evidence=True)
        self.assertNotEqual(mode.identity,self.app.identity)
        source=self.stage_data(run,'script_regions'); seg=self.stage_data(run,'glyph_segmentation')
        with self.assertRaisesRegex(ValueError,'Missing hybrid page evidence'):
            mode._check_prefix('glyph_segmentation',seg['pages'],[1],source)
        with self.assertRaisesRegex(ValueError,'pinned Yale source'):
            mode._scope('script_regions',self.manifest('2',[1]),{})

    def test_empty_queue_not_alignment_permission(self):
        run=self.register('1',[4]); self.proposals(run)
        self.assertEqual(self.fixture_outcomes(run,'ACCEPTED')['total'],0)
        self.assertEqual(self.app.sweep()[0]['control'],'READY')
        self.assertEqual(self.status(run)['next_stage'],'transcription_alignment')
        self.assertEqual(self.app.sweep()[0]['reason'],'UNSUPPORTED')
        self.assertEqual(self.status(run)['control'],'BLOCKED')
        self.assertEqual(self.app.queue.summary(run)['scientific_status'],'UNADJUDICATED')
        with self.assertRaisesRegex(ValueError,'not enabled'): self.app.ledger.resume_service(run,self.app.identity)

    def test_accepted_only_and_failed_only_remain_distinct(self):
        a=self.register('1',[1]); self.proposals(a); count=self.fixture_outcomes(a,'ACCEPTED'); self.assertGreater(count['accepted'],0)
        self.app.sweep(); self.app.sweep()
        self.assertEqual(self.app.queue.summary(a)['pending'],0)
        self.assertEqual(self.status(a)['next_stage'],'transcription_alignment')
        b=self.register('2',[2]); self.proposals(b); count=self.fixture_outcomes(b,'FAILED'); self.assertGreater(count['failed'],0)
        self.assertEqual(self.app.sweep()[0]['reason'],'DEPENDENCY')
        self.assertEqual(self.status(b)['next_stage'],'exception_review')
        self.assertEqual(self.app.queue.summary(b)['classification']['failed'],count['failed'])
        with self.assertRaisesRegex(ValueError,'new authorized run'): self.app.ledger.resume_service(b,self.app.identity)

    def test_actual_exit_after_page_checkpoint_no_recompute(self):
        run=self.register('1',[1,2,3]); code="import os,sys; from vrs_service import Service; a=Service(sys.argv[1]); orig=a.ledger.checkpoint; a.ledger.checkpoint=lambda *x:(orig(*x),os._exit(77)); a.sweep()"
        p=subprocess.run([sys.executable,'-c',code,str(self.root)],cwd=Path(__file__).parent,timeout=30)
        self.assertEqual(p.returncode,77); st=self.status(run); self.assertTrue(st['locked'])
        cp=c.load(c.artifact(self.root,st['checkpoint']['artifact'])); self.assertEqual([x['page'] for x in cp['pages']],[1])
        with self.assertRaises(ValueError): self.app.recover(run,st['generation'])
        self.app.recover(run,st['generation'],confirm_stopped=True)
        restarted=Service(self.root); orig=restarted._page; calls=[]
        def observe(run,stage,page,source,attempt): calls.append(page); return orig(run,stage,page,source,attempt)
        with patch.object(restarted,'_page',side_effect=observe): self.assertEqual(restarted.sweep()[0]['control'],'READY')
        self.assertEqual(calls,[2,3]); self.assertEqual(self.stage_data(run,'script_regions')['pages'][0],cp['pages'][0])

    def test_resource_pause_preserves_segmentation_checkpoint(self):
        run=self.register('1',[1,2]); self.app.sweep(); orig=self.app._page; calls=[]
        def pressure(run,stage,page,source,attempt):
            calls.append(page)
            if page==2: raise h.ResourceBlocked('test pressure')
            return orig(run,stage,page,source,attempt)
        with patch.object(self.app,'_page',side_effect=pressure): self.assertEqual(self.app.sweep()[0]['reason'],'RESOURCE_PRESSURE')
        st=self.status(run); self.assertEqual(st['control'],'PAUSED'); self.assertEqual(calls,[1,2]); self.assertIsNotNone(st['checkpoint'])
        self.assertEqual(self.app.sweep(),[]); self.app.ledger.resume_service(run,self.app.identity); calls=[]
        def observe(run,stage,page,source,attempt): calls.append(page); return orig(run,stage,page,source,attempt)
        with patch.object(self.app,'_page',side_effect=observe): self.app.sweep()
        self.assertEqual(calls,[2]); self.assertEqual(self.status(run)['next_stage'],'glyph_classification')

    def test_stop_request_and_queue_import_crash_recovery(self):
        run=self.register('1',[1]); self.proposals(run); self.fixture_outcomes(run,'ABSTAINED')
        code="import os,sys; from vrs_service import Service; a=Service(sys.argv[1]); a.ledger.record=lambda *x:os._exit(78); a.sweep()"
        p=subprocess.run([sys.executable,'-c',code,str(self.root)],cwd=Path(__file__).parent,timeout=30)
        self.assertEqual(p.returncode,78); st=self.status(run); self.assertTrue(st['locked'])
        before=self.app.queue.summary(run); self.app.recover(run,st['generation'],confirm_stopped=True)
        self.app.sweep(); self.assertEqual(self.status(run)['receipts']['exception_review']['reason'],'REVIEW_PENDING')
        self.assertEqual(self.app.queue.summary(run)['queue_sha256'],before['queue_sha256'])
        self.assertEqual(sum(r['kind']=='EXCEPTION_QUEUE_SEEDED' for r in self.app.ledger.history(run)),1)
        self.app.ledger.request_stop(run); self.assertEqual(self.status(run)['control'],'PAUSED')
        with self.assertRaisesRegex(ValueError,'correction handoff'): self.app.ledger.resume_service(run,self.app.identity)
        self.app.ledger.request_stop(run,cancel=True); self.assertEqual(self.status(run)['control'],'CANCELLED')

    def test_service_stop_preserves_page_and_restarts(self):
        run=self.register('1',[1,2]); orig=self.app.ledger.checkpoint
        def stopping(*args): orig(*args); self.app.stop.set()
        with patch.object(self.app.ledger,'checkpoint',side_effect=stopping): self.app.sweep()
        st=self.status(run); self.assertEqual(st['control'],'READY'); self.assertFalse(st['locked']); self.assertIsNotNone(st['checkpoint'])
        resumed=Service(self.root); self.assertEqual(resumed.sweep()[0]['control'],'READY'); self.assertEqual(self.status(run)['next_stage'],'glyph_segmentation')

    def test_page_tamper_blocks_resume_without_overwrite(self):
        run=self.register('1',[1,2]); orig=self.app.ledger.checkpoint
        def stopping(*args): orig(*args); self.app.stop.set()
        with patch.object(self.app.ledger,'checkpoint',side_effect=stopping): self.app.sweep()
        cp=c.load(c.artifact(self.root,self.status(run)['checkpoint']['artifact'])); path=c.artifact(self.root,cp['pages'][0]['manifest']); crop=path.parent/c.load(path)['regions'][0]['file']; crop.write_bytes(b'tampered')
        a=Service(self.root); self.assertEqual(a.sweep()[0]['control'],'PAUSED'); self.assertEqual(self.status(run)['next_stage'],'script_regions')
        self.assertEqual(crop.read_bytes(),b'tampered'); self.assertEqual(a.sweep(),[])

    def test_cancel_during_page_does_not_advance(self):
        run=self.register('1',[1,2]); original=self.app._page
        def cancel(run,stage,page,source,attempt):
            row=original(run,stage,page,source,attempt)
            self.app.ledger.request_stop(run,cancel=True)
            return row
        with patch.object(self.app,'_page',side_effect=cancel): self.app.sweep()
        st=self.status(run); self.assertEqual(st['control'],'CANCELLED'); self.assertFalse(st['locked'])
        self.assertEqual(st['next_stage'],'script_regions'); self.assertIsNotNone(st['checkpoint'])
        self.assertEqual(self.app.sweep(),[])

    def test_queue_admission_pause_before_seed_and_retry(self):
        run=self.register('1',[1]); self.proposals(run); self.fixture_outcomes(run,'FAILED')
        with patch.object(self.app,'_admit',side_effect=h.ResourceBlocked('fixture')):
            self.assertEqual(self.app.sweep()[0]['control'],'ERROR')
        self.assertEqual(self.status(run)['control'],'PAUSED')
        self.assertEqual(self.app.ledger.history(run)[-1]['payload']['reason'],'RESOURCE_PRESSURE')
        with self.assertRaises(ValueError): self.app.queue.summary(run)
        self.app.ledger.resume_service(run,self.app.identity)
        self.assertEqual(self.app.sweep()[0]['reason'],'DEPENDENCY')

    def test_local_plan_atomic_and_identity_fenced(self):
        a=self.manifest('1',[1]); b=self.manifest('2',[2]); bad=dict(b,backend='cuda')
        ra=self.file('config/a.json',a); rb=self.file('config/b.json',b); rc=self.file('config/bad.json',bad)
        with self.assertRaises(ValueError): self.app.register_plan(dict(schema=1,manifests=[ra,rc]))
        self.assertEqual(self.app.ledger.registered(),[])
        with self.assertRaises(ValueError): self.app.register_plan(dict(schema=1,manifests=[ra,ra]))
        old=self.app.ledger.register(b,'cpu','a'*64)
        with self.assertRaises(ValueError): self.app.register_plan(dict(schema=1,manifests=[ra,rb]))
        self.assertEqual([r['run_id'] for r in self.app.ledger.registered()],[old]); self.assertEqual(self.app.sweep(),[])
        ids=self.app.register_plan(dict(schema=1,manifests=[ra])); self.assertEqual(ids,self.app.register_plan(dict(schema=1,manifests=[ra])))
        self.assertEqual(self.app.sweep()[0]['run_id'],ids[0]); self.assertEqual(self.status(old)['generation'],0)


if __name__=='__main__': unittest.main()

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
import vrs_coordinator as co
import vrs_hardware as h


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name); self.app=co.Coordinator(self.root)
        with fitz.open() as doc:
            page=doc.new_page(width=90,height=90)
            for x in (15,24,33): page.draw_rect(fitz.Rect(x,22,x+1,32),color=None,fill=(0,0,0))
            doc.new_page(width=90,height=90)  # genuinely blank fixture
            doc.save(self.root/'source.pdf')
        (self.root/'groups.json').write_text('{"1":"leaf-a"}')
        (self.root/'blank.json').write_text('{"2":"leaf-b"}')
        for name in ('references','model','recognition_policy','transcription'):
            (self.root/name).write_text('unconsumed pinned fixture '+name)
        self.m=dict(schema=1,module=c.MODULE,protocol=c.PROTOCOL,backend='cpu',seed=7,run_nonce='1'*32,
                    inputs={k:co.ref(self.root,self.root/n) for k,n in [('manuscript','source.pdf'),('groups','groups.json'),('references','references'),('model','model'),('recognition_policy','recognition_policy')]},
                    transcriptions=[co.ref(self.root,self.root/'transcription')])

    def register(self, nonce='1', blank=False):
        m=dict(self.m,run_nonce=nonce*32)
        if blank: m['inputs']=dict(m['inputs'],groups=co.ref(self.root,self.root/'blank.json'))
        return self.app.register(m)

    def status(self, run): return self.app.ledger.status(run)

    def read_stage(self, run, stage):
        item=self.status(run)['receipts'][stage]
        return json.loads(c.artifact(self.root,item['artifact']).read_text())

    def test_actual_two_run_pipeline_and_blank(self):
        a=self.register(); b=self.register('2',True)
        self.assertEqual(self.register(),a)
        self.assertEqual(len(self.app.sweep()),2)
        self.assertEqual(self.read_stage(a,'script_regions')['kind'],'INK_PROPOSALS_ONLY')
        self.assertGreater(self.read_stage(a,'script_regions')['pages'][0]['regions'],0)
        self.assertEqual(self.read_stage(b,'script_regions')['pages'][0]['regions'],0)
        self.assertEqual(len(self.app.sweep()),2)
        self.assertGreater(self.read_stage(a,'glyph_segmentation')['pages'][0]['candidates'],0)
        self.assertEqual(self.read_stage(b,'glyph_segmentation')['pages'][0]['candidates'],0)
        self.assertEqual(len(self.app.sweep()),2)
        for run in (a,b):
            st=self.status(run); self.assertEqual(st['control'],'BLOCKED')
            self.assertEqual(st['next_stage'],'glyph_classification')
            self.assertEqual(st['receipts']['glyph_classification']['reason'],'UNSUPPORTED')
            self.assertFalse(st['locked'])
        self.assertEqual(self.app.sweep(),[])
        self.assertEqual(self.app.ledger.outbox(),[])

    def test_blocked_run_does_not_starve_later_run(self):
        a=self.register()
        with patch.object(self.app,'_admit',side_effect=h.ResourceBlocked('fixture')):
            self.assertEqual(self.app.sweep()[0]['reason'],'DEPENDENCY')
        self.assertEqual(self.status(a)['control'],'BLOCKED')
        b=self.register('2',True)
        self.assertEqual([r['run_id'] for r in self.app.sweep()],[b])
        self.assertEqual(self.status(b)['next_stage'],'glyph_segmentation')
        self.assertEqual(self.status(a)['generation'],1)

    def test_pause_at_checkpoint_and_resume_without_recompute(self):
        run=self.register(); original=self.app.ledger.checkpoint
        def pause(*args):
            original(*args); self.app.ledger.request_stop(run)
        with patch.object(self.app.ledger,'checkpoint',side_effect=pause): self.app.sweep()
        st=self.status(run); self.assertEqual(st['control'],'PAUSED'); self.assertIsNotNone(st['checkpoint'])
        restarted=co.Coordinator(self.root); restarted.ledger.resume(run)
        with patch.object(restarted,'_execute',side_effect=AssertionError('must not rerun')):
            self.assertEqual(restarted.sweep()[0]['control'],'READY')
        self.assertEqual(self.status(run)['next_stage'],'glyph_segmentation')
        self.assertIsNone(self.status(run)['checkpoint'])

    def test_actual_process_exit_and_fenced_recovery(self):
        run=self.register(blank=True)
        code="import os,sys; import vrs_coordinator as c; a=c.Coordinator(sys.argv[1]); a.ledger.record=lambda *args:os._exit(77); a.sweep()"
        done=subprocess.run([sys.executable,'-c',code,str(self.root)],cwd=Path(co.__file__).parent,timeout=30)
        self.assertEqual(done.returncode,77)
        st=self.status(run); self.assertTrue(st['locked']); self.assertIsNotNone(st['checkpoint'])
        self.assertEqual(self.app.sweep(),[])
        with self.assertRaises(ValueError): self.app.recover(run,st['generation'])
        with self.assertRaises(ValueError): self.app.recover(run,st['generation']+1,confirm_stopped=True)
        self.app.recover(run,st['generation'],confirm_stopped=True)
        with patch.object(self.app,'_execute',side_effect=AssertionError('must not rerun')): self.app.sweep()
        self.assertEqual(self.status(run)['next_stage'],'glyph_segmentation')

    def test_nested_crop_tamper_pauses_without_advance(self):
        run=self.register(); self.app.sweep()
        data=self.read_stage(run,'script_regions'); p=c.artifact(self.root,data['pages'][0]['manifest'])
        crop=p.parent/json.loads(p.read_text())['regions'][0]['file']; crop.write_bytes(b'tampered')
        self.assertEqual(self.app.sweep()[0]['control'],'ERROR')
        self.assertEqual(self.status(run)['control'],'PAUSED')
        self.assertEqual(self.status(run)['next_stage'],'glyph_segmentation')
        self.assertEqual(self.app.sweep(),[])

    def test_cancel_and_explicit_cuda_denial(self):
        run=self.register(); self.app.ledger.request_stop(run,cancel=True)
        self.assertEqual(self.app.sweep(),[])
        self.assertEqual(self.status(run)['control'],'CANCELLED')
        with self.assertRaises(ValueError): self.app.register(dict(self.m,backend='cuda'))
        with self.assertRaises(ValueError): self.app.register(dict(self.m,command='arbitrary'))

    def test_os_scheduler_lock_and_root_relative_state(self):
        run=self.register(blank=True)
        with co.scheduler_lock(self.app.lock):
            code="import sys; import vrs_coordinator as c; c.Coordinator(sys.argv[1]).sweep()"
            done=subprocess.run([sys.executable,'-c',code,str(self.root)],cwd=Path(co.__file__).parent,capture_output=True,timeout=10)
            self.assertNotEqual(done.returncode,0)
        self.app.sweep()
        with tempfile.TemporaryDirectory() as d:
            import shutil
            target=Path(d)/'moved workspace'; shutil.copytree(self.root,target)
            reopened=co.Coordinator(target)
            self.assertEqual(reopened.ledger.status(run)['next_stage'],'glyph_segmentation')
            self.assertEqual(reopened.sweep()[0]['stage'],'glyph_segmentation')

    def test_real_headless_watch_process(self):
        run=self.register(blank=True)
        proc=subprocess.Popen([sys.executable,str(Path(co.__file__).resolve()),str(self.root),'watch','--interval','1'],cwd=self.root,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            until=time.monotonic()+15
            while time.monotonic()<until and proc.poll() is None and self.status(run)['control']!='BLOCKED': time.sleep(.1)
            self.assertEqual(self.status(run)['control'],'BLOCKED')
        finally:
            proc.terminate(); proc.communicate(timeout=5)


if __name__=='__main__': unittest.main()

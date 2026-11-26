import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import vrs_contract as c
from vrs_core import sha
from vrs_operations import Operations
from vrs_monitor import Monitor,Notifications
import test_vrs_runtime as fixtures


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.RuntimeTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.root=self.f.root; self.api=Operations(self.root)

    def wait(self,fn,timeout=20):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if fn():return
            time.sleep(.1)
        self.fail('Condition timed out; managed session state: '+self.api.session()['state'])

    def test_empty_resources_and_caps(self):
        with tempfile.TemporaryDirectory() as d:
            a=Operations(d); self.assertEqual(a.jobs(),[]); r=a.resources(); self.assertTrue(0<=r['cpu_percent']<=100); self.assertGreater(r['ram_total'],0); self.assertEqual(r['gpu'],'NOT_MEASURED'); self.assertEqual(r['worker']['state'],'NOT_MANAGED'); self.assertNotIn('pid',json.dumps(a.diagnostics())); self.assertNotIn(d,json.dumps(a.diagnostics()))
            value=dict(cpu_threads=2,ram_mib=512,disk_mib=1024); self.assertEqual(a.save_ops(value),value); self.assertEqual(a.settings_ops(),value)
            for invalid in (dict(value,cpu_threads=True),dict(value,ram_mib=-1),dict(value,cpu_threads=257)):
                with self.assertRaises(ValueError):a.save_ops(invalid)

    def test_actual_managed_worker_and_stop(self):
        run=self.f.app.register(self.f.m); self.api.save_ops(dict(cpu_threads=2,ram_mib=0,disk_mib=0))
        try:
            session=self.api.start(sys.executable); self.assertEqual(session['state'],'RUNNING'); self.assertEqual(session['limits']['cpu_threads'],2)
            with self.assertRaises(ValueError):self.api.start(sys.executable)
            self.wait(lambda:self.f.status(run)['control']=='BLOCKED')
            self.assertEqual(self.api.jobs()[0]['reason'],'REVIEW_PENDING'); self.assertEqual(self.api.notice()[0],1)
            self.assertIn(self.api.stop()['state'],('STOP_REQUESTED','STOPPED'))
            self.wait(lambda:self.api.session()['state']=='STOPPED')
            self.assertFalse(self.f.status(run)['locked']); self.assertEqual(self.f.app.ledger.outbox(),[])
        finally:
            if self.api.session()['state'] in ('RUNNING','STOP_REQUESTED'):self.api.stop(); self.wait(lambda:self.api.session()['state']=='STOPPED')

    def test_terminal_acknowledgement_waits_for_process_exit(self):
        import psutil
        from vrs_desktop_api import atomic_json
        from vrs_operations import BASE
        p=self.root/BASE/'session.json';ident='a'*32
        atomic_json(p,dict(id=ident,pid=os.getpid(),created=psutil.Process().create_time(),state='STOPPED',limits=self.api.settings_ops()))
        self.assertEqual(self.api.session()['state'],'STOP_REQUESTED')
        # Reused or absent PID cannot impersonate the original process.
        data=c.load(p);data['created']-=100;atomic_json(p,data)
        self.assertEqual(self.api.session()['state'],'STOPPED')

    def test_bounded_session_write_retry(self):
        from vrs_operations import write_session
        p=self.root/'session-fixture.json';value={'state':'STOPPED'}
        with patch('vrs_operations.os.name','nt'),patch('vrs_operations.atomic_json',side_effect=[PermissionError('sharing violation'),None]) as write,patch('vrs_operations.time.sleep'):
            write_session(p,value);self.assertEqual(write.call_count,2)
        with patch('vrs_operations.os.name','nt'),patch('vrs_operations.atomic_json',side_effect=PermissionError('persistent')),patch('vrs_operations.time.monotonic',side_effect=[0,4]):
            with self.assertRaises(PermissionError):write_session(p,value)

    def test_resource_ceiling_pauses_and_resume(self):
        run=self.f.app.register(self.f.m); self.api.save_ops(dict(cpu_threads=1,ram_mib=1,disk_mib=0))
        try:
            self.api.start(sys.executable); self.wait(lambda:self.f.status(run)['control']=='PAUSED')
            self.assertEqual(self.api.jobs()[0]['completed'],0); self.assertIn('RESOURCE_PRESSURE',json.dumps(self.api.detail(run)))
        finally:
            if self.api.session()['state'] in ('RUNNING','STOP_REQUESTED'):self.api.stop(); self.wait(lambda:self.api.session()['state']=='STOPPED')
        self.assertEqual(self.api.control(sys.executable,'resume',run)['control'],'READY'); self.assertEqual(self.api.control(sys.executable,'cancel',run)['control'],'CANCELLED')
        with self.assertRaises(ValueError):self.api.control(sys.executable,'watch',run)

    def test_checkpoint_and_redacted_history(self):
        run=self.f.app.register(self.f.m); app=self.f.app; original=app.ledger.checkpoint
        def stop(*args):original(*args); app.stop.set()
        with patch.object(app.ledger,'checkpoint',side_effect=stop):app.sweep()
        d=self.api.detail(run); self.assertEqual(d['pages'],dict(done=1,total=1)); self.assertEqual(self.api.jobs()[0]['completed'],0)
        with app.ledger._tx() as db:app.ledger._event(db,run,'REVIEW_DECISION',dict(reviewer='SECRET',candidate_id='SECRET',reason='SECRET',path='SECRET'))
        self.assertNotIn('SECRET',json.dumps(self.api.detail(run)))

    def test_evidence_and_preview_actual_comparison(self):
        run=self.f.run_to_review(); q=self.f.app.review_items(run,limit=1000); initial=self.api.evidence(run); self.assertEqual(initial['review']['pending'],len(q['items'])); self.assertEqual(initial['comparisons'],[])
        for i,item in enumerate(q['items']):self.f.app.submit(self.f.decision(run,item,'glyph' if i==0 else 'false_positive'))
        self.f.app.sweep(); self.f.app.sweep(); before=sha(self.f.app.ledger.db); e=self.api.evidence(run); self.assertEqual(e['scientific_status'],'UNADJUDICATED'); self.assertEqual(len(e['comparisons']),2); self.assertTrue(all(r['compared']==1 for r in e['comparisons'])); self.assertEqual(e['review']['resolved'],len(q['items']))
        rel=self.api.export_preview(run); self.assertEqual(c.load(self.root/rel),e); self.assertEqual(self.api.export_preview(run),rel); self.assertEqual(sha(self.f.app.ledger.db),before); self.assertNotIn('accuracy',json.dumps(e)); self.assertEqual(self.f.app.ledger.outbox(),[])
        index=c.load(c.artifact(self.root,self.f.status(run)['receipts']['transcription_alignment']['artifact'])); (self.root/index['reports'][0]['report']['path']).write_text('{}')
        with self.assertRaises(ValueError):self.api.evidence(run)

    def test_notification_coalescing_and_private_payload(self):
        n=Notifications(); self.assertTrue(n.next(1,'a',0)); self.assertFalse(n.next(1,'a',100)); self.assertFalse(n.next(2,'b',10)); self.assertTrue(n.next(2,'b',31)); self.assertFalse(n.next(0,'empty',35)); self.assertTrue(n.next(1,'a',70))
        run=self.f.run_to_review(); count,key=self.api.notice(); self.assertEqual(count,1); self.assertNotEqual(key,run); self.assertEqual(len(key),64)

    def test_actual_gui_operations(self):
        import tkinter as tk
        run=self.f.run_to_review(); w=tk.Tk(); app=Monitor(w,self.root)
        def settle():
            deadline=time.monotonic()+12
            while time.monotonic()<deadline:
                w.update(); time.sleep(.015)
                if app.future is None:return
            self.fail('GUI operation timeout')
        try:
            settle(); app.show('Jobs'); settle(); self.assertIn(run,app.jobs_tree.get_children()); app.jobs_tree.selection_set(run); app.job_detail(); settle(); self.assertIn('REVIEW_PENDING',app.job_text.get('1.0','end')); self.assertIn('CPU',app.telemetry.get()); app.show('Evidence'); settle(); self.assertIn('UNADJUDICATED',app.ev_text.get('1.0','end')); app.export(); settle(); self.assertTrue(list((self.root/'workspace/vrs101/exports').glob('*.json')))
            w.geometry('1024x650'); w.update(); self.assertEqual(w.winfo_width(),1024); self.assertEqual(w.winfo_height(),650)
        finally:
            if app.future: settle()
            app.close()


if __name__=='__main__':unittest.main()

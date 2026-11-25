import copy
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import vrs_contract as c
from vrs_core import sha
from vrs_ledger import Ledger


class LedgerTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.db = self.root / 'ledger.sqlite'
        self.l = Ledger(self.root, self.db)
        self.m = dict(schema=1, module=c.MODULE, protocol=c.PROTOCOL, backend='cpu', seed=9,
                      run_nonce='1'*32, inputs={r:self.file(r) for r in c.ROLES}, transcriptions=[self.file('eva')])
        self.run = self.l.register(self.m, 'cpu', 'b'*64)
        self.repo = 'DJCyberdog/voynich'

    def file(self, name, text=None):
        p = self.root / name
        p.write_text(text or 'fixture '+name)
        return dict(path=name, sha256=sha(p))

    def item(self, stage, counts=None, state='COMPLETED', reason='NONE', name=None):
        artifact = self.file(name or stage) if state=='COMPLETED' or reason=='REVIEW_PENDING' else None
        return dict(schema=1, run_id=self.run, stage=stage, state=state, reason=reason, artifact=artifact, counts=counts)

    def classify(self, token):
        for stage in c.STAGES[:2]:
            self.l.record(self.run, token, self.item(stage))
        self.l.record(self.run, token, self.item(c.STAGES[2], dict(total=5,accepted=3,abstained=2,failed=0)))

    def finish(self):
        token = self.l.claim(self.run)
        self.classify(token)
        self.l.record(self.run, token, self.item(c.STAGES[3],dict(resolved=2,pending=0,deferred=0)))
        return self.l.record(self.run, token, self.item(c.STAGES[4]))

    def enqueue(self):
        return self.l.enqueue(self.run,self.repo,'a'*40,{self.repo},publish=True)

    def test_registration_idempotent_and_scope(self):
        self.assertEqual(self.l.register(self.m,'cpu','b'*64),self.run)
        with self.assertRaisesRegex(ValueError,'identity conflict'):
            self.l.register(self.m,'cpu','c'*64)
        with self.assertRaises(ValueError):
            self.l.register(dict(self.m,experiment='EXP-9999'),'cpu','b'*64)
        self.assertEqual(self.l.status(self.run)['next_stage'],c.STAGES[0])

    def test_concurrent_claim_exclusive(self):
        def get():
            try:
                return Ledger(self.root,self.db).claim(self.run)
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            values=list(pool.map(lambda _:get(),range(2)))
        self.assertEqual(sum(v is not None for v in values),1)

    def test_checkpoint_restart_and_fencing(self):
        token=self.l.claim(self.run)
        cp=self.file('checkpoint')
        self.l.checkpoint(self.run,token,c.STAGES[0],cp)
        l=Ledger(self.root,self.db)
        self.assertEqual(l.status(self.run)['checkpoint']['artifact'],cp)
        gen=l.status(self.run)['generation']
        with self.assertRaises(ValueError): l.recover(self.run,gen)
        with self.assertRaises(ValueError): l.recover(self.run,gen+1,worker_confirmed_stopped=True)
        l.recover(self.run,gen,worker_confirmed_stopped=True)
        new=l.claim(self.run)
        self.assertNotEqual(new,token)
        with self.assertRaisesRegex(ValueError,'Stale'): l.release(self.run,token)
        l.record(self.run,new,self.item(c.STAGES[0]))
        self.assertIsNone(l.status(self.run)['checkpoint'])
        self.assertEqual([h['kind'] for h in l.history(self.run)],['CHECKPOINT','RECEIPT'])

    def test_checkpoint_tamper_and_stage_guard(self):
        token=self.l.claim(self.run)
        with self.assertRaises(ValueError): self.l.checkpoint(self.run,token,c.STAGES[1],self.file('wrong'))
        with self.assertRaises(ValueError): self.l.checkpoint(self.run,token,c.STAGES[0],self.m['inputs']['model'])
        cp=self.file('cp')
        self.l.checkpoint(self.run,token,c.STAGES[0],cp)
        self.l.release(self.run,token)
        self.file('cp','tampered')
        with self.assertRaisesRegex(ValueError,'hash mismatch'): self.l.claim(self.run)
        self.assertFalse(self.l.status(self.run)['locked'])

    def test_pause_and_cancel_cooperative(self):
        token=self.l.claim(self.run)
        self.l.request_stop(self.run)
        self.assertEqual(self.l.status(self.run)['control'],'PAUSE_REQUESTED')
        with self.assertRaisesRegex(ValueError,'Stop requested'): self.l.record(self.run,token,self.item(c.STAGES[0]))
        self.l.checkpoint(self.run,token,c.STAGES[0],self.file('cp'))
        self.l.release(self.run,token)
        self.assertEqual(self.l.status(self.run)['control'],'PAUSED')
        self.l.resume(self.run)
        token=self.l.claim(self.run)
        self.l.request_stop(self.run,cancel=True)
        with self.assertRaises(ValueError): self.l.request_stop(self.run)
        self.l.release(self.run,token)
        self.assertEqual(self.l.status(self.run)['control'],'CANCELLED')
        with self.assertRaises(ValueError): self.l.resume(self.run)

    def test_review_block_unrelated_run_and_resume(self):
        token=self.l.claim(self.run)
        self.classify(token)
        item=self.item(c.STAGES[3],dict(resolved=0,pending=1,deferred=1),'BLOCKED','REVIEW_PENDING','review0')
        self.assertEqual(self.l.record(self.run,token,item),'BLOCKED')
        with self.assertRaises(ValueError): self.l.claim(self.run)
        other=self.l.register(dict(self.m,run_nonce='2'*32),'cpu','b'*64)
        self.assertTrue(self.l.claim(other))
        self.l.resume(self.run)
        token=self.l.claim(self.run)
        self.l.record(self.run,token,self.item(c.STAGES[3],dict(resolved=2,pending=0,deferred=0),name='review1'))
        self.assertEqual(self.l.record(self.run,token,self.item(c.STAGES[4])),'COMPLETED')
        self.assertEqual(len(self.l.history(self.run)),6)
        with self.assertRaises(ValueError): self.l.claim(self.run)

    def test_failure_requires_explicit_resume_and_preserves_history(self):
        token=self.l.claim(self.run)
        fail=self.item(c.STAGES[0],state='FAILED',reason='PROCESSING_ERROR')
        self.assertEqual(self.l.record(self.run,token,fail),'FAILED')
        with self.assertRaises(ValueError): self.l.claim(self.run)
        self.l.resume(self.run)
        token=self.l.claim(self.run)
        self.l.record(self.run,token,self.item(c.STAGES[0]))
        self.assertEqual(self.l.history(self.run)[0]['payload'],fail)

    def test_invalid_receipt_rolls_back(self):
        token=self.l.claim(self.run)
        with self.assertRaises(ValueError): self.l.record(self.run,token,self.item(c.STAGES[1]))
        self.assertEqual(self.l.history(self.run),[])
        self.classify(token)
        bad=self.item(c.STAGES[3],dict(resolved=3,pending=0,deferred=0))
        with self.assertRaisesRegex(ValueError,'denominator'): self.l.record(self.run,token,bad)
        self.assertEqual(self.l.status(self.run)['next_stage'],c.STAGES[3])

    def test_outbox_consent_idempotence_and_retry(self):
        self.assertEqual(self.finish(),'COMPLETED')
        with self.assertRaises(ValueError): self.l.enqueue(self.run,self.repo,'a'*40,{self.repo})
        key=self.enqueue()
        self.assertEqual(key,self.enqueue())
        l=Ledger(self.root,self.db)
        with self.assertRaises(ValueError): l.claim_report(key,{self.repo})
        with self.assertRaises(ValueError): l.claim_report(key,{'other/repo'},publish=True)
        token,report=l.claim_report(key,{self.repo},publish=True)
        self.assertEqual(c.digest(report),key)
        with self.assertRaises(ValueError): l.claim_report(key,{self.repo},publish=True)
        l.finish_report(key,token)
        new,again=l.claim_report(key,{self.repo},publish=True)
        self.assertEqual(report,again)
        remote=dict(report_sha256=key,repository=self.repo,pr_number=1,commit_sha='c'*40)
        with self.assertRaises(ValueError): l.finish_report(key,token,remote)
        with self.assertRaises(ValueError): l.finish_report(key,new,dict(remote,repository='other/repo'))
        l.finish_report(key,new,remote)
        self.assertEqual(l.outbox()[0]['state'],'SENT')
        self.assertEqual(l.outbox()[0]['remote'],remote)
        self.assertEqual(len(l.outbox()),1)

    def test_outbox_recovery_and_tamper(self):
        self.finish();key=self.enqueue();token,_=self.l.claim_report(key,{self.repo},publish=True)
        gen=self.l.outbox()[0]['generation']
        with self.assertRaises(ValueError): self.l.recover_report(key,gen)
        with self.assertRaises(ValueError): self.l.recover_report(key,gen+1,publisher_confirmed_stopped=True)
        self.l.recover_report(key,gen,publisher_confirmed_stopped=True)
        with self.assertRaises(ValueError): self.l.finish_report(key,token)
        with sqlite3.connect(self.db) as conn:
            conn.execute('UPDATE outbox SET report=? WHERE id=?',(json.dumps({'repository':self.repo}),key))
        with self.assertRaisesRegex(ValueError,'digest mismatch'): self.l.claim_report(key,{self.repo},publish=True)

    def test_partial_snapshot_preserved_and_no_ready_report(self):
        with self.assertRaises(ValueError): self.enqueue()
        token=self.l.claim(self.run);self.classify(token)
        self.l.record(self.run,token,self.item(c.STAGES[3],dict(resolved=0,pending=2,deferred=0),'BLOCKED','REVIEW_PENDING','first_review'))
        partial=self.enqueue()
        self.l.resume(self.run);token=self.l.claim(self.run)
        self.l.record(self.run,token,self.item(c.STAGES[3],dict(resolved=2,pending=0,deferred=0),name='final_review'))
        self.l.record(self.run,token,self.item(c.STAGES[4]))
        complete=self.enqueue()
        self.assertNotEqual(partial,complete)
        _,report=self.l.claim_report(partial,{self.repo},publish=True)
        self.assertEqual(report['technical_status'],'PARTIAL')
        _,report=self.l.claim_report(complete,{self.repo},publish=True)
        self.assertEqual(report['technical_status'],'COMPLETED')

    def test_schema_reject(self):
        with sqlite3.connect(self.db) as conn: conn.execute('PRAGMA user_version=99')
        with self.assertRaisesRegex(ValueError,'schema'): Ledger(self.root,self.db)

    def test_historical_checkpoint_path_reuse_rejected(self):
        token=self.l.claim(self.run)
        self.l.checkpoint(self.run,token,c.STAGES[0],self.file('cp1'))
        self.l.checkpoint(self.run,token,c.STAGES[0],self.file('cp2'))
        with self.assertRaisesRegex(ValueError,'Historical'): self.l.checkpoint(self.run,token,c.STAGES[0],self.file('cp1','changed'))


if __name__=='__main__': unittest.main()

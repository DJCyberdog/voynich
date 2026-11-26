"""VRS-140 synthetic read-only compatibility and relocation checks."""
import shutil
import tempfile
import unittest
from pathlib import Path
from vrs_core import sha
from vrs_rc_preflight import inspect
import test_vrs_runtime as fixture

class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.RuntimeTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.root=self.f.root;self.db=self.f.app.ledger.db

    def test_review_revision_roundtrip_relocated_copy(self):
        run=self.f.run_to_review();item=self.f.app.review_items(run)['items'][0]
        self.f.app.submit(self.f.decision(run,item,'deferred'))
        item=self.f.app.review_items(run)['items'][0];self.f.app.submit(self.f.decision(run,item,'glyph'))
        # Existing run identity remains immutable; classify it against another worker.
        before=sha(self.db);a=inspect(self.root,'0'*64)
        self.assertEqual(a['status'],'PREFLIGHT_PASS');self.assertEqual(a['counts']['decision_revisions'],2)
        self.assertEqual(a['counts']['foreign_worker'],1);self.assertFalse(a['execution_authorized'])
        with tempfile.TemporaryDirectory() as d:
            moved=Path(d)/'relocated';shutil.copytree(self.root,moved)
            b=inspect(moved,'0'*64);self.assertEqual(a,b)
            self.assertEqual(sha(self.db),before)

    def test_active_ownership_and_tamper(self):
        run=self.f.app.register(self.f.m);token=self.f.app.ledger.claim(run)
        before=sha(self.db);r=inspect(self.root,self.f.app.identity)
        self.assertEqual(r['status'],'BLOCKED_ACTIVE_OWNERSHIP');self.assertEqual(r['counts']['locked'],1)
        self.assertEqual(sha(self.db),before);self.f.app.ledger.release(run,token)
        (self.root/'eva.txt').write_text('tampered',encoding='utf-8')
        before=sha(self.db)
        with self.assertRaises(ValueError):inspect(self.root)
        self.assertEqual(sha(self.db),before)

    def test_unknown_schema_and_sidecar_rejected(self):
        side=self.db.with_name(self.db.name+'-wal');side.write_bytes(b'fixture')
        with self.assertRaisesRegex(ValueError,'sidecar'):inspect(self.root)
        side.unlink()
        with self.f.app.ledger._tx() as conn:conn.execute('PRAGMA user_version=99')
        before=sha(self.db)
        with self.assertRaisesRegex(ValueError,'Unsupported ledger schema'):inspect(self.root)
        self.assertEqual(sha(self.db),before)

if __name__=='__main__':unittest.main()

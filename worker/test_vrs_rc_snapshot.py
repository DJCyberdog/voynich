"""Snapshot and restore fixtures, including real reviewed ledger roundtrip."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import vrs_rc_snapshot as s
import test_vrs_runtime as fixture

class SnapshotTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.home=Path(tmp.name)
        self.root=self.home/'app';self.root.mkdir()
        (self.root/'empty').mkdir();(self.root/'config').mkdir();(self.root/'config'/'private').write_bytes(b'private-fixture')
        self.bundle=self.home/'backup';self.out=self.home/'restore'

    def test_exact_roundtrip_no_overwrite(self):
        a=s.snapshot(self.root,self.bundle);h=a['manifest_sha256']
        self.assertEqual(s.verify(self.bundle,h)['inventory']['files']['config/private']['bytes'],15)
        (self.root/'config/private').write_bytes(b'new')
        self.assertEqual(s.restore(self.bundle,self.out,h)['status'],'RESTORE_PASS')
        self.assertEqual((self.out/'app/config/private').read_bytes(),b'private-fixture')
        self.assertTrue((self.out/'app/empty').is_dir());self.assertEqual((self.root/'config/private').read_bytes(),b'new')
        with self.assertRaises(ValueError):s.restore(self.bundle,self.out,h)
        with self.assertRaises(ValueError):s.snapshot(self.root,self.root/'nested')

    def test_approved_digest_and_payload_tamper(self):
        h=s.snapshot(self.root,self.bundle)['manifest_sha256']
        with self.assertRaises(ValueError):s.verify(self.bundle,'0'*64)
        (self.bundle/'payload/config/private').write_bytes(b'tamper')
        with self.assertRaises(ValueError):s.restore(self.bundle,self.out,h)
        self.assertFalse(self.out.exists())

    def test_refuse_hardlink_and_interrupted_copy(self):
        import os
        os.link(self.root/'config/private',self.root/'alias')
        with self.assertRaises(ValueError):s.snapshot(self.root,self.bundle)
        (self.root/'alias').unlink()
        with patch.object(s,'copy_tree',side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):s.snapshot(self.root,self.bundle)
        self.assertFalse(self.bundle.exists())

    def test_real_reviewed_workspace_roundtrip(self):
        f=fixture.RuntimeTests();f.setUp();self.addCleanup(f.doCleanups)
        run=f.run_to_review();item=f.app.review_items(run)['items'][0]
        f.app.submit(f.decision(run,item,'deferred'));item=f.app.review_items(run)['items'][0];f.app.submit(f.decision(run,item,'glyph'))
        a=s.inspect(f.root);h=s.snapshot(f.root,self.bundle)['manifest_sha256']
        s.restore(self.bundle,self.out,h);b=s.inspect(self.out/'app')
        self.assertEqual(a,b);self.assertEqual(b['counts']['decision_revisions'],2)
        self.assertEqual(s.inspect(f.root),a)

    def test_active_ledger_refused(self):
        f=fixture.RuntimeTests();f.setUp();self.addCleanup(f.doCleanups)
        run=f.app.register(f.m);token=f.app.ledger.claim(run)
        try:
            with self.assertRaises(ValueError):s.snapshot(f.root,self.bundle)
            self.assertFalse(self.bundle.exists())
        finally:f.app.ledger.release(run,token)

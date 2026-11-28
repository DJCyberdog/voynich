"""Hosted disposable source/state migration fixture, not a native installation."""
import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

import vrs_rc2_migration as migration
import vrs_rc_snapshot as snap
import vrs_source_update as source
from vrs_build_portable import source_payload
from vrs_ledger import Ledger
from vrs_portable import digest


@unittest.skipUnless(os.environ.get('VRS_RC1_SOURCE'),'explicit immutable RC1 checkout required')
class CandidateFixture(unittest.TestCase):
    def test_exact_source_and_retained_state(self):
        old=source_payload(Path(os.environ['VRS_RC1_SOURCE']))
        self.assertEqual(source.blob(old[source.MANIFEST]),source.RC1_BASE_BLOB)
        new=source_payload(Path(__file__).resolve().parent)
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp).resolve();root=home/'rc1';root.mkdir()
            for name,data in old.items():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            sentinels={'data/pinned.pdf':b'fixture source','models/glyph.bin':b'fixture model','workspace/review.json':b'fixture review','config/private.json':b'fixture config','workspace/outbox/report.json':b'fixture outbox'}
            generated={'runtime/cuda/python.exe':b'old runtime','.venv/cuda/Scripts/python.exe':b'old venv','bootstrap/python.exe':b'old bootstrap','cache/downloads/wheel':b'old wheel','config/install-cuda.json':b'{}','config/bootstrap-origin.json':b'{}'}
            for name,data in {**sentinels,**generated}.items():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            (root/'config/portable.json').write_text(json.dumps(dict(schema=1,profile='cuda',root=str(root),plan='config/install-cuda.json',sha256=digest(root/'config/install-cuda.json'))),encoding='utf-8')
            db=root/'workspace/vrs095/ledger.sqlite';db.parent.mkdir();Ledger(root,db)
            logical=snap.preflight(root);self.assertIsNotNone(logical)
            archive=home/'candidate.zip'
            with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
                for name,data in new.items():z.writestr(source.PREFIX+name,data)
            snapshot=home/'snapshot';approved=snap.snapshot(root,snapshot)['manifest_sha256']
            baseline=snap.scan(root,snap.LOCKS)
            target=hashlib.sha256(new[source.MANIFEST]).hexdigest()
            out=home/'candidate';report=migration.prepare(snapshot,approved,archive,digest(archive),target,out)
            self.assertEqual(report['status'],'CANDIDATE_PREPARED');self.assertFalse(report['execution_authorized']);self.assertTrue(report['setup_required'])
            self.assertEqual(source.installed(out/'app')[0],new)
            self.assertEqual(snap.preflight(out/'app'),logical)
            for name,data in sentinels.items():self.assertEqual((out/'app'/name).read_bytes(),data)
            for name in (*generated,'config/portable.json'):self.assertFalse((out/'app'/name).exists())
            self.assertEqual(snap.scan(root,snap.LOCKS),baseline)
            self.assertEqual(snap.verify(snapshot,approved)['inventory'],baseline)
            with self.assertRaisesRegex(ValueError,'wrong target manifest'):
                migration.prepare(snapshot,approved,archive,digest(archive),'0'*64,home/'wrong')
            self.assertFalse((home/'wrong').exists())
            self.assertEqual(snap.scan(root,snap.LOCKS),baseline)
            print(json.dumps(dict(status='PASS',counts=report['counts'],empty_sqlite_ledger_preserved=True,native_installation=False,activation=False)),flush=True)

if __name__=='__main__':unittest.main()

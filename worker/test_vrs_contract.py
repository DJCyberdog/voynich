import json
import tempfile
import unittest
from pathlib import Path

import vrs_contract as c
from vrs_core import sha


class ContractTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.m = dict(schema=1, module=c.MODULE, protocol=c.PROTOCOL, backend='cpu', seed=7, run_nonce='1'*32,
                      inputs={role: self.file(role) for role in c.ROLES}, transcriptions=[self.file('eva'), self.file('sta')])
        self.run = c.manifest(self.root, self.m)
        self.r = {s: dict(schema=1, run_id=self.run, stage=s, state='PENDING', reason='NOT_STARTED',
                          artifact=None, counts=None) for s in c.STAGES}

    def file(self, name):
        p = self.root / name
        p.write_text('private fixture ' + name)
        return dict(path=name, sha256=sha(p))

    def complete(self, stage, counts=None):
        self.r[stage].update(state='COMPLETED', reason='NONE', artifact=self.file(stage), counts=counts)

    def classify(self):
        self.complete('script_regions')
        self.complete('glyph_segmentation')
        self.complete('glyph_classification', dict(total=7, accepted=4, abstained=2, failed=1))

    def args(self):
        return (self.root, self.m, self.r, 'DJCyberdog/voynich', 'a'*40, {'DJCyberdog/voynich'}, 'cpu', 'b'*64)

    def report(self):
        return c.evidence(*self.args())

    def test_no_job_required_and_stable_evidence(self):
        self.classify()
        self.complete('exception_review', dict(resolved=2, pending=0, deferred=0))
        self.complete('transcription_alignment')
        report = self.report()
        self.assertEqual(report['technical_status'], 'COMPLETED')
        self.assertEqual(report['scientific_status'], 'UNADJUDICATED')
        self.assertEqual(c.verify_evidence(report, *self.args()), c.digest(self.report()))
        raw = c.canonical(report)
        self.assertNotIn(b'private fixture', raw)
        self.assertNotIn(b'"path"', raw)
        self.assertNotIn(str(self.root).encode(), raw)

    def test_partial_and_pending_reviews(self):
        self.classify()
        self.assertEqual(self.report()['review'], dict(resolved=0, pending=2, deferred=0))
        self.r['exception_review'].update(state='BLOCKED', reason='REVIEW_PENDING', artifact=self.file('review'),
                                          counts=dict(resolved=1, pending=0, deferred=1))
        self.assertEqual(self.report()['technical_status'], 'PARTIAL')
        self.assertEqual(self.report()['review']['deferred'], 1)
        self.complete('transcription_alignment')
        with self.assertRaisesRegex(ValueError, 'dependency'):
            self.report()

    def test_scope_and_version_fail_closed(self):
        for key, val in [('schema', 2), ('schema', True), ('module', 'autonomous-experiments'),
                         ('protocol', 'new-hypothesis'), ('command', 'shell'), ('experiment', 'EXP-9999')]:
            bad = dict(self.m, **{key: val})
            with self.assertRaises(ValueError):
                c.manifest(self.root, bad)

    def test_tampered_artifacts_and_binding(self):
        self.classify()
        self.r['glyph_classification']['run_id'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'binding'):
            self.report()
        self.r['glyph_classification']['run_id'] = self.run
        (self.root / 'glyph_classification').write_text('modified')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.report()
        (self.root / 'manuscript').write_text('modified')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.report()

    def test_path_and_alias_rejection(self):
        ref = self.m['inputs']['manuscript']
        for name in ('../outside', '/tmp/file', 'C:/file', 'a\\b', 'a//b', './manuscript'):
            with self.assertRaises(ValueError):
                c.artifact(self.root, dict(ref, path=name))
        (self.root / 'link').symlink_to(self.root / 'manuscript')
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            c.artifact(self.root, dict(ref, path='link'))
        self.m['inputs']['groups'] = ref
        with self.assertRaisesRegex(ValueError, 'Aliased'):
            c.manifest(self.root, self.m)

    def test_invalid_counts_and_receipts(self):
        self.classify()
        self.r['glyph_classification']['counts']['accepted'] = True
        with self.assertRaises(ValueError):
            self.report()
        self.r['glyph_classification']['counts']['accepted'] = 5
        with self.assertRaisesRegex(ValueError, 'denominator'):
            self.report()
        self.r['glyph_classification']['counts']['accepted'] = 4
        self.complete('exception_review', dict(resolved=3, pending=0, deferred=0))
        with self.assertRaisesRegex(ValueError, 'denominator'):
            self.report()

    def test_repo_and_backend_isolation(self):
        args = list(self.args())
        args[3] = 'other/repo'
        with self.assertRaisesRegex(ValueError, 'not locally authorized'):
            c.evidence(*args)
        args = list(self.args())
        args[6] = 'cuda'
        with self.assertRaisesRegex(ValueError, 'Backend mismatch'):
            c.evidence(*args)

    def test_report_tamper_and_private_field(self):
        for key, value in [('scientific_status', 'PASS'), ('local_path', str(self.root)), ('seed', True)]:
            report = dict(self.report(), **{key: value})
            with self.assertRaisesRegex(ValueError, 'Evidence mismatch'):
                c.verify_evidence(report, *self.args())

    def test_json_bounds_duplicates_and_constants(self):
        p = self.root / 'bad.json'
        for raw in (b'{"schema":1,"schema":2}', b'{"x":NaN}', b' '* (c.MAX_JSON + 1)):
            p.write_bytes(raw)
            with self.assertRaises(ValueError):
                c.load(p)
        p.write_text(json.dumps(self.m))
        self.assertEqual(c.load(p), self.m)

    def test_replica_identity_and_stage_alias(self):
        replica = dict(self.m, run_nonce='2'*32)
        self.assertNotEqual(c.manifest(self.root, replica), self.run)
        self.complete('script_regions')
        self.r['script_regions']['artifact'] = self.m['inputs']['manuscript']
        with self.assertRaisesRegex(ValueError, 'aliases'):
            self.report()

    def test_failed_not_promoted(self):
        self.r['script_regions'].update(state='FAILED', reason='PROCESSING_ERROR')
        report = self.report()
        self.assertEqual(report['technical_status'], 'FAILED')
        self.assertEqual(report['scientific_status'], 'UNADJUDICATED')
        self.assertIsNone(report['classification'])


if __name__ == '__main__':
    unittest.main()

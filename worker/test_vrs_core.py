"""Golden local data contracts and lightweight review import checks."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import vrs_core as core


class CoreContractTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.crop = self.root / 'crop.bin'
        self.crop.write_bytes(b'golden crop bytes')
        self.manifest = self.root / 'manifest.json'
        self.row = {'id': 'r1', 'group': 'leaf1', 'file': 'crop.bin',
                    'sha256': hashlib.sha256(b'golden crop bytes').hexdigest()}

    def test_json_golden(self):
        dest = self.root / 'nested' / 'result.json'
        core.write(dest, {'z': 3, 'a': [True, None, 'EVA']})
        self.assertEqual(dest.read_bytes(), b'{\n  "a": [\n    true,\n    null,\n    "EVA"\n  ],\n  "z": 3\n}\n')
        self.assertEqual(core.read(dest), {'a': [True, None, 'EVA'], 'z': 3})
        with self.assertRaises(ValueError):
            core.write(dest, {'invalid': float('nan')})
        self.assertEqual(core.read(dest)['z'], 3)

    def test_dataset_and_tamper(self):
        obj = {'schema': 1, 'regions': [self.row]}
        core.write(self.manifest, obj)
        self.assertEqual(core.dataset(self.manifest), obj)
        self.crop.write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'Crop hash mismatch'):
            core.dataset(self.manifest)

    def test_duplicate_empty_group_and_escape(self):
        for rows, msg in [([], 'Duplicate/empty'), ([self.row, self.row], 'Duplicate/empty'),
                          ([dict(self.row, group=' ')], 'Missing group'),
                          ([dict(self.row, file='../outside')], 'Path escapes')]:
            core.write(self.manifest, {'regions': rows})
            with self.assertRaisesRegex(ValueError, msg):
                core.dataset(self.manifest)

    def test_core_import_without_ml(self):
        code = '''import sys
class Block:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'worker','torch','numpy','fitz','PIL','tkinter'}:
            raise ImportError('blocked '+fullname)
sys.meta_path.insert(0, Block())
import vrs_core
assert vrs_core.sha and vrs_core.dataset
'''
        subprocess.run([sys.executable, '-c', code], cwd=Path(core.__file__).parent, check=True)

    def test_legacy_source_parity(self):
        legacy = Path(core.__file__).with_name('worker.py')
        if not legacy.exists():
            self.skipTest('legacy worker checkout unavailable')
        def defs(path):
            return {n.name: ast.dump(n, include_attributes=False)
                    for n in ast.parse(path.read_text(encoding='utf-8')).body
                    if isinstance(n, ast.FunctionDef)}
        previous, current = defs(legacy), defs(Path(core.__file__))
        for name in ('require', 'sha', 'read', 'write', 'within', 'dataset'):
            self.assertEqual(current[name], previous[name], name)

    def test_review_import_without_compute(self):
        root = Path(core.__file__).parent
        names = ('active_review', 'review_groups', 'review_client', 'tray_client')
        if not all((root / (name + '.py')).exists() for name in names):
            self.skipTest('review checkout unavailable')
        code = '''import sys
class Block:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'worker','torch','numpy','fitz','glyphs','pipeline','bridge','validation'}:
            raise ImportError('blocked '+fullname)
sys.meta_path.insert(0, Block())
import active_review, review_groups, review_client, tray_client
assert all(m.w.__name__ == 'vrs_core' for m in (active_review,review_groups,review_client,tray_client))
'''
        subprocess.run([sys.executable, '-c', code], cwd=root, check=True)


if __name__ == '__main__':
    unittest.main()

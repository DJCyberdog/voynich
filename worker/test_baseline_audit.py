import tempfile
import unittest
from pathlib import Path
from baseline_audit import audit, blob_sha


class BaselineAuditTest(unittest.TestCase):
    def test_identity_and_import_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            data = b'import os\nfrom pathlib import Path\ndef test_example(): pass\n'
            (root / 'test_demo.py').write_bytes(data)
            result = audit(root, {'schema': 1, 'files': {'test_demo.py': blob_sha(data)}})
            self.assertEqual(result['status'], 'MATCH')
            self.assertEqual(result['test_functions'], 1)
            self.assertEqual(result['files'][0]['imports'], ['os', 'pathlib'])

    def test_missing_changed_and_additional(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'a.py').write_text('bad syntax !')
            (root / 'extra.py').touch()
            result = audit(root, {'schema': 1, 'files': {'a.py': blob_sha(b''), 'b.py': blob_sha(b'')}})
            self.assertEqual(result['status'], 'NOT_MATCH')
            self.assertEqual([x['status'] for x in result['files']], ['CHANGED', 'MISSING'])
            self.assertIn('syntax_error', result['files'][0])
            self.assertEqual(result['additional_python_files'], ['extra.py'])

    def test_reject_path_and_schema(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ('../private', '/etc/passwd', 'a\\b'):
                with self.assertRaises(ValueError):
                    audit(d, {'schema': 1, 'files': {name: blob_sha(b'')}})
            with self.assertRaises(ValueError):
                audit(d, {'schema': 2, 'files': {}})

    def test_git_blob_known_empty(self):
        self.assertEqual(blob_sha(b''), 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391')


if __name__ == '__main__':
    unittest.main()

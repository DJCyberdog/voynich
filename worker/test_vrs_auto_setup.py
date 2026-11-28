import hashlib,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import vrs_auto_setup as a
from vrs_portable import save

class AutoSetupTests(unittest.TestCase):
    def test_fixed_profile(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(ValueError):a.profile_for(root,None)
            self.assertEqual(a.profile_for(root,'review'),'review')
            save(root/'data/rc1/trial/run.json',{'backend':'cuda'})
            self.assertEqual(a.profile_for(root,None),'cuda')
            with self.assertRaises(ValueError):a.profile_for(root,'cpu')

    def test_archive_pin(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);raw=b'fixture'
            with patch.dict(a.BOOTSTRAP,sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),file='fixture.tar.gz'):
                p=root/'cache/downloads'/a.BOOTSTRAP['sha256']/a.BOOTSTRAP['file'];p.parent.mkdir(parents=True);p.write_bytes(raw)
                self.assertEqual(a.verify_archive(root),p);p.write_bytes(b'changed')
                with self.assertRaises(ValueError):a.verify_archive(root)

    def test_runtime_layout(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);base=root/'python';base.mkdir()
            for name in ('python.exe','python313.dll','Lib/venv/__init__.py','Lib/ensurepip/__init__.py','tcl/tk.tcl','LICENSE.txt','DLLs/_tkinter.pyd','Lib/site-packages/pip/__init__.py'):
                p=base/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fixture')
            z=root/'runtime.zip';a.runtime_zip(base,z)
            with zipfile.ZipFile(z) as f:
                self.assertEqual(f.read('LICENSE.txt'),b'fixture')
                self.assertIn('tcl/tk.tcl',f.namelist());self.assertIn('Lib/site-packages/pip/__init__.py',f.namelist())
            (base/'python313.dll').unlink()
            with self.assertRaises(ValueError):a.runtime_zip(base,root/'bad.zip')

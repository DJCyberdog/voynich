import hashlib,tempfile,unittest,zipfile
from pathlib import Path
from vrs_native_acceptance import assemble_runtime,source_copy
from vrs_portable import save

class NativeHarness(unittest.TestCase):
    def test_runtime_allowlist(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);base=root/'runtime';base.mkdir()
            for n in ('python.exe','python313.dll','Lib/venv/x.py','Lib/ensurepip/x.py','DLLs/_tkinter.pyd','tcl/tk.tcl','Lib/site-packages/secret.py','secret.ini'):
                p=base/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fixture')
            z=root/'runtime.zip';assemble_runtime(base,z)
            with zipfile.ZipFile(z) as f:self.assertEqual(set(f.namelist()),{'python.exe','python313.dll','Lib/venv/x.py','Lib/ensurepip/x.py','DLLs/_tkinter.pyd','tcl/tk.tcl'})
            (base/'DLLs/_tkinter.pyd').unlink()
            with self.assertRaises(ValueError):assemble_runtime(base,root/'bad.zip')
    def test_source_copy(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);s=r/'source';s.mkdir();out=r/'app';out.mkdir();b=b'print(1)\n';(s/'a.py').write_bytes(b);(s/'private.txt').write_text('secret');save(s/'portable_sources.json',{'schema':1,'files':{'a.py':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}})
            source_copy(s,out);self.assertEqual((out/'a.py').read_bytes(),b);self.assertFalse((out/'private.txt').exists());(s/'a.py').write_bytes(b'changed')
            with self.assertRaises(ValueError):source_copy(s,out)

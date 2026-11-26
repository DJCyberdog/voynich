import tempfile,unittest,zipfile
from pathlib import Path
from vrs_prepare_plan import prepare,wheel_identity
from vrs_portable import plan,acquire

class TestPlan(unittest.TestCase):
    def test_offline_lock(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); w=root/'input';w.mkdir(); r=w/'python.zip'
            with zipfile.ZipFile(r,'w') as z:z.writestr('python.exe',b'fixture')
            for n,v in [('pillow','12.3.0'),('psutil','7.2.2')]:
                with zipfile.ZipFile(w/f'{n}-{v}-cp313-cp313-win_amd64.whl','w') as z:z.writestr(f'{n}-{v}.dist-info/METADATA',f'Name: {n}\nVersion: {v}\n')
            result=prepare(root,'review',r,w);self.assertEqual(result['approval'],'NOT_APPROVED');p=plan(root,'review',result['plan'],result['sha256']);self.assertEqual(len(p['wheels']),2);self.assertTrue(acquire(root,p['runtime']).exists())
            with self.assertRaises(ValueError):prepare(root,'review',r,w)
    def test_foreign_or_mismatched_wheel(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ('pillow-12.3.0-cp313-cp313-manylinux_x86_64.whl','pillow-12.3.0-cp313-cp313-win_amd64.whl'):
                p=Path(d)/name
                with zipfile.ZipFile(p,'w') as z:z.writestr('pillow-12.3.0.dist-info/METADATA','Name: other\nVersion: 12.3.0\n')
                with self.assertRaises(ValueError):wheel_identity(p)

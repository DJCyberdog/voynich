import hashlib,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import vrs_source_update as u
from vrs_portable import save,digest

class SourceUpdate(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)/'app';self.root.mkdir();self.old={'a.py':b'old','old.py':b'remove','Update.bat':b'fixed','requirements-review.txt':b'fixed'};self.new={'a.py':b'new','new.py':b'added','Update.bat':b'fixed','requirements-review.txt':b'fixed'}
        for n,b in self.old.items():(self.root/n).write_bytes(b)
        save(self.root/u.MANIFEST,{'schema':1,'files':{n:u.blob(b) for n,b in self.old.items()}})
        (self.root/'workspace').mkdir();(self.root/'workspace/state').write_bytes(b'preserve');(self.root/'config').mkdir();(self.root/'config/secret').write_bytes(b'private')
    def package(self,files=None,extra=None):
        import json
        files=self.new if files is None else files;p=Path(self.tmp.name)/'update.zip'
        with zipfile.ZipFile(p,'w') as z:
            for n,b in files.items():z.writestr(u.PREFIX+n,b)
            z.writestr(u.PREFIX+u.MANIFEST,json.dumps({'schema':1,'files':{n:u.blob(b) for n,b in files.items()}},sort_keys=True))
            if extra:z.writestr(u.PREFIX+extra,b'evil')
        return p,digest(p)
    def test_update_replay_state(self):
        (self.root/'cache/pyc').mkdir(parents=True);(self.root/'cache/pyc/old.pyc').write_bytes(b'old');p,h=self.package();self.assertEqual(u.update(self.root,p,h)['status'],'UPDATED');self.assertFalse((self.root/'cache/pyc').exists());self.assertEqual(u.installed(self.root)[1],{n:u.blob(b) for n,b in self.new.items()});self.assertFalse((self.root/'old.py').exists());self.assertEqual((self.root/'workspace/state').read_bytes(),b'preserve');self.assertEqual((self.root/'config/secret').read_bytes(),b'private');self.assertEqual(u.update(self.root,p,h)['status'],'UNCHANGED')
    def test_refuse_tamper_collision_private_and_dependency(self):
        p,h=self.package()
        with self.assertRaises(ValueError):u.update(self.root,p,'0'*64)
        (self.root/'new.py').write_bytes(b'user')
        with self.assertRaises(ValueError):u.update(self.root,p,h)
        (self.root/'new.py').unlink()
        for n in ('workspace/private.py','../evil.py','requirements-review.txt','Update.bat','vrs_source_update.py','vrs_portable.py'):
            files=dict(self.new);files[n]=b'changed';p,h=self.package(files)
            with self.assertRaises(ValueError):u.update(self.root,p,h)
        p,h=self.package(extra='unlisted.py')
        with self.assertRaises(ValueError):u.update(self.root,p,h)
        (self.root/'a.py').write_bytes(b'user changed');p,h=self.package()
        with self.assertRaises(ValueError):u.update(self.root,p,h)
    def test_bootstrap_launcher_fence(self):
        files=dict(self.new,**{'Setup-Auto.ps1':b'# fixture','vrs_auto_setup.py':b'# fixture'})
        p,h=self.package(files)
        self.assertIn('Setup-Auto.ps1',u.read_bundle(p,h)[1])
        with self.assertRaisesRegex(ValueError,'full package migration'):u.update(self.root,p,h)
        self.assertFalse(u.pending(self.root))
        self.assertEqual((self.root/'workspace/state').read_bytes(),b'preserve')
        files['Other.ps1']=b'# unmanaged'
        p,h=self.package(files)
        with self.assertRaises(ValueError):u.read_bundle(p,h)

    def test_rollback_on_failure(self):
        p,h=self.package();original=u.write;failed=[False]
        def fail_once(path,data):
            if path==self.root/'new.py' and not failed[0]:failed[0]=True;raise OSError('simulated failure')
            original(path,data)
        with patch.object(u,'write',side_effect=fail_once):
            with self.assertRaises(OSError):u.update(self.root,p,h)
        self.assertFalse(u.pending(self.root));self.assertEqual(u.installed(self.root)[1],{n:u.blob(b) for n,b in self.old.items()})
    def test_interrupted_recovery_and_external_edit(self):
        p,h=self.package();original=u.write
        def fail(path,data):
            if path==self.root/'new.py':raise OSError('failure')
            original(path,data)
        with patch.object(u,'write',side_effect=fail),patch.object(u,'rollback',side_effect=OSError('interrupted rollback')):
            with self.assertRaises(OSError):u.update(self.root,p,h)
        self.assertTrue(u.pending(self.root))
        with self.assertRaises(ValueError):
            with u.exclusive(self.root):pass
        (self.root/'a.py').write_bytes(b'external')
        with self.assertRaises(ValueError):u.recover(self.root)
        (self.root/'a.py').write_bytes(b'new');self.assertEqual(u.recover(self.root)['status'],'ROLLED_BACK');self.assertEqual(u.installed(self.root)[1],{n:u.blob(b) for n,b in self.old.items()})
    def test_managed_worker_stop_gate(self):
        save(self.root/'workspace/vrs101/session.json',{'state':'RUNNING'});p,h=self.package()
        with self.assertRaises(ValueError):u.update(self.root,p,h)

    def test_cli_update_and_recovery_gate(self):
        import sys
        from vrs_portable import main
        p,h=self.package()
        with patch.object(sys,'argv',['vrs_portable.py','update','--root',str(self.root),'--source',str(p),'--approve',h]):self.assertEqual(main(),0)
        self.assertEqual((self.root/'a.py').read_bytes(),b'new')
        save(self.root/u.JOURNAL,{'schema':1})
        with patch.object(sys,'argv',['vrs_portable.py','start','--root',str(self.root)]):self.assertEqual(main(),1)

import hashlib,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import vrs_source_update as u
from vrs_portable import save,digest

class SourceUpdate(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)/'app';self.root.mkdir();self.root=self.root.resolve(strict=True);self.old={'a.py':b'old','old.py':b'remove','Update.bat':b'fixed','requirements-review.txt':b'fixed'};self.new={'a.py':b'new','new.py':b'added','Update.bat':b'fixed','requirements-review.txt':b'fixed'}
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
            if path.name=='new.py' and path.parent.samefile(self.root) and not failed[0]:failed[0]=True;raise OSError('simulated failure')
            original(path,data)
        with patch.object(u,'write',side_effect=fail_once):
            with self.assertRaises(OSError):u.update(self.root,p,h)
        self.assertFalse(u.pending(self.root));self.assertEqual(u.installed(self.root)[1],{n:u.blob(b) for n,b in self.old.items()})
    def test_interrupted_recovery_and_external_edit(self):
        p,h=self.package();original=u.write
        def fail(path,data):
            if path.name=='new.py' and path.parent.samefile(self.root):raise OSError('failure')
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


    def rc2_fixture(self):
        self.old['vrs_source_update.py']=b'# frozen RC1 updater'
        self.new['vrs_source_update.py']=Path(u.__file__).read_bytes()
        (self.root/'vrs_source_update.py').write_bytes(self.old['vrs_source_update.py'])
        save(self.root/u.MANIFEST,{'schema':1,'files':{n:u.blob(b) for n,b in self.old.items()}})
        self.base_bytes=(self.root/u.MANIFEST).read_bytes()
        pin=patch.object(u,'RC1_BASE_BLOB',u.blob(self.base_bytes))
        pin.start();self.addCleanup(pin.stop)
        for n in ('data/rc1/source','bootstrap/python.exe','.venv/cuda/Scripts/python.exe','runtime/cuda/python.exe','cache/downloads/wheel','workspace/ledger','workspace/outbox','config/portable.json'):
            p=self.root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(n.encode())
        p,h=self.package();new,_=u.read_bundle(p,h)
        self.target_bytes=new[u.MANIFEST]
        return p,h,u.sha256(self.base_bytes),u.sha256(self.target_bytes)

    def assert_rc2_state(self,raw):
        self.assertEqual((self.root/u.MANIFEST).read_bytes(),raw)
        u.installed(self.root)
        for n in ('data/rc1/source','bootstrap/python.exe','.venv/cuda/Scripts/python.exe','runtime/cuda/python.exe','cache/downloads/wheel','workspace/ledger','workspace/outbox','config/portable.json'):
            self.assertEqual((self.root/n).read_bytes(),n.encode())
        self.assertEqual((self.root/'workspace/state').read_bytes(),b'preserve')
        self.assertEqual((self.root/'config/secret').read_bytes(),b'private')

    def test_rc2_pinned_update_and_post_success_rollback(self):
        a=self.rc2_fixture()
        result=u.apply_rc2(self.root,*a)
        self.assertEqual(result['status'],'UPDATED');self.assertTrue(result['rollback_retained'])
        self.assert_rc2_state(self.target_bytes);self.assertFalse(u.pending(self.root))
        with self.assertRaises(ValueError):u.update(self.root,a[0],a[1])
        self.assertEqual(u.rollback_rc2(self.root)['status'],'ROLLED_BACK')
        self.assert_rc2_state(self.base_bytes);self.assertFalse(u.pending(self.root))
        self.assertEqual(u.rollback_rc2(self.root)['status'],'ALREADY_ROLLED_BACK')
        self.assertEqual(u.apply_rc2(self.root,*a)['status'],'UPDATED')
        self.assert_rc2_state(self.target_bytes)

    def test_rc2_wrong_base_target_archive_and_staged_code(self):
        p,h,b,t=self.rc2_fixture()
        for args in ((p,h,'0'*64,t),(p,h,b,'0'*64),(p,'0'*64,b,t)):
            with self.assertRaises(ValueError):u.apply_rc2(self.root,*args)
            self.assert_rc2_state(self.base_bytes);self.assertFalse(u.pending(self.root))
        with patch.object(u,'RC1_BASE_BLOB','0'*40):
            with self.assertRaisesRegex(ValueError,'Wrong RC1'):u.apply_rc2(self.root,p,h,b,t)
        self.new['vrs_source_update.py']=b'wrong staged updater';p,h=self.package()
        new,_=u.read_bundle(p,h)
        with self.assertRaisesRegex(ValueError,'Staged updater'):u.apply_rc2(self.root,p,h,b,u.sha256(new[u.MANIFEST]))
        self.assert_rc2_state(self.base_bytes);self.assertFalse(u.pending(self.root))

    def test_rc2_low_space_and_running_worker(self):
        from types import SimpleNamespace
        a=self.rc2_fixture()
        with patch('shutil.disk_usage',return_value=SimpleNamespace(free=0)):
            with self.assertRaisesRegex(ValueError,'Insufficient free'):u.apply_rc2(self.root,*a)
        save(self.root/'workspace/vrs101/session.json',{'state':'RUNNING'})
        with self.assertRaisesRegex(ValueError,'Stop managed worker'):u.apply_rc2(self.root,*a)
        self.assert_rc2_state(self.base_bytes);self.assertFalse(u.pending(self.root))
        save(self.root/'workspace/vrs101/session.json',{'state':'STOPPED'})
        with u.exclusive(self.root):
            with self.assertRaisesRegex(ValueError,'busy'):u.apply_rc2(self.root,*a)
        self.assert_rc2_state(self.base_bytes)

    def test_rc2_permission_failure_before_journal(self):
        a=self.rc2_fixture();original=u.write
        def fail(path,data):
            if 'backup' in path.parts:raise PermissionError('denied backup')
            original(path,data)
        with patch.object(u,'write',side_effect=fail):
            with self.assertRaises(PermissionError):u.apply_rc2(self.root,*a)
        self.assert_rc2_state(self.base_bytes);self.assertFalse(u.pending(self.root))
        self.assertEqual(u.apply_rc2(self.root,*a)['status'],'UPDATED')

    def test_rc2_interrupted_transaction_recover_and_retry(self):
        a=self.rc2_fixture();original=u.write
        def fail(path,data):
            if path.name=='new.py' and path.parent.samefile(self.root):raise OSError('simulated disk failure')
            original(path,data)
        with patch.object(u,'write',side_effect=fail),patch.object(u,'rollback',side_effect=OSError('interrupted recovery')):
            with self.assertRaises(OSError):u.apply_rc2(self.root,*a)
        self.assertTrue(u.pending(self.root))
        with self.assertRaises(ValueError):
            with u.exclusive(self.root):pass
        self.assertEqual(u.recover(self.root)['status'],'ROLLED_BACK')
        self.assert_rc2_state(self.base_bytes);self.assertFalse(u.pending(self.root))
        self.assertEqual(u.apply_rc2(self.root,*a)['status'],'UPDATED')
        self.assert_rc2_state(self.target_bytes)

    def test_rc2_rollback_refuses_tamper(self):
        a=self.rc2_fixture();u.apply_rc2(self.root,*a)
        (self.root/'a.py').write_bytes(b'external modification')
        with self.assertRaises(ValueError):u.rollback_rc2(self.root)
        self.assertFalse(u.pending(self.root))
        (self.root/'a.py').write_bytes(self.new['a.py'])
        backup=self.root/'workspace/source-update/backup/a.py'
        backup.write_bytes(b'bad backup')
        with self.assertRaisesRegex(ValueError,'backup mismatch'):u.rollback_rc2(self.root)
        self.assert_rc2_state(self.target_bytes);self.assertTrue(u.pending(self.root))
        backup.write_bytes(self.old['a.py'])
        self.assertEqual(u.recover(self.root)['status'],'ROLLED_BACK')
        self.assert_rc2_state(self.base_bytes)

    def test_rc2_reject_other_launcher_change(self):
        p,h,b,t=self.rc2_fixture()
        self.new['Update.bat']=b'changed';p,h=self.package();new,_=u.read_bundle(p,h)
        with self.assertRaisesRegex(ValueError,'full package migration'):u.apply_rc2(self.root,p,h,b,u.sha256(new[u.MANIFEST]))
        self.assert_rc2_state(self.base_bytes);self.assertFalse(u.pending(self.root))

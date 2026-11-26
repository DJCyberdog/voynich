import hashlib
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
import vrs_portable as p
import vrs_portable_logs as logs
import vrs_portable_secrets as secrets
from vrs_build_portable import build

class TestPortable(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='VRS portable ü '); self.root=Path(self.tmp.name); p.environment(self.root)
    def tearDown(self):self.tmp.cleanup()
    def asset(self,name,data):
        sha=hashlib.sha256(data).hexdigest(); x=p.local(self.root,'cache/downloads/'+sha+'/'+name); x.parent.mkdir(parents=True,exist_ok=True); x.write_bytes(data); return dict(file=name,sha256=sha,size=len(data),url='https://files.pythonhosted.org/'+name)
    def make_plan(self):
        z=self.root/'runtime-fixture.zip'
        with zipfile.ZipFile(z,'w') as f:f.writestr('python.exe',b'fixture')
        runtime=self.asset('python.zip',z.read_bytes()); wheels=[self.asset(n+'.whl',n.encode()) for n in ('pillow','psutil')]; v=dict(schema=1,profile='review',runtime=runtime,wheels=wheels,requirements=[f'{n}=={ver} --hash=sha256:{w["sha256"]}' for n,ver,w in zip(('pillow','psutil'),('12.3.0','7.2.2'),wheels)],runtime_python='python.exe'); path=self.root/'config/plan.json'; p.save(path,v); return v,p.digest(path)
    def test_paths_environment(self):
        with patch.dict(os.environ,{'PYTHONPATH':'outside','VRS_GITHUB_TOKEN_TEST':'SECRET','PIP_INDEX_URL':'evil'}):e=p.environment(self.root)
        for k in ('TEMP','HF_HOME','TORCH_HOME','CUDA_CACHE_PATH','PYTHONPYCACHEPREFIX','HOME'):self.assertTrue(Path(e[k]).is_relative_to(self.root))
        self.assertNotIn('VRS_GITHUB_TOKEN_TEST',e);self.assertNotIn('PYTHONPATH',e);self.assertNotIn('PIP_INDEX_URL',e)
        for name in ('../evil','/evil','a\\b','C:/a','a/../b','NUL.txt','file:stream','a/.. ','a//b'):
            with self.assertRaises(ValueError):p.local(self.root,name)
        (self.root/'link').symlink_to(self.root/'temp',target_is_directory=True)
        with self.assertRaises(ValueError):p.local(self.root,'link/file')
    def test_archive_guards(self):
        for name in ('../outside','/outside','CON'):
            z=self.root/'bad.zip'; out=self.root/'out';out.mkdir(exist_ok=True)
            with zipfile.ZipFile(z,'w') as f:f.writestr(name,b'a')
            with self.subTest(name=name),self.assertRaises(ValueError):p.extract(z,out)
        # ZipInfo normalizes backslashes on Windows when writing; create the raw
        # hostile member in both ZIP headers instead of testing a sanitized name.
        for raw in (b'a\\b',b'a\x00b'):
            with zipfile.ZipFile(z,'w') as f:f.writestr('a/b',b'x')
            data=z.read_bytes();self.assertEqual(data.count(b'a/b'),2);z.write_bytes(data.replace(b'a/b',raw))
            with self.subTest(raw=raw),self.assertRaises(ValueError):p.extract(z,out)
        self.assertEqual(list(out.iterdir()),[])
        with zipfile.ZipFile(z,'w') as f:f.writestr('A',b'a');f.writestr('a',b'b')
        with self.assertRaises(ValueError):p.extract(z,out)
        with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as f:f.writestr('bomb',b'\0'*2*1024**2)
        with self.assertRaises(ValueError):p.extract(z,out)
        with zipfile.ZipFile(z,'w') as f:f.writestr('bin/x',b'abc')
        p.extract(z,out);self.assertEqual((out/'bin/x').read_bytes(),b'abc')
    def test_plan_offline_tamper(self):
        v,h=self.make_plan();self.assertEqual(p.plan(self.root,'review','config/plan.json',h),v)
        with self.assertRaises(ValueError):p.plan(self.root,'review','config/plan.json','0'*64)
        f=p.acquire(self.root,v['wheels'][0]);f.write_bytes(b'wrong')
        with self.assertRaises(ValueError):p.acquire(self.root,v['wheels'][0])
        with self.assertRaises(ValueError):p.check_url('https://evil.example/file')
        with self.assertRaises(ValueError):p.check_url('https://user@github.com/file')
    def test_install_rollback_and_move(self):
        v,h=self.make_plan();payload=self.root/'workspace/user-state';payload.write_text('preserved')
        def fake(root,args,**kw):
            if 'venv' in args:
                x=Path(args[-1])/'Scripts/python.exe';x.parent.mkdir(parents=True);x.write_bytes(b'fake interpreter')
        with patch.object(p,'invoke',side_effect=fake):p.install_plan(self.root,'review',v,'config/plan.json',h,False)
        self.assertEqual(p.active(self.root)['profile'],'review');before=p.exe(self.root,'review').read_bytes()
        with patch.object(p,'invoke',side_effect=RuntimeError('simulated failure')):
            with self.assertRaises(RuntimeError):p.install_plan(self.root,'review',v,'config/plan.json',h,False)
        self.assertEqual(p.exe(self.root,'review').read_bytes(),before);self.assertEqual(payload.read_text(),'preserved')
        moved=self.root/'temp'/'moved';moved.mkdir();shutil.copytree(self.root/'config',moved/'config');shutil.copytree(self.root/'.venv',moved/'.venv')
        with self.assertRaises(ValueError):p.active(moved)
    def test_exclusive_and_native_block(self):
        with p.exclusive(self.root):
            with self.assertRaises(ValueError):
                with p.exclusive(self.root):pass
        if os.name!='nt':
            with self.assertRaises(ValueError):p.setup(self.root,'review','config/plan.json','0'*64,False)
    def test_logs_redact_rotate_export(self):
        with patch.object(logs,'CAP',300):
            for _ in range(12):logs.event(self.root,'worker','INFO','WORKER_START',state='RUNNING')
        self.assertLessEqual(len(list((self.root/'logs').glob('worker-*.jsonl'))),4)
        with self.assertRaises(ValueError):logs.event(self.root,'github','INFO','SECRET_TOKEN')
        try:raise ValueError('SECRET_TOKEN '+str(self.root))
        except ValueError as e:logs.crash(self.root,'application',e)
        rows=logs.records(self.root,level='ERROR');self.assertTrue(rows); self.assertNotIn('SECRET_TOKEN',json.dumps(rows));self.assertNotIn(str(self.root),json.dumps(rows))
        with zipfile.ZipFile(logs.export(self.root)) as z:self.assertNotIn(b'SECRET_TOKEN',z.read('technical.jsonl'))
    def test_credential_store_boundary(self):
        with self.assertRaises(ValueError):secrets.path(self.root,'../../token')
        if os.name!='nt':
            with self.assertRaises(ValueError):secrets.store(self.root,'VRS_GITHUB_TOKEN_TEST','abcdef')
        with patch.object(secrets,'dpapi',side_effect=lambda b,decrypt=False: b[::-1]):
            secrets.store(self.root,'VRS_GITHUB_TOKEN_TEST','abcdef'); self.assertEqual(secrets.read(self.root,'VRS_GITHUB_TOKEN_TEST'),'abcdef');self.assertEqual(secrets.path(self.root,'VRS_GITHUB_TOKEN_TEST').read_bytes(),b'fedcba')
    def test_source_zip_deterministic(self):
        src=self.root/'a.py';src.write_bytes(b'print(1)\n'); b=src.read_bytes();sha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest();p.save(self.root/'portable_sources.json',dict(schema=1,files={'a.py':sha})); first=build(self.root); h=p.digest(first);first.unlink();self.assertEqual(p.digest(build(self.root)),h);src.write_bytes(b'bad');
        with self.assertRaises(ValueError):build(self.root)
    def test_logs_config(self):
        p.save(self.root/'config/logging.json',{'schema':1,'level':'WARNING','days':2});logs.event(self.root,'setup','INFO','COMMAND_START',action='setup');logs.event(self.root,'setup','ERROR','CRASH');self.assertEqual(len(logs.records(self.root)),1)

if __name__=='__main__':unittest.main()

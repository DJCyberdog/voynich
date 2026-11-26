"""Synthetic tests only: never provision or disclose actual research bytes in CI."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import fitz
import vrs_contract as c
import vrs_rc1_intake as i
from vrs_core import sha
from vrs_desktop_api import Desktop,atomic_json

class IntakeTests(unittest.TestCase):
    def setUp(self):
        d=tempfile.TemporaryDirectory();self.addCleanup(d.cleanup);self.home=Path(d.name);self.intake=self.home/'intake';self.intake.mkdir()
        self.source=self.home/'source';self.source.mkdir();p=self.source/'fixture.py';p.write_bytes(b'# fixture\n');b=p.read_bytes();atomic_json(self.source/'portable_sources.json',{'schema':1,'files':{'fixture.py':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}})
        self.out=self.home/'out';self.rows=[]
        for role,scheme,name in [('manuscript',None,'original.pdf'),('reference_pdf','Eva-','eva.pdf'),('reference_pdf','STA1','sta.pdf')]:
            p=self.path(name)
            with fitz.open() as doc:page=doc.new_page();page.insert_text((50,50),name);doc.save(p)
            self.add(role,scheme,name)
        for scheme,name,label in [('Eva-','eva.txt','a'),('STA1','sta.txt','A1')]:
            self.path(name).write_text(f'#=IVTFF {scheme} 2.0 M 1\n<f1r.1,@P0> {label}\n',encoding='utf-8');self.add('transcription',scheme,name)
        self.plan=dict(schema=1,scope='SYNTHETIC_TEST',application_sha256=sha(self.source/'portable_sources.json'),sources=self.rows,run_manifest=None,catalog=None)

    def path(self,name):
        p=self.intake/'data/rc1'/name;p.parent.mkdir(parents=True,exist_ok=True);return p
    def add(self,role,scheme,name):
        p=self.path(name);self.rows.append(dict(id=name.lower(),path=p.relative_to(self.intake).as_posix(),role=role,sha256=sha(p),bytes=p.stat().st_size,origin='synthetic fixture',edition='fixture 1',scheme=scheme,rights='LOCAL_USE_ATTESTED',rights_basis='generated test data'))
    def provision(self):return i.provision(self.source,self.intake,self.out,self.plan,c.digest(self.plan),'SYNTHETIC_TEST')
    def test_explicit_partial_admission_and_source_registry(self):
        report,_=i.inspect(self.intake,self.plan);self.assertEqual(report['status'],'INVENTORY_INCOMPLETE');self.assertEqual(report['missing'],['visual_catalog','run_manifest'])
        self.assertEqual(self.provision()['status'],'PROVISIONED_INCOMPLETE');self.assertEqual(len(Desktop(self.out).sources()),5)
        self.assertEqual(i.verify(self.out,c.digest(self.plan),'SYNTHETIC_TEST')['status'],'VERIFIED')
        self.assertEqual(Desktop(self.out).runs(),[])
        with self.assertRaises(ValueError):self.provision()
        with self.assertRaises(ValueError):i.verify(self.out,c.digest(self.plan),'REAL_RESEARCH')
    def test_wrong_approval_scope_and_tamper(self):
        with self.assertRaises(ValueError):i.provision(self.source,self.intake,self.out,self.plan,'0'*64,'SYNTHETIC_TEST')
        with self.assertRaises(ValueError):i.provision(self.source,self.intake,self.out,self.plan,c.digest(self.plan),'REAL_RESEARCH')
        self.path('eva.txt').write_text('changed');self.assertEqual(i.inspect(self.intake,self.plan)[0]['status'],'BLOCKED')
        with self.assertRaises(ValueError):self.provision()
        self.assertFalse(self.out.exists())
    def test_denied_rights_scheme_and_collision(self):
        self.rows[0]['rights']='UNKNOWN';self.assertEqual(i.inspect(self.intake,self.plan)[0]['blocked'][0]['reason'],'LOCAL_USE_NOT_ATTESTED')
        self.rows[0]['rights']='LOCAL_USE_ATTESTED';self.rows[-1]['scheme']='Eva-';self.assertEqual(i.inspect(self.intake,self.plan)[0]['status'],'BLOCKED')
        self.rows[-1]['scheme']='STA1';self.rows[-1]['path']=self.rows[0]['path'].upper()
        with self.assertRaises(ValueError):i.inspect(self.intake,self.plan)
    def test_no_unadmitted_dependency_or_blind_key(self):
        self.rows[-1]['path']='data/rc1/owner_key.json'
        with self.assertRaises(ValueError):i.inspect(self.intake,self.plan)
        self.rows.pop();atomic_json(self.path('policy.json'),{'schema':1,'approval':{'path':'config/approved.json','sha256':'a'*64},'mapping':None});self.add('recognition_policy',None,'policy.json')
        self.assertEqual(i.inspect(self.intake,self.plan)[0]['status'],'BLOCKED')
    def test_restore_integrity_and_partial_failure(self):
        from vrs_rc_snapshot import snapshot,restore
        with patch.object(i,'copy_input',side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):self.provision()
        self.assertFalse(self.out.exists());self.provision()
        b=self.home/'backup';restored=self.home/'restored';h=snapshot(self.out,b)['manifest_sha256'];restore(b,restored,h)
        self.assertEqual(i.verify(restored/'app',c.digest(self.plan),'SYNTHETIC_TEST')['status'],'VERIFIED')
        (self.out/self.rows[0]['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):i.verify(self.out,c.digest(self.plan),'SYNTHETIC_TEST')

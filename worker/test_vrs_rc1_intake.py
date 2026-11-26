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

    def test_full_runtime_review_and_snapshot_replay(self):
        import json,shutil
        from PIL import Image
        from test_vrs_runtime import RuntimeTests
        from vrs_runtime import Runtime
        from vrs_rc_snapshot import snapshot,restore
        from vrs_rc_preflight import inspect as ledger
        f=RuntimeTests();f.setUp();self.addCleanup(f.doCleanups)
        # Replace the simple source-only fixture with a dependency-complete intake.
        shutil.rmtree(self.intake/'data/rc1');self.rows.clear()
        def raw(role,scheme,name,src):
            p=self.path(name);shutil.copyfile(src,p);self.add(role,scheme,name)
            return dict(path=self.rows[-1]['path'],sha256=self.rows[-1]['sha256'])
        def obj(role,scheme,name,value):
            atomic_json(self.path(name),value);self.add(role,scheme,name)
            return dict(path=self.rows[-1]['path'],sha256=self.rows[-1]['sha256'])
        original=raw('manuscript',None,'original.pdf',f.root/'source.pdf')
        groups=raw('groups',None,'groups.json',f.root/'groups.json')
        trans=[raw('transcription',scheme,name,f.root/name) for scheme,name in [('Eva-','eva.txt'),('STA1','sta.txt')]]
        inventories=[];models=[];catalog=[]
        for name,label in [('Eva-','a'),('STA1','A1')]:
            inv=raw('inventory',name,name+'-alphabet.json',f.root/(name+'-alphabet.json'));inventories.append(dict(alphabet=inv))
            model=raw('model',name,name+'-model.json',f.root/(name+'-model.json'))
            report=raw('model_report',name,name+'-report.json',f.root/(name+'-report.json'))
            models.append(dict(convention=name,model=model,report=report))
            p=self.path(name+'-ref.pdf')
            with fitz.open() as d:page=d.new_page();page.insert_text((50,50),name);d.save(p)
            self.add('reference_pdf',name,p.name)
            p=self.path(name+'-sample.png');Image.new('RGB',(20,30),'white' if name=='Eva-' else 'black').save(p);self.add('reference_sample',name,p.name)
            catalog.append(dict(id=name,name=name,version='fixture',source='synthetic',coverage='subset',entries=[dict(label=label,samples=[dict(file=p.name,sha256=sha(p),source='fixture')])]))
        refs=obj('references',None,'references.json',dict(schema=1,inventories=inventories))
        bundle=obj('model_bundle',None,'models.json',dict(schema=1,models=models))
        mapping=raw('mapping',None,'map.json',f.root/'map.json')
        policy=obj('recognition_policy',None,'policy.json',dict(schema=1,approval=None,mapping=mapping))
        run_manifest=dict(f.m,inputs=dict(manuscript=original,groups=groups,references=refs,model=bundle,recognition_policy=policy),transcriptions=trans)
        obj('run_manifest',None,'run.json',run_manifest);self.plan['run_manifest']='run.json'
        obj('visual_catalog',None,'catalog.json',dict(schema=1,preview=True,schemes=catalog));self.plan['catalog']='catalog.json'
        self.assertEqual(i.inspect(self.intake,self.plan)[0]['status'],'INVENTORY_PASS')
        self.assertEqual(self.provision()['status'],'PROVISIONED')
        self.assertEqual(set(Desktop(self.out).catalog(Desktop(self.out).settings()['catalog'])),set(i.SCHEMES))
        app=Runtime(self.out);run=app.register(run_manifest)
        for stage in c.STAGES[:4]:self.assertEqual(app.sweep()[0]['stage'],stage)
        self.assertEqual(app.ledger.status(run)['receipts']['glyph_classification']['counts']['accepted'],0)
        item=app.review_items(run)['items'][0];f.app=app;app.submit(f.decision(run,item,'deferred'))
        item=app.review_items(run)['items'][0];app.submit(f.decision(run,item,'glyph'))
        before=ledger(self.out);self.assertEqual(before['counts']['decision_revisions'],2)
        approved=c.digest(self.plan);i.verify(self.out,approved,'SYNTHETIC_TEST')
        b=self.home/'reviewed-backup';out=self.home/'reviewed-restore';h=snapshot(self.out,b)['manifest_sha256'];restore(b,out,h)
        self.assertEqual(ledger(out/'app'),before);i.verify(out/'app',approved,'SYNTHETIC_TEST')
        restored=Runtime(out/'app');self.assertEqual(restored.review_items(run),app.review_items(run))
        self.assertEqual(restored.ledger.outbox(),[])

    def test_archive_not_runtime_and_unknown_rights_readonly(self):
        p=self.path('IT2a-n.txt');p.write_text('#=IVTFF EvaT 2.0 M 3\n<f1r.1,@P0> a\n',encoding='utf-8');self.add('transcription_archive','EvaT',p.name)
        self.rows[0]['rights']='UNKNOWN'
        report,details=i.inspect(self.intake,self.plan)
        self.assertEqual(report['status'],'BLOCKED');self.assertEqual(report['verified_sources'],6)
        self.assertFalse(details['it2a-n.txt']['runtime_eligible'])
        self.rows[0]['rights']='LOCAL_USE_ATTESTED'
        self.rows.pop(3)
        report,_=i.inspect(self.intake,self.plan)
        self.assertIn('transcription:Eva-',report['missing'])
        self.assertEqual(self.provision()['status'],'PROVISIONED_INCOMPLETE')
        self.assertEqual(len(Desktop(self.out).sources()),4)
        self.assertEqual((self.out/'data/rc1/IT2a-n.txt').read_bytes(),p.read_bytes())
    def test_starter_never_authorizes_rights_or_fabricates_eva(self):
        seed=i.starter(self.source,self.intake)
        self.assertEqual(seed['scope'],'REAL_RESEARCH');self.assertEqual(len(seed['sources']),4)
        self.assertTrue(all(row['rights']=='UNKNOWN' for row in seed['sources']))
        self.assertEqual(seed['application_sha256'],sha(self.source/'portable_sources.json'))
        report,_=i.inspect(self.intake,seed)
        self.assertEqual(report['status'],'BLOCKED');self.assertIn('transcription:Eva-',report['missing'])

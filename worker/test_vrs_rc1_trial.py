"""Technical trial guards using synthetic files, no original corpus in CI."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import fitz
import vrs_contract as c
import vrs_rc1_intake as intake
import vrs_rc1_trial as trial
from vrs_rc1_catalog import merge_catalogs
from vrs_portable import digest
from vrs_desktop_api import atomic_json
from vrs_source_update import blob


class TrialTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.source=self.root/'source';self.source.mkdir();(self.source/'dummy.py').write_bytes(b'# test\n')
        atomic_json(self.source/'portable_sources.json',dict(schema=1,files={'dummy.py':blob(b'# test\n')}))
        self.originals=self.root/'originals';self.originals.mkdir();self.out=self.root/'intake'
        self.pdf=self.originals/'voynich(1).pdf'
        with fitz.open() as d:d.new_page();d.save(self.pdf)
        self.eva=self.originals/'ZL3b-n.txt';self.eva.write_bytes(b'#=IVTFF Eva- 2.0 M 5\n<f1r.1,@P0> a\n')
        self.known=(('pdf','voynich.pdf','manuscript',None,digest(self.pdf),self.pdf.stat().st_size,'fixture','fixture'),)
        self.optional=(('eva','ZL3b-n(1).txt','transcription','Eva-',digest(self.eva),self.eva.stat().st_size,'fixture','fixture'),)
        self.addCleanup(patch.stopall);patch.object(intake,'KNOWN_SOURCES',self.known).start();patch.object(intake,'OPTIONAL_SOURCES',self.optional).start()

    def test_stage_exact_aliases_and_explicit_local_use(self):
        result=trial.stage(self.source,self.originals,self.out);plan=c.load(self.out/'sources-plan.json')
        self.assertEqual(result['sources'],2);self.assertTrue(all(r['rights']=='UNKNOWN' for r in plan['sources']))
        self.assertEqual((self.out/'data/rc1/ZL3b-n(1).txt').read_bytes(),self.eva.read_bytes())
        with self.assertRaises(ValueError):trial.attest(self.out,plan,'0'*64,'fixture')
        approved=trial.attest(self.out,plan,c.digest(plan),'synthetic test only')
        self.assertFalse(approved['execution_authorized']);self.assertNotEqual(approved['plan_sha256'],result['plan_sha256'])
        self.assertTrue(all(r['rights']=='LOCAL_USE_ATTESTED' for r in c.load(self.out/approved['path'])['sources']))
        self.assertFalse((self.out/'workspace').exists())

    def test_stage_refuses_lfs_pointer_and_tamper(self):
        self.pdf.write_bytes(b'version https://git-lfs.github.com/spec/v1\n')
        with self.assertRaises(ValueError):trial.stage(self.source,self.originals,self.out)
        self.assertFalse(self.out.exists())

    def test_caption_and_compact_json(self):
        p=self.root/'caption.pdf'
        with fitz.open() as d:
            for _ in range(214):d.new_page()
            d[3].insert_text((40,40),'1r\nPage 4 of 214');d.save(p)
        self.assertEqual(trial.first_folio(p),{'4':'f1'})
        with self.assertRaises(ValueError):trial.first_folio(self.pdf)
        j=self.root/'compact.json';trial.compact(j,{'x':[0,1,.2]});self.assertEqual(c.load(j),{'x':[0,1,.2]})
        with self.assertRaises(FileExistsError):trial.compact(j,{'x':0})

    def test_explicit_runtime_preview_alias_only(self):
        from PIL import Image
        p=self.root/'catalog';p.mkdir();im=p/'sample.png';Image.new('L',(8,8),0).save(im)
        plan=self.root/'plan.json';atomic_json(plan,{'fixture':True})
        raw=dict(schema=1,preview=True,plan_sha256=digest(plan),schemes=[dict(id='Eva-',name='Eva-',version='fixture',source='fixture',entries=[dict(label='a',samples=[dict(file='sample.png',sha256=digest(im),source='fixture')])])])
        atomic_json(p/'references.json',raw)
        with self.assertRaises(ValueError):merge_catalogs([(p,plan)],self.root/'refused')
        path,images=merge_catalogs([(p,plan)],self.root/'allowed',runtime_subset=True)
        self.assertEqual(len(images),1);self.assertTrue(c.load(path)['preview'])

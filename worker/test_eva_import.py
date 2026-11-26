import os
import tempfile
import unittest
from pathlib import Path
from PIL import Image
import eva_import as e
import reference_import as ri
import active_review as ar
import worker as w


class EvaImportTests(unittest.TestCase):
    def test_unknown_pdf_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'wrong.pdf'; p.write_bytes(b'not the pinned source')
            with self.assertRaisesRegex(ValueError,'edition/hash'): e.discover(p,Path(tmp)/'plan.json')

    def test_combine_separate_aux_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); pic=p/'ref.png'; Image.new('L',(16,16),100).save(pic)
            def scheme(key):
                return dict(id=key,name=key,version='toy',source='synthetic',entries=[dict(label='X',samples=[dict(file=pic.name,sha256=w.sha(pic),source='test')])])
            a=p/'a.json'; b=p/'b.json'
            w.write(a,dict(schema=1,schemes=[scheme('eva-original'),scheme('eva-aux')]))
            w.write(b,dict(schema=1,schemes=[scheme('sta1')]))
            out=p/'out'; e.combine([a,b],out)
            self.assertEqual(set(ar.catalog(out/'references.json')),{'eva-original','sta1'})
            self.assertEqual(set(ar.catalog(out/'auxiliary.json')),{'eva-aux'})
            with self.assertRaisesRegex(ValueError,'Duplicate scheme'): e.combine([a,a],p/'dup')
            pic.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'provenance'): e.combine([a,b],p/'bad')

    @unittest.skipUnless(os.getenv('EVA_REFERENCE_PDF'),'Owner source not supplied')
    def test_actual_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); pdf=os.environ['EVA_REFERENCE_PDF']; plan=p/'plan.json'
            data=e.discover(pdf,plan)
            self.assertEqual(len(data['entries']),329)
            self.assertEqual(data['recognized_pages'],[1,2,3,4,6,7])
            self.assertEqual(sum(x['visual_column'].startswith('Extended EVA') for x in data['entries']),85)
            self.assertEqual(sum(x['visual_column']=='Basic EVA' for x in data['entries']),26)
            result=ri.build(pdf,plan,p/'catalog',preview=True)
            self.assertEqual(result['schemes'],{'eva-original':147,'eva-aux':14,'frogguy':43,'bennett':24,'fsg':36,'currier':36})
            ar.catalog(p/'catalog/references.json')

if __name__=='__main__': unittest.main()

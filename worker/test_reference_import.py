import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
import fitz
import active_review as a
import reference_import as r
import review_groups as g
import worker as w


class ReferenceImportTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); self.root=Path(t.name)
        self.pdf=self.root/'ref.pdf'; doc=fitz.open(); page=doc.new_page(width=200,height=100)
        page.draw_circle((50,45),10,color=(0,0,0)); doc.save(self.pdf); doc.close()
        self.plan=self.root/'plan.json'
        self.data=dict(schema=1,source='synthetic test',version='test',rights='synthetic fixture',source_sha256=w.sha(self.pdf),reviewed=False,entries=[dict(scheme='sta1',label='X1',page=1,box=[30,25,70,65],sta_code='X1',visual_column='EVA')])
        w.write(self.plan,self.data)
    def test_preview_and_approval_gate(self):
        with self.assertRaisesRegex(ValueError,'review'): r.build(self.pdf,self.plan,self.root/'no')
        result=r.build(self.pdf,self.plan,self.root/'preview',preview=True)
        self.assertEqual(result['images'],1)
        c=a.catalog(self.root/'preview/references.json'); self.assertIn('unreviewed',c['sta1']['coverage'])
        self.data.update(reviewed=True,reviewer='fixture',private_use_confirmed=True); w.write(self.plan,self.data)
        r.build(self.pdf,self.plan,self.root/'approved'); self.assertIn('reviewed subset',a.catalog(self.root/'approved/references.json')['sta1']['coverage'])
    def test_bad_hash_and_box(self):
        self.data['source_sha256']='0'*64; w.write(self.plan,self.data)
        with self.assertRaisesRegex(ValueError,'hash'): r.build(self.pdf,self.plan,self.root/'bad',preview=True)
        self.data['source_sha256']=w.sha(self.pdf); self.data['entries'][0]['box']=[-1,0,70,65]; w.write(self.plan,self.data)
        with self.assertRaisesRegex(ValueError,'clip'): r.build(self.pdf,self.plan,self.root/'bad2',preview=True)
    def test_groups_do_not_propagate(self):
        img=Image.new('L',(48,16),255); d=ImageDraw.Draw(img); d.rectangle((3,3,7,13),fill=0); d.rectangle((19,3,23,13),fill=0); d.rectangle((32,1,47,15),fill=0); img.save(self.root/'crop.png')
        rows=[dict(id=str(i),record={'file':'crop.png'},box=[x,0,x+16,16]) for i,x in enumerate((0,16,32))]
        out=g.ordered(self.root/'manifest.json',rows)
        self.assertEqual(len(out),3); self.assertEqual(out[0]['visual_group'],out[1]['visual_group']); self.assertNotEqual(out[0]['visual_group'],out[2]['visual_group']); self.assertTrue(all('label' not in row for row in out))

if __name__=='__main__': unittest.main()

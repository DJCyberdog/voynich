import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
import glyphs as g
import worker as w


class GlyphTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup); self.root=Path(temp.name)
        self.manifest=self.root/'manifest.json'; records=[]; annotations={}
        for i in range(4):
            image=Image.new('L',(100,44),255); d=ImageDraw.Draw(image)
            d.rectangle((8,6,12+i,34),fill=0); d.rectangle((49,14,83,18+i),fill=0)
            path=self.root/f'r{i}.png'; image.save(path)
            records.append(dict(id=f'r{i}',page=i+1,group=f'leaf{i}',file=path.name,sha256=w.sha(path)))
            annotations[f'r{i}']=dict(status='single_line',glyphs=[dict(box=b,label=l) for b,l in zip(g.boxes(image),['X','Y'])])
        w.write(self.manifest,dict(regions=records)); self.a=self.root/'a.json'; self.b=self.root/'b.json'
        for p,who in [(self.a,'alpha'),(self.b,'beta')]: w.write(p,dict(schema=1,manifest_sha256=w.sha(self.manifest),reviewer=who,regions=annotations))
        self.alphabet=self.root/'alphabet.json'; w.write(self.alphabet,dict(convention='synthetic-only',labels=['X','Y']))
        self.split=self.root/'split.json'; w.write(self.split,dict(train=['leaf0','leaf1'],test=['leaf2','leaf3']))

    def test_projection_and_review_template(self):
        im=Image.new('L',(32,20),255); self.assertEqual(g.boxes(im),[])
        d=ImageDraw.Draw(im); d.rectangle((0,2,3,9),fill=0); d.rectangle((28,4,31,15),fill=0)
        self.assertEqual(g.boxes(im),[[0,2,4,10],[28,4,32,16]])
        path=self.root/'template.json'; g.propose(self.manifest,path,'reviewer')
        self.assertTrue(all(r['status']=='unreviewed' and all(x['label']=='unknown' for x in r['glyphs']) for r in w.read(path)['regions'].values()))

    def test_review_and_split_guards(self):
        b=w.read(self.b); b['reviewer']='alpha'; w.write(self.b,b)
        with self.assertRaisesRegex(ValueError,'Distinct'): g.cohorts(self.manifest,self.a,self.b,self.alphabet,self.split)
        b['reviewer']='beta'; b['regions']['r0']['glyphs'][0]['box'][0]=-1; w.write(self.b,b)
        with self.assertRaisesRegex(ValueError,'Invalid glyph box'): g.cohorts(self.manifest,self.a,self.b,self.alphabet,self.split)
        b=w.read(self.a); b['reviewer']='beta'; w.write(self.b,b)
        w.write(self.split,dict(train=['leaf0','leaf1'],test=['leaf1','leaf2','leaf3']))
        with self.assertRaisesRegex(ValueError,'leakage'): g.cohorts(self.manifest,self.a,self.b,self.alphabet,self.split)

    def test_disagreement_and_unknown_accounting(self):
        b=w.read(self.b); b['regions']['r0']['glyphs'][0]['label']='Y'; w.write(self.b,b)
        _,sets,excluded,unknown=g.cohorts(self.manifest,self.a,self.b,self.alphabet,self.split)
        self.assertEqual(excluded['train'],1); self.assertEqual(len(sets['train']),2)
        for p in (self.a,self.b):
            a=w.read(p); a['regions']['r0']['glyphs'][0]['label']='unknown'; w.write(p,a)
        _,sets,excluded,unknown=g.cohorts(self.manifest,self.a,self.b,self.alphabet,self.split)
        self.assertEqual(unknown['train'],1); self.assertEqual(len(sets['train']),3)

    def test_duplicate_normalized_glyph(self):
        a=w.read(self.manifest); a['regions'][2]['file']=a['regions'][0]['file']; a['regions'][2]['sha256']=a['regions'][0]['sha256']; w.write(self.manifest,a)
        for p in (self.a,self.b):
            r=w.read(p); r['manifest_sha256']=w.sha(self.manifest); r['regions']['r2']=r['regions']['r0']; w.write(p,r)
        with self.assertRaisesRegex(ValueError,'duplicate across split'): g.cohorts(self.manifest,self.a,self.b,self.alphabet,self.split)

    def test_cpu_train_predict_and_reject(self):
        out=self.root/'model'; r=g.train(self.manifest,self.a,self.b,self.alphabet,self.split,out,'cpu')
        self.assertEqual(r['test_n'],4); self.assertEqual(r['accuracy_including_unknown'],1)
        self.assertEqual(g.decision('X',.13,.1),'unknown'); self.assertEqual(g.decision('X',.01,.001),'unknown')
        res=g.predict(self.manifest,self.a,self.alphabet,out/'glyph_model.json',out/'glyph_report.json',self.root/'pred.json','cpu')
        self.assertEqual(len(res['rows']),8); self.assertEqual(res['scientific_status'],'UNADJUDICATED')
        self.assertTrue(all('truth' not in row for row in res['rows']))
        with (out/'glyph_model.json').open('a') as f: f.write(' ')
        with self.assertRaisesRegex(ValueError,'provenance'): g.predict(self.manifest,self.a,self.alphabet,out/'glyph_model.json',out/'glyph_report.json',self.root/'bad.json','cpu')

if __name__=='__main__': unittest.main()

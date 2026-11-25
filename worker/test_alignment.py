import os
import tempfile
import unittest
from pathlib import Path
from PIL import Image
import alignment as a
import worker as w
import active_review as ar


class AlignmentTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); self.root=Path(t.name)
        self.src=self.root/'eva.txt'; self.src.write_text('#=IVTFF Eva- 2.0 M 5\n<f1r> <! metadata>\n<f1r.1,@P0> <%>ch.o<$>\n<f1r.2,+P0> [a:o]\n<f1r.3,+P0> a,b\n<fRos.1,@L0> @130;{ee}\n')
        self.hash=w.sha(self.src)

    def test_parse_boundaries(self):
        scheme,rows,s=a.load_source(self.src,self.hash); self.assertEqual(scheme,'Eva-'); self.assertEqual((s['loci'],s['strict'],s['unresolved']),(4,2,2))
        self.assertEqual(rows['fRos.1']['units'],['@130;','{ee}']); self.assertEqual(rows['f1r.1']['units'],list('cho'))
        with self.assertRaisesRegex(ValueError,'SHA256'): a.load_source(self.src,'0'*64)
        p=self.root/'sta.txt'; p.write_text('#=IVTFF STA1 2.0 M 6\n<f1r.1,@P0> A1K1.A2\n<f1r.2,+P0> [A1:A2]\n')
        self.assertEqual(a.load_source(p,w.sha(p))[1]['f1r.1']['units'],['A1','K1','A2'])
        with p.open('a') as f: f.write('<f1r.1,@P0> A1\n')
        with self.assertRaisesRegex(ValueError,'Duplicate locus'): a.load_source(p,w.sha(p))

    def test_alignment_uncertainty_and_segmentation(self):
        r=a.align([[('c','h')],[('o',)]],list('cho')); self.assertTrue(r['exact_notation_agreement']); self.assertEqual(r['steps'][0]['reference'],[0,2])
        r=a.align([[('a',),('o',)]],['o']); self.assertFalse(r['exact_notation_agreement']); self.assertEqual(r['steps'][0]['operation'],'alternative_match')
        r=a.align([[]],['o']); self.assertEqual(r['cost'],1); self.assertEqual(r['steps'][0]['operation'],'unknown')
        r=a.align([[('o',)]],['o','o']); self.assertTrue(r['ambiguous_optimum']); self.assertIsNone(r['steps'])
        self.assertEqual(a.align([[('a',)],[('o',)]],['a'])['cost'],1)
        self.assertEqual(a.align([[('a',)]],['b'])['steps'][0]['operation'],'substitution')

    def test_compare_requires_mapping(self):
        p=self.root/'obs.json'; out=self.root/'report.json'
        def r(rid,locus,status='confirmed',scope='complete_locus',subtype='@P0'):
            return dict(region_id=rid,locus=locus,mapping_status=status,scope=scope,mapper='declared',subtype=subtype,candidates=[['ch'],['o']])
        rows=[r('a','f1r.1'),r('b','f1r.1','tentative'),r('c','f1r.1',scope='partial'),r('d','f1r.2',subtype='+P0'),r('e','f1r.1',subtype='+P0'),r('f','f1r.99')]
        w.write(p,dict(schema=1,scheme='Eva-',source_sha256=self.hash,manifest_sha256='0'*64,prediction_sha256='1'*64,regions=rows))
        x=a.compare(self.src,self.hash,p,out); self.assertEqual(x['COMPARED'],1); self.assertEqual(x['UNRESOLVED'],5); self.assertEqual(x['exact_notation_agreement'],1)
        self.assertEqual(w.read(out)['scientific_status'],'UNADJUDICATED')
        with self.assertRaisesRegex(ValueError,'already exists'): a.compare(self.src,self.hash,p,out)

    def test_adapter_and_review(self):
        root=self.root; image=root/'crop.png'; Image.new('L',(60,20),180).save(image)
        manifest=root/'manifest.json'; w.write(manifest,dict(regions=[dict(id='r',page=1,group='leaf1',file=image.name,sha256=w.sha(image))]))
        alphabet=root/'alpha.json'; w.write(alphabet,dict(convention='Eva-',labels=['ch','o']))
        model=root/'model.json'; w.write(model,dict(inventory_sha256=w.sha(alphabet),labels=['ch','o']))
        pred=root/'pred.json'; w.write(pred,dict(manifest_sha256=w.sha(manifest),model_sha256=w.sha(model),rows=[dict(region_id='r',box=[20,0,30,10],predicted='unknown'),dict(region_id='r',box=[0,0,10,10],predicted='ch'),dict(region_id='r',box=[10,0,20,10],predicted='unknown')]))
        mapping=root/'map.json'; w.write(mapping,dict(manifest_sha256=w.sha(manifest),source_sha256=self.hash,scheme='Eva-',alphabet_sha256=w.sha(alphabet),prediction_sha256=w.sha(pred),regions={'r':dict(page=1,group='leaf1',locus='f1r.1',subtype='@P0',scope='complete_locus',mapping_status='confirmed',mapper='fixture')}))
        out=root/'obs.json'; a.prepare(manifest,pred,alphabet,model,mapping,self.src,self.hash,out); self.assertEqual(w.read(out)['regions'][0]['candidates'],[['ch'],[],[]])
        refs=root/'refs.json'; w.write(refs,dict(schema=1,schemes=[dict(id='eva-from-sta',name='toy',version='toy',source='fixture',entries=[dict(label='o',samples=[dict(file=image.name,sha256=w.sha(image),source='fixture')])])]))
        review=root/'review.json'; schemes,rows,data=ar.open_session(manifest,pred,refs,review,'owner')
        for row in rows:
            if row['box'][0]==10: d=dict(kind='false_positive',mapping=ar.empty_mapping(schemes),note='')
            else: d=dict(kind='glyph',mapping={'eva-from-sta':dict(state='mapped',label='o')},note='')
            data['decisions'][row['id']]=d
        w.write(review,data); obs=root/'reviewed.json'; a.prepare(manifest,pred,alphabet,model,mapping,self.src,self.hash,obs,review,refs,'eva-from-sta')
        row=w.read(obs)['regions'][0]; self.assertEqual(row['candidates'],[['ch'],['o']]); self.assertEqual(row['excluded_false_positives'],1)
        self.assertEqual(a.compare(self.src,self.hash,obs,root/'comparison.json')['exact_notation_agreement'],1)
        with self.assertRaisesRegex(ValueError,'No implicit'): a.prepare(manifest,pred,alphabet,model,mapping,self.src,self.hash,root/'bad.json',review,refs,'sta1')
        model.write_text('{}')
        with self.assertRaisesRegex(ValueError,'binding mismatch'): a.prepare(manifest,pred,alphabet,model,mapping,self.src,self.hash,root/'bad.json')

    @unittest.skipUnless(os.getenv('VOYNICH_TRANSCRIPT_DIR'),'Pinned owner sources unavailable')
    def test_actual_sources(self):
        p=Path(os.environ['VOYNICH_TRANSCRIPT_DIR'])
        cases=[('ZL3b-n.txt','bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc',5385,2161),('ZL3b.txt','8438ba1c45f47fe1d06b5262cbcdf60ce69158a0edbd4dd802612896f3217e2a',5385,2772),('GC2a_1.txt','0c0d1eea4b5ab87f8a65fb7f4346864cd90758ad993812b4f2122b3899d4ac88',5367,3733)]
        for name,sha,n,strict in cases:
            _,rows,s=a.load_source(p/name,sha); self.assertEqual((s['loci'],s['strict']),(n,strict)); self.assertIn('fRos.1' if name!='GC2a_1.txt' else 'fRos.2',rows)
        audit=a.audit_common([(p/name,sha) for name,sha,_,_ in cases]); self.assertEqual((audit['common_loci'],audit['common_subtype'],audit['strict_common']),(5366,5366,1691))

if __name__=='__main__': unittest.main()

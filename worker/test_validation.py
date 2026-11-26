import csv
import os
import tempfile
import unittest
from pathlib import Path
from PIL import Image
import fitz
import glyphs as g
import validation as v
import worker as w


class ValidationTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); self.root=Path(t.name)
        root=self.root; pdf=root/'toy.pdf'; doc=fitz.open()
        for i in range(4):
            page=doc.new_page(width=600,height=800)
            page.draw_rect(fitz.Rect(280,149,284+i*2,170),color=None,fill=(0,0,0))
            page.draw_rect(fitz.Rect(302,155,321,158+i*2),color=None,fill=(0,0,0))
            page.draw_circle((300+i,480),6+i,fill=(0,0,0),color=None)
        doc.save(pdf); doc.close()
        review=root/'centers.csv'
        with review.open('w',newline='') as f:
            writer=csv.writer(f); writer.writerow(['review_id','page','text_x','text_y'])
            for i in range(1,5): writer.writerows([[f'T{i}',i,.5,.2],[f'N{i}',i,.5,.6]])
        groups=root/'groups.json'; w.write(groups,{str(i):f'leaf{i}' for i in range(1,5)})
        manifest=root/'data/manifest.json'; w.prepare(pdf,w.sha(pdf),review,groups,manifest.parent)
        alphabet=root/'alphabet.json'; w.write(alphabet,dict(convention='Eva-',labels=['o','l']))
        rows={}; labels={}
        for rec in w.dataset(manifest)['regions']:
            rid=rec['id']; labels[rid]='script' if rid.startswith('T') else 'non_script'
            if labels[rid]=='script':
                with Image.open(manifest.parent/rec['file']) as im: boxes=g.boxes(im)
                self.assertEqual(len(boxes),2); rows[rid]=dict(status='single_line',glyphs=[dict(box=b,label=l) for b,l in zip(boxes,['o','l'])])
            else: rows[rid]=dict(status='reject',glyphs=[])
        files=dict(pdf=pdf,review_csv=review,groups=groups,manifest=manifest,alphabet=alphabet)
        for side in ('left','right'):
            files['script_'+side]=root/f'script-{side}.json'; w.write(files['script_'+side],dict(reviewer='synthetic-'+side,manifest_sha256=w.sha(manifest),labels=labels))
            files['glyph_'+side]=root/f'glyph-{side}.json'; w.write(files['glyph_'+side],dict(schema=1,reviewer='synthetic-'+side,manifest_sha256=w.sha(manifest),inventory_sha256=w.sha(alphabet),regions=rows))
        split=root/'split.json'; w.write(split,dict(train=['leaf1','leaf2'],test=['leaf3','leaf4'])); files['split']=split
        source=root/'source.txt'; source.write_text('#=IVTFF Eva- 2.0 M 5\n<f3r.1,@P0> ol\n<f4r.1,@P0> ol\n'); files['transcription']=source
        mapping=root/'mapping.json'; maps={}
        for rec in w.dataset(manifest)['regions']:
            if rec['page']<3: continue
            rid=rec['id']; maps[rid]=dict(page=rec['page'],group=rec['group'],locus=f'f{rec["page"]}r.1' if rid.startswith('T') else None,subtype='@P0',mapping_status='confirmed' if rid.startswith('T') else 'unconfirmed',scope='complete_locus',mapper='synthetic')
        w.write(mapping,dict(manifest_sha256=w.sha(manifest),source_sha256=w.sha(source),scheme='Eva-',regions=maps)); files['mapping']=mapping
        self.files=files; self.plan=root/'plan.json'; self.freeze()

    def freeze(self):
        w.write(self.plan,dict(schema=1,scope='synthetic',inputs={k:dict(path=str(p.relative_to(self.root)),sha256=w.sha(p)) for k,p in self.files.items()},settings=dict(device='cpu',epochs=3,batch=2,seed=42)))

    def test_end_to_end(self):
        out=self.root/'run'; report=v.run(self.plan,out)
        self.assertEqual(report['technical_status'],'COMPLETED'); self.assertEqual(report['scientific_status'],'UNADJUDICATED')
        self.assertEqual(report['heldout_regions'],4); self.assertEqual(report['gated']['eligible'],2); self.assertEqual(report['ungated_diagnostic']['eligible'],2)
        self.assertEqual(report['mapping_exclusions'],{'not_agreed_script':2})
        self.assertEqual(report['ungated_diagnostic']['compared'],2)
        self.assertEqual(report['gated']['compared']+report['gated']['not_compared'],2)
        self.assertEqual(report['glyph_reference_box_test_n'],4)
        self.assertEqual(report['localization']['status'],'BLOCKED_NO_EXHAUSTIVE_PAGE_REFERENCE')
        self.assertEqual(w.read(out/'run.json')['report_sha256'],w.sha(out/'validation_report.json'))
        with self.assertRaisesRegex(ValueError,'already exists'): v.run(self.plan,out)

    def test_tampered_input_and_duplicate_locus(self):
        mapping=self.files['mapping']; data=w.read(mapping); data['regions']['T4']['locus']='f3r.1'; w.write(mapping,data)
        with self.assertRaisesRegex(ValueError,'Input hash mismatch'): v.preflight(self.plan)
        self.freeze()
        with self.assertRaisesRegex(ValueError,'Duplicate confirmed'): v.preflight(self.plan)

    def test_unconfirmed_map_and_split_rejection(self):
        mapping=self.files['mapping']; data=w.read(mapping); data['regions']['T4']['mapping_status']='tentative'; w.write(mapping,data); self.freeze()
        *_,eligible,reasons,excluded=v.preflight(self.plan); self.assertEqual(eligible,{'T3'}); self.assertEqual(reasons['mapping_unconfirmed'],1)
        split=self.files['split']; w.write(split,dict(train=['leaf1','leaf2','leaf3'],test=['leaf3','leaf4'])); self.freeze()
        with self.assertRaisesRegex(ValueError,'leakage'): v.preflight(self.plan)

    def test_localization_reference(self):
        ref=self.root/'page_ref.json'; self.files['page_reference']=ref
        w.write(ref,dict(source_sha256=w.sha(self.files['pdf']),groups_sha256=w.sha(self.files['groups']),reviewer='synthetic geometry',exhaustive=True,pages={'3':[[280/600,149/800,321/600,170/800]],'4':[[280/600,149/800,321/600,170/800]]}))
        self.freeze(); report=v.run(self.plan,self.root/'loc-run'); self.assertEqual(report['localization']['status'],'COMPARED')
        self.assertEqual(report['localization']['metrics']['0.5']['reference'],2)
        d=w.read(ref); d['pages']['1']=[]; w.write(ref,d); self.freeze()
        with self.assertRaisesRegex(ValueError,'exact held-out pages'): v.preflight(self.plan)

    @unittest.skipUnless(os.getenv('VOYNICH_MANUSCRIPT_PDF'),'Pinned manuscript PDF unavailable')
    def test_actual_probe(self):
        groups=self.root/'actual-groups.json'; w.write(groups,{'6':'f2','176':'f99'})
        report=v.probe(os.environ['VOYNICH_MANUSCRIPT_PDF'],'d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c',groups,self.root/'actual',[6,176])
        self.assertEqual(report['screened'],12782); self.assertEqual(report['proposal_counts'],{'6':2361,'176':3106})
        self.assertEqual(report['projection_run_counts'],{'6':8468,'176':8222}); self.assertEqual(report['scientific_status'],'BLOCKED_NO_INDEPENDENT_LABELS')

    def test_probe_counts_only(self):
        out=self.root/'probe'; report=v.probe(self.files['pdf'],w.sha(self.files['pdf']),self.files['groups'],out,[1])
        self.assertEqual(report['scientific_status'],'BLOCKED_NO_INDEPENDENT_LABELS'); self.assertGreater(report['proposal_counts']['1'],0)
        self.assertEqual(report['manifest_sha256'],w.sha(out/'manifest.json'))

if __name__=='__main__': unittest.main()

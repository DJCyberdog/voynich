import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
import vrs_contract as c
from vrs_core import sha
from vrs_desktop_api import Desktop, ReadLedger, safe
import test_vrs_runtime as fixtures


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.RuntimeTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.root=self.f.root; self.api=Desktop(self.root)

    def test_empty_workspace_and_settings(self):
        with tempfile.TemporaryDirectory() as d:
            a=Desktop(d); self.assertEqual(a.runs(),[]); cfg=a.settings(); self.assertEqual(cfg['language'],'de'); cfg.update(theme='light',language='en',reviewer='reviewer'); self.assertEqual(a.save_settings(cfg),cfg)
            self.assertFalse((Path(d)/'workspace').exists())

    def test_read_only_review_and_crop(self):
        run=self.f.run_to_review(); db=ReadLedger(self.root).db; before=sha(db); result=self.api.review(run,limit=1)
        self.assertEqual(result['snapshot'],self.f.app.review_items(run,limit=1)['snapshot']); self.assertEqual(result['items'],self.f.app.review_items(run,limit=1)['items']); im,box=self.api.crop(result['items'][0]); self.assertGreater(im.width,0); self.assertEqual(box,result['items'][0]['box']); self.assertEqual(sha(db),before)
        with ReadLedger(self.root)._tx() as conn:
            with self.assertRaises(Exception): conn.execute("UPDATE runs SET control='READY'")

    def test_full_page_context_exact_crop_and_identity(self):
        run=self.f.run_to_review(); item=self.api.review(run,limit=1)['items'][0]
        db=ReadLedger(self.root).db; before=sha(db)
        page,box=self.api.page_context(item); crop,local=self.api.crop(item)
        self.assertEqual(page.size,(250,250))
        self.assertEqual(page.crop(box).tobytes(),crop.crop(local).tobytes())
        self.assertEqual(sha(db),before)
        for changed in (dict(item,page=2),dict(item,region_id='fake'),dict(item,box=[0,0,1,1])):
            with self.assertRaises(ValueError):self.api.page_context(changed)
        (self.root/item['crop']['path']).write_bytes(b'bad')
        with self.assertRaises(ValueError):self.api.page_context(item)

    def test_vector_window_native_coordinates_and_bounds(self):
        from vrs_desktop_api import vector_window
        image=Image.new('RGB',(100,100),'white')
        rows=[dict(box=[40,41,44,45],contours=[[[0,0],[4,0],[4,4],[0,4],[0,0]]]),
              dict(box=[80,80,82,82],contours=[])]
        preview,box,paths,count,layers=vector_window(image,[42,42,46,46],rows)
        self.assertEqual(count,1);self.assertEqual(preview.size,(54,53))
        self.assertEqual(box,[26,25,30,29]);self.assertEqual(paths[0][0],(24,24))
        self.assertEqual(vector_window(image,[1,1,2,2],rows)[3],0)
        rows[0]['contours'][0][1]=[9,0]
        with self.assertRaises(ValueError):vector_window(image,[42,42,46,46],rows)

    def test_hybrid_review_layers_and_group_extent(self):
        from vrs_desktop_api import vector_window
        image=Image.new('RGB',(120,120),'white')
        rows=[dict(id='a',box=[40,40,44,44],contours=[],fallback=True,graph=dict(paths=[[[0,0],[3,3]]],nodes=[dict(point=[0,0],degree=1),dict(point=[3,3],degree=3)])),
              dict(id='b',box=[45,40,48,44],contours=[]),dict(id='c',box=[49,40,52,44],contours=[])]
        pairs=[dict(id='p',members=['a','b'],box=[40,40,48,44])]
        extra=dict(splits=[dict(id='s',parent='a',parts=[dict(box=[40,40,42,44]),dict(box=[42,40,44,44])])],compounds=[dict(id='g',members=['a','b','c'],box=[40,40,52,44])])
        im,box,_,count,layers=vector_window(image,[40,40,44,44],rows,pairs,extra)
        self.assertEqual((im.size,box,count),((60,52),[24,24,28,28],1))
        self.assertEqual(layers['skeleton'],[[(24.5,24.5),(27.5,27.5)]])
        self.assertEqual(layers['nodes'][1],(27.5,27.5,3));self.assertEqual(layers['fallback'],1)
        self.assertEqual(layers['hypotheses']['compounds'],[('g',[[24,24,36,28],[24,24,28,28],[29,24,32,28],[33,24,36,28]])])
        self.assertEqual(len(layers['hypotheses']['splits']),1)
        pairs[0]['box']=[40,40,47,44]
        with self.assertRaisesRegex(ValueError,'Group envelope mismatch'):vector_window(image,[40,40,44,44],rows,pairs,extra)

    def test_large_component_is_clipped_not_discarded(self):
        from vrs_desktop_api import vector_window
        image=Image.new('RGB',(1600,1600),'white')
        rows=[dict(id='large',box=[0,0,1600,1600],contours=[[[0,0],[1600,0],[1600,1600],[0,1600],[0,0]]],
                   graph=dict(paths=[[[0,800],[1599,800]],[[0,0],[1599,1599]]],
                              nodes=[dict(point=[0,0],degree=1),dict(point=[800,800],degree=3)]))]
        target=[790,790,810,810]
        preview,box,paths,count,layers=vector_window(image,target,rows)
        self.assertEqual(preview.size,(68,68));self.assertEqual(box,[24,24,44,44])
        self.assertEqual(preview.crop(box).tobytes(),image.crop(target).tobytes())
        self.assertEqual(count,1);self.assertEqual(paths,[])
        self.assertEqual(layers['skeleton'][0],[(0,34.5),(68,34.5)])
        self.assertEqual(layers['nodes'],[(34.5,34.5,3)])
        self.assertEqual(layers['clipping'],dict(large_components=1,clipped_paths=3,outside_nodes=1))
        self.assertEqual(len(rows[0]['graph']['nodes']),2)

    def test_declared_locus_context_has_no_reading_hints(self):
        run=self.f.run_to_review(); q=self.api.review(run,limit=100)
        first=self.f.eligible[0]['region_id']
        item=next(x for x in q['items'] if x['region_id']==first)
        rows=self.api.locus_context(item)
        self.assertEqual({x['scheme'] for x in rows},{'Eva-','STA1'})
        self.assertTrue(all(x['status']=='DECLARED' and x['locus']=='f1r.1' and 'units' not in x and 'text' not in x for x in rows))
        with self.assertRaises(ValueError):self.api.locus_context(dict(item,page=99))
        other=next((x for x in q['items'] if x['region_id']!=first),None)
        if other is not None:self.assertTrue(all(x['status']=='UNDECLARED' for x in self.api.locus_context(other)))

    def test_no_hybrid_evidence_keeps_legacy_review(self):
        run=self.f.run_to_review(); item=self.api.review(run,limit=1)['items'][0]
        with self.assertRaisesRegex(ValueError,'No hybrid evidence'):self.api.vector_context(item,'majority')
        self.assertIsNotNone(self.api.crop(item)[0])

    def test_offline_draft_and_authoritative_subprocess(self):
        run=self.f.run_to_review(); q=self.api.review(run); item=q['items'][0]; path=self.api.stage_decision(item,q['snapshot'],q['inventory'],'fixture','glyph',{'Eva-':{'state':'mapped','label':'a'},'STA1':{'state':'absent','label':None}})
        self.assertEqual(self.f.app.review_items(run)['snapshot']['resolved'],0); self.assertEqual(c.load(self.root/path)['candidate_id'],item['id'])
        result=self.api.command(sys.executable,'decide',path); self.assertEqual(result['resolved'],1)
        self.assertNotIn(item['id'],[x['id'] for x in self.api.review(run)['items']]); self.assertEqual(self.api.command(sys.executable,'decide',path),result)
        with self.assertRaises(ValueError): self.api.command(sys.executable,'watch',path)

    def test_invalid_draft_and_tampered_crop(self):
        run=self.f.run_to_review(); q=self.api.review(run); item=q['items'][0]
        with self.assertRaises(ValueError): self.api.stage_decision(item,q['snapshot'],q['inventory'],'r','glyph',{})
        with self.assertRaises(ValueError): self.api.stage_decision(item,q['snapshot'],q['inventory'],'r','glyph',{'Eva-':{'state':'mapped','label':'fake'},'STA1':{'state':'unknown','label':None}})
        (self.root/item['crop']['path']).write_bytes(b'bad')
        with self.assertRaises(ValueError): self.api.crop(item)

    def test_visual_catalog_and_import(self):
        image=self.root/'glyph.png'; Image.new('L',(20,30),30).save(image)
        r=self.f.file('catalog.json',dict(schema=1,preview=True,schemes=[dict(id='Eva-',name='EVA',version='fixture',source='synthetic',coverage='subset',entries=[dict(label='a',samples=[dict(file='glyph.png',sha256=sha(image),source='fixture page')])])]))
        cat=self.api.catalog(r['path']); self.assertIn('a',cat['Eva-']['entries']); self.assertNotIn('STA1',cat); self.assertEqual(self.api.reference_image(cat['Eva-']['entries']['a'][0][0]).size,(20,30))
        p=self.api.import_source(self.root/'source.pdf','manuscript'); self.assertEqual(p['details']['pages'],2); self.assertEqual(p,self.api.import_source(self.root/'source.pdf','manuscript')); self.assertEqual(self.api.import_source(self.root/'eva.txt','transcription')['details']['loci'],1)
        with self.assertRaises(Exception): self.api.import_source(image,'manuscript')
        image.write_bytes(b'changed')
        with self.assertRaises(ValueError): self.api.catalog(r['path'])
        with self.assertRaises(ValueError): safe(self.root,'../outside')

    def test_manifest_verification_without_ml_import(self):
        p=self.f.file('manifest.json',self.f.m)['path']; code='import sys; from vrs_desktop_api import Desktop; a=Desktop(sys.argv[1]); a.manifest_info(sys.argv[2]); assert not any(x in sys.modules for x in ("torch","numpy","fitz"))'
        proc=subprocess.run([sys.executable,'-S','-c',code,str(self.root),p],capture_output=True,text=True,timeout=30); self.assertEqual(proc.returncode,0,proc.stderr)

    def test_manifest_builder_and_sources_registry(self):
        roles={k:v['path'] for k,v in self.f.m['inputs'].items()}; trans=[r['path'] for r in self.f.m['transcriptions']]
        info=self.api.make_manifest(roles,trans); self.assertEqual(info['inventories'],{'Eva-':2,'STA1':2}); self.assertFalse(info['approved']); self.assertEqual(self.api.manifest_info(info['path'])['run_id'],info['run_id'])
        self.assertEqual(self.api.command(sys.executable,'register',info['path'])['run_id'],info['run_id'])
        one=self.api.import_source(self.root/'source.pdf','manuscript'); two=self.api.import_source(self.root/'eva.txt','transcription'); self.assertEqual({r['sha256'] for r in self.api.sources()},{one['sha256'],two['sha256']})
        (self.root/one['path']).write_bytes(b'corrupt')
        with self.assertRaises(ValueError): self.api.sources()

    def test_catalog_builder_and_draft_replay(self):
        import fitz
        path=self.root/'visual.pdf'
        with fitz.open() as doc:
            page=doc.new_page(width=100,height=100); page.draw_rect(fitz.Rect(30,20,40,70),color=None,fill=(0,0,0)); doc.save(path)
        plan=self.f.file('catalog-plan.json',dict(schema=1,source='fixture PDF',source_sha256=sha(path),version='fixture',rights='synthetic',reviewed=False,entries=[dict(scheme='basic-eva',label='a',page=1,box=[20,10,60,80])]))
        with self.assertRaises(ValueError): self.api.build_catalog('visual.pdf',plan['path'],False)
        built=self.api.build_catalog('visual.pdf',plan['path'],True); catalog=self.api.catalog(built['path']); self.assertTrue(catalog['basic-eva']['preview'])
        run=self.f.run_to_review(); q=self.api.review(run); rel=self.api.stage_decision(q['items'][0],q['snapshot'],q['inventory'],'fixture','false_positive',{}); self.assertEqual(self.api.drafts()[0]['path'],rel)
        self.assertEqual(self.api.submit_draft(sys.executable,rel)['resolved'],1)
        with self.assertRaises(ValueError): self.api.submit_draft(sys.executable,'source.pdf')

    def test_isolated_review_process_without_compute_packages(self):
        import PIL, shutil
        run=self.f.run_to_review()
        with tempfile.TemporaryDirectory() as d:
            lib=Path(d); source=Path(PIL.__file__).parent; shutil.copytree(source,lib/'PIL',ignore=shutil.ignore_patterns('__pycache__'))
            if (source.parent/'pillow.libs').exists(): shutil.copytree(source.parent/'pillow.libs',lib/'pillow.libs')
            code="import sys; sys.path.insert(0,sys.argv[1]); import tkinter as tk; from vrs_desktop_api import Desktop; from PIL import ImageTk; a=Desktop(sys.argv[2]); q=a.review(sys.argv[3]); im,_=a.crop(q['items'][0]); w=tk.Tk(); p=ImageTk.PhotoImage(im); w.destroy(); assert not any(x in sys.modules for x in ('torch','numpy','fitz')); print('ISOLATED_REVIEW_PASS')"
            proc=subprocess.run([sys.executable,'-S','-c',code,d,str(self.root),run],capture_output=True,text=True,timeout=30); self.assertEqual(proc.returncode,0,proc.stderr); self.assertIn('ISOLATED_REVIEW_PASS',proc.stdout)

    def test_actual_gui(self):
        import tkinter as tk
        from vrs_desktop import App
        run=self.f.run_to_review();image=self.root/'visual-fixture.png';Image.new('RGB',(40,30),'white').save(image);catalog=self.f.file('visual-fixture.json',dict(schema=1,preview=True,schemes=[dict(id='Eva-',name='EVA',version='fixture',source='synthetic',coverage='subset',entries=[dict(label='a',samples=[dict(file=image.name,sha256=sha(image),source='synthetic fixture')])])]))
        cfg=self.api.settings(); cfg.update(reviewer='fixture',interpreter=sys.executable,catalog=catalog['path']); self.api.save_settings(cfg)
        w=tk.Tk(); app=App(w,self.root)
        def settle():
            until=time.monotonic()+15
            while time.monotonic()<until:
                w.update(); time.sleep(.015)
                if app.future is None: w.update(); return
            self.fail('UI task timeout')
        try:
            settle(); self.assertIn(run,app.tree.get_children()); self.assertEqual(app.homecount.cget('text'),'1');self.assertEqual(app.homepending.cget('text'),'1');self.assertEqual(app.homecomplete.cget('text'),'0');app.tree.selection_set(run); app.open_selected(); settle(); self.assertTrue(app.items); self.assertIsNotNone(app.image)
            from vrs_build_portable import RELEASE_VERSION
            self.assertIn(RELEASE_VERSION,w.title());self.assertEqual(float(app.reviewprogress.cget('value')),0)
            app.labels.selection_set(0);app.sample();settle();self.assertEqual(app.maps['Eva-'][0].get(),'unreviewed');app.assign_reference();self.assertEqual(app.maps['Eva-'][0].get(),'mapped')
            app.visual_catalog();settle();modal=next(x for x in w.winfo_children() if isinstance(x,tk.Toplevel));self.assertIn('Eva-',modal.title());modal.destroy();self.assertEqual(set(app.maps),{'Eva-','STA1'}); app.zoom(1.25); self.assertGreater(app.factor,1); app.mode(True); self.assertTrue(app.glyph_only); app.open_page_context(); settle(); self.assertTrue(app.page_active); self.assertEqual(app.page_image.size,(250,250)); app.mode(False); self.assertFalse(app.page_active); app.vectors_loaded((Image.new('RGB',(30,30),'white'),[1,1,5,5],[],1,dict(skeleton=[[(1.5,1.5),(2.5,2.5)]],nodes=[(2.5,2.5,3)],fallback=0,hypotheses={'splits':[('s1',[[1,1,3,5],[3,1,5,5]]),('s2',[[1,1,5,3],[1,3,5,5]])],'pairs':[],'compounds':[]})),'majority'); app.vector_layer.set(app.t('Skeleton')); app.change_vector_layer(); self.assertEqual(len(app.canvas.find_withtag('vector-node')),1); app.vector_layer.set(app.t('Splits')); app.change_vector_layer(); self.assertEqual(len(app.canvas.find_withtag('vector-hypothesis')),2); app.step_hypothesis(1); self.assertEqual(app.vector_index,1); app.mode(False); self.assertFalse(app.vector_active)
            app.kind.set('false_positive'); app.kind_changed(); app.submit(); settle(); self.assertEqual(self.api.review(run)['snapshot']['resolved'],1)
            app.show('Settings'); app.fields['theme'].set('light'); app.fields['language'].set('en'); app.apply(); settle(); self.assertEqual(app.cfg['theme'],'light'); self.assertEqual(app.cfg['language'],'en')
            w.geometry('1024x650'); w.update(); app.show('Review'); settle(); self.assertGreater(app.canvas.winfo_width(),150);self.assertTrue(app.kindbox.winfo_ismapped());self.assertTrue(app.review_side.winfo_ismapped())
            for widget in [app.draft_button,app.submit_button,*app.zoom_controls]:
                self.assertTrue(widget.winfo_ismapped());self.assertGreaterEqual(widget.winfo_width(),widget.winfo_reqwidth());self.assertGreaterEqual(widget.winfo_height(),widget.winfo_reqheight())
            app.show('Home');settle();self.assertTrue(app.home_review.winfo_ismapped());self.assertGreaterEqual(app.home_review.winfo_height(),app.home_review.winfo_reqheight())
        finally:
            if not app.closing: app.close()

if __name__=='__main__': unittest.main()

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import active_review as a
import worker as w


class ActiveReviewTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); self.root=Path(t.name)
        image=self.root/'crop.png'; Image.new('L',(60,25),220).save(image)
        self.manifest=self.root/'manifest.json'; w.write(self.manifest,{'regions':[dict(id='r1',group='leaf1',page=1,file=image.name,sha256=w.sha(image))]})
        self.pred=self.root/'pred.json'; w.write(self.pred,dict(manifest_sha256=w.sha(self.manifest),rows=[dict(region_id='r1',box=[0,0,10,10],predicted='unknown'),dict(region_id='r1',box=[10,0,20,10],predicted='unknown'),dict(region_id='r1',box=[20,0,30,10],predicted='unknown'),dict(region_id='r1',box=[30,0,40,10],predicted='X')]))
        self.refs=self.root/'refs.json'; w.write(self.refs,dict(schema=1,schemes=[dict(id=k,name=k,version='toy',source='synthetic only',entries=[dict(label=l,samples=[dict(file=image.name,sha256=w.sha(image),source='fixture')])]) for k,l in [('EVA-test','x'),('STA-test','y')]]))
        self.out=self.root/'review.json'
    def test_distinct_mapping_and_absence(self):
        s,rows,data=a.open_session(self.manifest,self.pred,self.refs,self.out,'owner')
        self.assertEqual(len(rows),3)
        d=dict(kind='glyph',mapping={'EVA-test':dict(state='mapped',label='x'),'STA-test':dict(state='not_in_inventory',label=None)},note='test')
        a.validate_decision(d,s); data['decisions'][rows[0]['id']]=d; w.write(self.out,data)
        self.assertEqual(a.open_session(self.manifest,self.pred,self.refs,self.out,'owner')[2],data)
        with self.assertRaisesRegex(ValueError,'provenance'): a.open_session(self.manifest,self.pred,self.refs,self.out,'other')
    def test_false_positive_and_unknown(self):
        s=a.catalog(self.refs); m=a.empty_mapping(s)
        a.validate_decision(dict(kind='false_positive',mapping=m,note=''),s)
        a.validate_decision(dict(kind='uncertain',mapping=m,note=''),s)
        a.validate_decision(dict(kind='compound',mapping=m,note=''),s)
        a.validate_decision(dict(kind='glyph',mapping=a.empty_mapping(s,'not_in_inventory'),note='candidate'),s)
        with self.assertRaisesRegex(ValueError,'Mark each'): a.validate_decision(dict(kind='glyph',mapping=m,note=''),s)
        m['EVA-test']=dict(state='mapped',label='x')
        with self.assertRaisesRegex(ValueError,'Non-glyph'): a.validate_decision(dict(kind='false_positive',mapping=m,note=''),s)
    def test_catalog_and_prediction_integrity(self):
        r=w.read(self.refs); r['schemes'][0]['entries'][0]['samples'][0]['sha256']='0'*64; w.write(self.refs,r)
        with self.assertRaisesRegex(ValueError,'provenance'): a.catalog(self.refs)
        p=w.read(self.pred); p['rows'][0]['box']=[-1,0,10,10]; w.write(self.pred,p)
        with self.assertRaisesRegex(ValueError,'box'): a.queue(self.manifest,self.pred)
    @unittest.skipUnless(os.environ.get('DISPLAY') or os.name=='nt','GUI display required')
    def test_gui_review_resume(self):
        import tkinter as tk
        original=tk.Tk; observations=[]; errors=[]
        def create(*args,**kwargs):
            root=original(*args,**kwargs)
            def click():
                try:
                    children=root.winfo_children(); observations.append(children[0].cget('text')); bar=children[-1]; buttons={b.cget('text'):b for b in bar.winfo_children()}
                    if len(observations)==1:
                        panels=children[3].winfo_children()[0].winfo_children()[0].winfo_children()
                        for panel in panels:
                            cell=panel.winfo_children()[-1].winfo_children()[0].winfo_children()[0].winfo_children()[0]
                            cell.winfo_children()[0].invoke()
                        buttons['Zuordnungen speichern'].invoke()
                    elif len(observations)==2:
                        buttons['In keinem geladenen Inventar'].invoke(); buttons['Zuordnungen speichern'].invoke()
                    else: buttons['False Positive'].invoke()
                except Exception as e: errors.append(e)
                finally: root.destroy()
            root.after(150,click); root.after(2500,root.destroy); return root
        with patch('tkinter.Tk',side_effect=create):
            for _ in range(3): a.review(self.manifest,self.pred,self.refs,self.out,'owner')
        self.assertFalse(errors,errors); self.assertIn('1/3',observations[1]); self.assertIn('2/3',observations[2]); d=w.read(self.out)['decisions']; self.assertEqual(len(d),3); self.assertEqual({v['kind'] for v in d.values()},{'glyph','false_positive'}); self.assertEqual({m['state'] for v in d.values() if v['kind']=='glyph' for m in v['mapping'].values()},{'mapped','not_in_inventory'})

if __name__=='__main__': unittest.main()

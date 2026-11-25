import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import fitz
import torch
import worker as w


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pdf = self.root / 'synthetic.pdf'
        doc = fitz.open()
        for i in range(4):
            p = doc.new_page(width=600, height=800)
            p.insert_text((275, 160), 'AB' + str(i), fontsize=12)
            p.draw_circle((300+i, 480), 9+i, color=(0,0,0))
        doc.save(self.pdf); doc.close()
        self.review = self.root / 'review.csv'
        with self.review.open('w', newline='') as f:
            a = csv.writer(f); a.writerow(['review_id','page','text_x','text_y'])
            for i in range(1,5):
                a.writerow([f'T{i}',i,.5,.2]); a.writerow([f'N{i}',i,.5,.6])
        self.groups = self.root / 'groups.json'
        w.write(self.groups,{str(i):f'leaf{i}' for i in range(1,5)})
        self.manifest = self.root / 'data' / 'manifest.json'
        w.prepare(self.pdf,w.sha(self.pdf),self.review,self.groups,self.manifest.parent)
        self.a,self.b = self.root/'a.json',self.root/'b.json'
        labels = {r['id']: 'script' if r['id'].startswith('T') else 'non_script' for r in w.read(self.manifest)['regions']}
        for p,r in [(self.a,'alpha'),(self.b,'beta')]:
            w.write(p,dict(reviewer=r,manifest_sha256=w.sha(self.manifest),labels=labels))
        self.split = self.root/'split.json'
        w.write(self.split,dict(train=['leaf1','leaf2'],test=['leaf3','leaf4']))

    def test_prepare_and_hash(self):
        self.assertEqual(len(w.dataset(self.manifest)['regions']),8)
        with self.assertRaisesRegex(ValueError,'PDF SHA256'):
            w.prepare(self.pdf,'0'*64,self.review,self.groups,self.root/'bad')
        r=w.read(self.manifest)['regions'][0]
        (self.manifest.parent/r['file']).write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'Crop hash'):
            w.dataset(self.manifest)

    def test_split_and_review_guards(self):
        sets,excluded=w.cohorts(self.manifest,self.a,self.b,self.split)
        self.assertEqual([len(sets[x]) for x in ('train','test')],[4,4]); self.assertEqual(sum(excluded.values()),0)
        b=w.read(self.b); b['labels']['N3']='unknown'; w.write(self.b,b)
        self.assertEqual(w.cohorts(self.manifest,self.a,self.b,self.split)[1]['test'],1)
        b['reviewer']='alpha'; w.write(self.b,b)
        with self.assertRaisesRegex(ValueError,'distinct reviewer'):
            w.cohorts(self.manifest,self.a,self.b,self.split)
        b['reviewer']='beta'; w.write(self.b,b)
        w.write(self.split,dict(train=['leaf1','leaf2'],test=['leaf2','leaf3','leaf4']))
        with self.assertRaisesRegex(ValueError,'leakage'):
            w.cohorts(self.manifest,self.a,self.b,self.split)

    def test_cpu_train_resume(self):
        args=(self.manifest,self.a,self.b,self.split)
        full=w.train(*args,self.root/'full',device='cpu',epochs=2,batch=2)
        original=torch.save; calls=[0]
        def interrupt(*a,**kw):
            calls[0]+=1
            if calls[0]==2: raise OSError('simulated interruption')
            return original(*a,**kw)
        with patch('torch.save',side_effect=interrupt), self.assertRaisesRegex(OSError,'simulated'):
            w.train(*args,self.root/'resumed',device='cpu',epochs=2,batch=2)
        resumed=w.train(*args,self.root/'resumed',device='cpu',epochs=2,batch=2,resume=True)
        self.assertEqual(full['losses'],resumed['losses']); self.assertEqual(full['counts'],resumed['counts'])
        self.assertEqual(sum(resumed['counts'].values()),4)
        with self.assertRaisesRegex(ValueError,'Completed output'):
            w.train(*args,self.root/'full',device='cpu',epochs=2,batch=2)

    def test_device(self):
        self.assertEqual(w.device_info('cpu')['device'],'cpu')
        if not torch.cuda.is_available():
            self.assertEqual(w.device_info('auto')['device'],'cpu')
            with self.assertRaisesRegex(RuntimeError,'CUDA required'):
                w.device_info('cuda')

if __name__=='__main__': unittest.main()

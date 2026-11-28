import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import vrs_rc2_holdout as h

class HoldoutTests(unittest.TestCase):
    def fixture(self):
        def window(i,kind,extent,boxes,exhaustive=True):
            return dict(id=i,page=4,leaf='leaf-holdout',image_sha256='a'*64,size=[100,100],box=extent,kind=kind,exhaustive=exhaustive,boxes=boxes)
        r=dict(schema=1,source_sha256='b'*64,registration_sha256='c'*64,rights_sha256='d'*64,independent_review_sha256='e'*64,development_leaves=['leaf-dev'],windows=[
            window('positive','glyph',[0,0,50,50],[[0,0,10,10],[20,20,30,30]]),
            window('negative','illustration',[50,0,100,50],[]),
            window('partial','compound',[0,50,50,100],[[0,50,10,60]],False),
            window('unknown','unknown',[50,50,100,100],[],False)])
        rows={'positive':[[0,0,10,10],[0,0,10,10]],'negative':[[60,10,70,20]],'partial':[[0,50,10,60],[20,60,30,70]],'unknown':[[60,60,70,70]]}
        p=dict(schema=1,source_sha256='b'*64,reference_sha256='f'*64,freeze_sha256='1'*64,methods={k:dict(implementation_sha256='2'*64,windows=copy.deepcopy(rows)) for k in h.METHODS})
        return r,p
    def test_denominators(self):
        r,p=self.fixture();out=h.evaluate(r,p,'f'*64)
        for row in out['methods'].values():
            for m in row['thresholds'].values():
                self.assertEqual((m['tp'],m['fn'],m['fp'],m['unresolved'],m['excluded_predictions']),(2,1,2,1,1))
                self.assertEqual(m['annotated_reference_recall'],2/3)
                self.assertIsNone(m['scored_precision'])
                self.assertEqual(m['negative_predictions_by_class']['illustration'],1)
            self.assertEqual(row['overlap_diagnostics']['split_overlap'],1)
        self.assertEqual(out['status'],'METRICS_ONLY_NOT_SCIENTIFIC_ACCEPTANCE')
    def test_augmenting_path(self):
        self.assertEqual(h.match([(0,0,20,10),(0,0,10,10)],[(0,0,10,10),(10,0,20,10)],(1,2)),2)
        self.assertEqual(h.match([(0,0,20,10)],[(0,0,10,10),(10,0,20,10)],(3,4)),0)
    def test_fail_closed(self):
        r,p=self.fixture()
        for change in ('leak','missing','source','negative','overlap','outside'):
            a,b=copy.deepcopy(r),copy.deepcopy(p)
            if change=='leak':a['development_leaves'].append('leaf-holdout')
            elif change=='missing':del b['methods']['vector']['windows']['positive']
            elif change=='source':b['source_sha256']='0'*64
            elif change=='negative':a['windows'][1]['exhaustive']=False
            elif change=='overlap':a['windows'][1]['box']=[40,0,100,50]
            elif change=='outside':b['methods']['raster']['windows']['positive']=[[0,0,100,100]]
            with self.subTest(change=change),self.assertRaises(ValueError):h.evaluate(a,b,'f'*64)
    def test_pins_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.json';raw=b'{"a":1,"a":2}';p.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'Duplicate'):h.read_pinned(p,hashlib.sha256(raw).hexdigest())
            with self.assertRaisesRegex(ValueError,'pin'):h.read_pinned(p,'0'*64)

if __name__=='__main__':unittest.main()

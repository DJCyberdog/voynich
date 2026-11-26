import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import vrs_inference as v
import vrs_hardware as h
import glyphs as g
import test_glyphs


class InferenceTests(unittest.TestCase):
    def test_order_and_batch_bound(self):
        admissions=[]
        rows=list(v.ordered_batches(range(11),lambda x:x*2,lambda xs:[x+1 for x in xs],batch=3,workers=2,admit=admissions.append))
        self.assertEqual(rows,[(x,2*x+1) for x in range(11)])
        self.assertEqual(admissions,[3,3,3,3])

    def test_failure_no_fallback(self):
        def fail(xs): raise MemoryError()
        with self.assertRaises(h.ResourceBlocked):
            list(v.ordered_batches(range(4),lambda x:x,fail,batch=2,workers=2,admit=lambda n:None))
        with self.assertRaisesRegex(ValueError,'cardinality'):
            list(v.ordered_batches(range(2),lambda x:x,lambda xs:[],batch=2,workers=1,admit=lambda n:None))

    def test_admission_blocks_before_prepare(self):
        seen=[]
        def reject(n): raise h.ResourceBlocked('pressure')
        with self.assertRaises(h.ResourceBlocked):
            list(v.ordered_batches(range(2),seen.append,lambda xs:xs,batch=2,workers=1,admit=reject))
        self.assertEqual(seen,[])

    def test_minimum_profiles(self):
        i=dict(machine='AMD64',system='Windows',physical=6,allowed=12,ram_total=16*h.GIB,disk_free=60*h.GIB,gpu=dict(ok=True,total=16*h.GIB))
        self.assertTrue(v.minimum(i,'cuda')['meets_checked_minimum'])
        self.assertFalse(v.minimum(dict(i,ram_total=8*h.GIB),'cpu')['meets_checked_minimum'])
        self.assertTrue(v.minimum(dict(i,ram_total=8*h.GIB,gpu=None),'review')['meets_checked_minimum'])
        self.assertFalse(v.minimum(dict(i,gpu=None),'cuda')['meets_checked_minimum'])
        self.assertTrue(v.minimum(i,'cuda')['unverified'])

    def test_legacy_prediction_equivalence(self):
        f=test_glyphs.GlyphTests(); f.setUp(); self.addCleanup(f.doCleanups)
        out=f.root/'model'; g.train(f.manifest,f.a,f.b,f.alphabet,f.split,out,'cpu')
        args=(f.manifest,f.a,f.alphabet,out/'glyph_model.json',out/'glyph_report.json')
        old=g.predict(*args,f.root/'legacy.json','cpu')
        # Host is intentionally below product minimum; inject resource snapshot only.
        info=dict(allowed=4,ram_total=16*h.GIB,ram_available=12*h.GIB,disk_free=100*h.GIB,gpu=None)
        with patch.object(h,'snapshot',return_value=info):
            new=v.predict(*args,f.root/'adaptive.json',device='cpu')
            serial=v.predict(*args,f.root/'serial.json',device='cpu',serial=True)
        self.assertEqual(old['rows'],new['rows']); self.assertEqual(old['rows'],serial['rows'])
        self.assertEqual(old['excluded_regions'],new['excluded_regions'])
        self.assertEqual(new['scientific_status'],'UNADJUDICATED')
        self.assertGreater(new['operational']['batch'],1)

    def test_estimates_scale(self):
        a=v.workload_estimate(100,2,100,10); b=v.workload_estimate(200,10,100,10)
        self.assertGreater(b['ram_item'],a['ram_item']); self.assertGreater(b['vram_item'],a['vram_item'])


if __name__=='__main__': unittest.main()

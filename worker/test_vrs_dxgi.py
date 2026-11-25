import unittest
from unittest.mock import MagicMock, patch

import glyphs as g
import test_glyphs
import vrs_backends as b
import vrs_dxgi as dx
import vrs_hardware as h


class DXGITests(unittest.TestCase):
    def setUp(self):
        self.api=MagicMock(); self.api.device_count.return_value=1; self.api.device_name.return_value='GPU fixture'
        self.row=dict(name='GPU fixture',luid=(0,42),dedicated=8*h.GIB,budget=6*h.GIB,usage=h.GIB)

    def test_budget_is_process_local_not_global(self):
        r=dx.memory(self.api,0,enumerate_fn=lambda:[self.row])
        self.assertEqual((r['free'],r['total'],r['luid']),(5*h.GIB,6*h.GIB,[0,42]))
        self.row['budget']=12*h.GIB
        self.assertEqual(dx.memory(self.api,0,enumerate_fn=lambda:[self.row])['free'],7*h.GIB)
        self.row['usage']=13*h.GIB
        self.assertEqual(dx.memory(self.api,0,enumerate_fn=lambda:[self.row])['free'],0)

    def test_identity_and_unsupported_devices(self):
        for rows in ([],[self.row,self.row],[dict(self.row,name='other')],[dict(self.row,dedicated=0)],[dict(self.row,budget=0)]):
            with self.assertRaises(h.ResourceBlocked): dx.memory(self.api,0,enumerate_fn=lambda:rows)
        with self.assertRaises(h.ResourceBlocked): dx.memory(self.api,0,[0,43],lambda:[self.row])
        self.api.device_count.return_value=2
        with self.assertRaises(h.ResourceBlocked): dx.memory(self.api,0,enumerate_fn=lambda:[self.row])

    def test_failed_query(self):
        with self.assertRaises(h.ResourceBlocked): dx.memory(self.api,0,enumerate_fn=MagicMock(side_effect=OSError('fixture')))
        with patch.object(dx.sys,'platform','linux'):
            with self.assertRaises(h.ResourceBlocked): dx.enumerate_budgets()

    def test_directml_qualification_and_post_admission(self):
        f=test_glyphs.GlyphTests(); f.setUp(); self.addCleanup(f.doCleanups)
        out=f.root/'model'; g.train(f.manifest,f.a,f.b,f.alphabet,f.split,out,'cpu')
        args=(f.manifest,f.a,f.alphabet,out/'glyph_model.json',out/'glyph_report.json')
        old=g.predict(*args,f.root/'legacy-dml.json','cpu')
        info=dict(allowed=4,ram_total=16*h.GIB,ram_available=12*h.GIB,disk_free=100*h.GIB)
        # Actual image/classifier path on CPU with simulated DirectML transport and budget.
        with patch.object(b,'resolve',return_value=(self.api,'cpu')),patch.object(dx,'enumerate_budgets',return_value=[self.row]),patch.object(h,'snapshot',side_effect=lambda *a:info.copy()):
            value=b.qualify(*args,f.root/'dml.json',backend='directml',limits={'batch_items':1})
            self.assertEqual(value['rows'],old['rows']); self.assertEqual(value['environment']['device'],'directml')
            self.assertEqual(value['operational']['native_acceptance'],'UNVERIFIED')
            original=b.exact_classify
            def pressure(*a):
                result=original(*a)
                if len(a[2])==1: self.row['usage']=self.row['budget']
                return result
            with patch.object(b,'exact_classify',side_effect=pressure):
                with self.assertRaises(h.ResourceBlocked): b.qualify(*args,f.root/'blocked-dml.json',backend='directml',limits={'batch_items':1})
            self.assertFalse((f.root/'blocked-dml.json').exists())
            self.api.synchronize.assert_not_called()


if __name__=='__main__': unittest.main()

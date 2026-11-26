import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import glyphs as g
import test_glyphs
import vrs_hardware as h
import vrs_inference as v
import vrs_resources as r
import vrs_core as core


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.info=dict(allowed=12,ram_total=16*h.GIB,ram_available=13*h.GIB,disk_free=100*h.GIB,gpu=dict(ok=True,index=0,total=16*h.GIB,free=14*h.GIB))
        self.work=dict(ram_base=h.GIB,ram_item=32*h.MIB,vram_base=2*h.GIB,vram_item=64*h.MIB,disk=20*h.GIB,items=10000)

    def test_limits_are_ceilings(self):
        p=r.plan(self.info,self.work,overrides=dict(cpu_workers=3,ram_bytes=4*h.GIB,vram_bytes=4*h.GIB,cache_bytes=64*h.MIB,batch_items=17))
        self.assertEqual(p['cpu_workers'],3)
        self.assertLessEqual(p['batch_ceiling'],17)
        self.assertLessEqual(self.work['ram_base']+2*p['batch_ceiling']*self.work['ram_item']+p['cache_budget'],p['ram_budget'])
        self.assertLessEqual(self.work['vram_base']+p['batch_ceiling']*self.work['vram_item'],p['vram_budget'])
        self.assertLessEqual(p['cache_budget'],64*h.MIB)
        self.assertEqual(r.plan(self.info,self.work,overrides={'cpu_workers':1000})['cpu_workers'],r.plan(self.info,self.work)['cpu_workers'])

    def test_invalid_or_impossible_limits(self):
        for bad in ({'x':1},{'cpu_workers':True},{'ram_bytes':-1},{'batch_items':0}):
            with self.assertRaises(ValueError): r.plan(self.info,self.work,overrides=bad)
        for bad in ({'ram_bytes':1},{'vram_bytes':0},{'disk_bytes':0}):
            with self.assertRaises(h.ResourceBlocked): r.plan(self.info,self.work,overrides=bad)

    def test_presets_and_scaling(self):
        self.assertEqual(r.plan(self.info,self.work,preset='silent'),r.plan(self.info,self.work,preset='quiet'))
        p=[r.plan(self.info,self.work,preset=x) for x in ('silent','balanced','performance')]
        self.assertLess(p[0]['batch_ceiling'],p[2]['batch_ceiling'])
        big=dict(self.info,allowed=32,ram_total=128*h.GIB,ram_available=110*h.GIB,gpu=dict(ok=True,index=0,total=48*h.GIB,free=45*h.GIB))
        q=r.plan(big,self.work)
        self.assertGreater(q['batch_ceiling'],p[2]['batch_ceiling'])
        self.assertGreater(q['cpu_workers'],p[2]['cpu_workers'])

    def test_cache_eviction_resize_disable(self):
        c=r.FeatureCache(1100)
        c.put('a',b'1'); c.put('b',b'2'); self.assertEqual(c.get('a'),b'1')
        c.put('c',b'3'); self.assertIsNone(c.get('b'))
        c.resize(0); self.assertEqual(c.stats()['used'],0)
        c.put('d',b'4'); self.assertIsNone(c.get('d'))
        with self.assertRaises(ValueError): c.put('x',bytearray(b'x'))

    def test_cache_concurrent_bound(self):
        c=r.FeatureCache(8192)
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda i:c.put(i,b'x'*1024),range(100)))
        self.assertLessEqual(c.stats()['used'],8192)
        self.assertGreater(c.stats()['evictions'],0)

    def test_prediction_parity_with_limits_and_cache(self):
        import torch
        f=test_glyphs.GlyphTests(); f.setUp(); self.addCleanup(f.doCleanups)
        out=f.root/'model'; g.train(f.manifest,f.a,f.b,f.alphabet,f.split,out,'cpu')
        args=(f.manifest,f.a,f.alphabet,out/'glyph_model.json',out/'glyph_report.json')
        old=g.predict(*args,f.root/'legacy-b.json','cpu'); previous=torch.get_num_threads()
        info=dict(self.info,gpu=None)
        with patch.object(h,'snapshot',return_value=info):
            for i,preset in enumerate(('silent','balanced','performance')):
                result=v.predict(*args,f.root/f'b{i}.json',device='cpu',preset=preset,limits={'cpu_workers':1,'batch_items':2,'cache_bytes':0 if i==0 else 65536})
                self.assertEqual(result['rows'],old['rows'])
                self.assertEqual(result['operational']['workers'],0)
                self.assertEqual(result['operational']['torch_threads'],1)
                self.assertLessEqual(result['operational']['batch'],2)
                self.assertEqual(torch.get_num_threads(),previous)

    def test_duplicate_source_cache_hit_and_pressure(self):
        f=test_glyphs.GlyphTests(); f.setUp(); self.addCleanup(f.doCleanups)
        out=f.root/'model'; g.train(f.manifest,f.a,f.b,f.alphabet,f.split,out,'cpu')
        # Inference-only repeat after training, not a change to the scientific split.
        m=core.read(f.manifest); row=dict(m['regions'][0],id='repeat',page=5,group='repeat')
        m['regions'].append(row); core.write(f.manifest,m)
        a=core.read(f.a); a['manifest_sha256']=core.sha(f.manifest); a['regions']['repeat']=a['regions']['r0']; core.write(f.a,a)
        args=(f.manifest,f.a,f.alphabet,out/'glyph_model.json',out/'glyph_report.json')
        old=g.predict(*args,f.root/'legacy-repeat.json','cpu')
        info=dict(self.info,gpu=None)
        with patch.object(h,'snapshot',return_value=info):
            value=v.predict(*args,f.root/'cached.json',device='cpu',limits={'cpu_workers':1,'batch_items':2,'cache_bytes':65536})
            self.assertEqual(value['rows'],old['rows'])
            self.assertEqual(value['operational']['cache']['hits'],2)
            self.assertGreater(value['operational']['cache']['used'],0)
            estimate=v.workload_estimate(100*44,2,10,1024**2)
            low=dict(info,ram_available=2*h.GIB+estimate['ram_base']+4*estimate['ram_item'])
            with patch.object(v,'fresh',return_value=low):
                value=v.predict(*args,f.root/'pressure.json',device='cpu',limits={'cpu_workers':1,'batch_items':2,'cache_bytes':65536})
            self.assertEqual(value['rows'],old['rows'])
            self.assertEqual(value['operational']['cache']['budget'],0)
            with patch.object(v,'fresh',return_value=dict(info,ram_available=h.GIB)):
                with self.assertRaises(h.ResourceBlocked): v.predict(*args,f.root/'blocked.json',device='cpu')
            self.assertFalse((f.root/'blocked.json').exists())

    def test_thread_limit_restored_on_failure(self):
        import torch
        previous=torch.get_num_threads()
        def fail(*args,**kwargs):
            torch.set_num_threads(1)
            raise h.ResourceBlocked('fixture')
        with patch.object(v,'_predict',side_effect=fail):
            with self.assertRaises(h.ResourceBlocked): v.predict()
        self.assertEqual(torch.get_num_threads(),previous)


if __name__=='__main__': unittest.main()

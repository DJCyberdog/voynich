import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import glyphs as g
import test_glyphs
import vrs_core as core
import vrs_hardware as h
import vrs_workstation as w


class WorkstationTests(unittest.TestCase):
    def setUp(self):
        self.info=dict(allowed=12,ram_total=16*h.GIB,ram_available=13*h.GIB,disk_free=100*h.GIB,gpu=None)
        self.work=dict(ram_base=256*h.MIB,ram_item=2*h.MIB,vram_base=256*h.MIB,vram_item=h.MIB,disk=1024**2,items=10000)
        self.devices=[dict(ok=True,index=i,total=16*h.GIB,free=14*h.GIB) for i in range(2)]

    def test_partition_deterministic_and_complete(self):
        weights=[('a',5),('b',10),('c',2),('d',8),('e',1)]
        groups=w.partition(weights,[1,2]); self.assertEqual(groups,w.partition(weights,[1,2]))
        self.assertEqual(sorted(x for group in groups for x in group),list('abcde'))
        self.assertTrue(all(group==sorted(group) for group in groups))
        with self.assertRaises(ValueError): w.partition(weights,[1]*6)
        with self.assertRaises(ValueError): w.partition([('a',1),('a',2)],[1])

    def test_aggregate_budgets(self):
        p=w.budgets(self.info,self.work,self.devices,overrides={'cpu_workers':6,'ram_bytes':8*h.GIB,'vram_bytes':4*h.GIB,'cache_bytes':16*h.MIB,'disk_bytes':10*h.GIB})
        children=[x['limits'] for x in p['plans']]
        self.assertLessEqual(sum(x['cpu_workers'] for x in children),p['cpu_slots'])
        self.assertLessEqual(sum(x['ram_bytes'] for x in children),p['host_ram_budget'])
        self.assertLessEqual(sum(x['cache_bytes'] for x in children),16*h.MIB)
        self.assertLessEqual(sum(x['disk_bytes'] for x in children),p['disk_budget']//2)
        self.assertTrue(all(x['vram_bytes']==4*h.GIB for x in children))
        self.assertEqual([x['index'] for x in p['plans']],[0,1])
        with self.assertRaises(ValueError): w.budgets(self.info,self.work,[self.devices[0]]*2)
        with self.assertRaises(ValueError): w.budgets(self.info,self.work,[None,self.devices[1]])
        with self.assertRaises(ValueError): w.budgets(self.info,self.work,self.devices,overrides={'cpu_workers':1})
        with self.assertRaises(h.ResourceBlocked): w.budgets(self.info,self.work,self.devices,overrides={'disk_bytes':0})

    def test_larger_system_scales(self):
        p=w.budgets(self.info,self.work,self.devices)
        big=dict(self.info,allowed=48,ram_total=128*h.GIB,ram_available=100*h.GIB)
        devices=[dict(ok=True,index=i,total=48*h.GIB,free=45*h.GIB) for i in range(2)]
        q=w.budgets(big,self.work,devices)
        self.assertGreater(q['host_ram_budget'],p['host_ram_budget'])
        self.assertGreater(q['cpu_slots'],p['cpu_slots'])
        self.assertGreater(q['plans'][0]['capacity'],p['plans'][0]['capacity'])

    def test_merge_rejects_coverage_and_binding(self):
        expected={'a':[(0,0,1,1)],'b':[(1,1,2,2)]}; groups=[['b'],['a']]; binding={'model_sha256':'a'*64}
        def report(rid):
            return dict(version='test',scientific_status='UNADJUDICATED',environment={'device':'cpu'},**binding,excluded_regions=0,rows=[dict(region_id=rid,box=list(expected[rid][0]),predicted='unknown',distance=.1,margin=.01)])
        reports=[report('b'),report('a')]
        self.assertEqual([x['region_id'] for x in w.merge(reports,groups,expected,set(),binding,'cpu')['rows']],['a','b'])
        for field,value in [('model_sha256','b'*64),('excluded_regions',1),('rows',[])]:
            bad=copy.deepcopy(reports); bad[0][field]=value
            with self.assertRaises(ValueError): w.merge(bad,groups,expected,set(),binding,'cpu')
        with self.assertRaises(ValueError): w.merge(reports,[['a'],['a']],expected,set(),binding,'cpu')

    def fixture(self):
        f=test_glyphs.GlyphTests(); f.setUp(); self.addCleanup(f.doCleanups)
        out=f.root/'model'; g.train(f.manifest,f.a,f.b,f.alphabet,f.split,out,'cpu')
        return f,(f.manifest,f.a,f.alphabet,out/'glyph_model.json',out/'glyph_report.json')

    def test_actual_two_cpu_processes(self):
        f,args=self.fixture(); old=g.predict(*args,f.root/'legacy.json','cpu')
        # Real subprocess execution; resource availability checked by parent AND each child.
        result=w.run(*args,f.root/'sharded.json',cpu_processes=2,timeout=90)
        self.assertEqual(result['rows'],old['rows']); self.assertEqual(result['excluded_regions'],old['excluded_regions'])
        self.assertEqual(len(result['operational']['shards']),2)
        self.assertEqual(sum(x['candidates'] for x in result['operational']['shards']),len(old['rows']))
        self.assertEqual(list(f.root.glob('.vrs-shards-*')),[])
        with self.assertRaises(ValueError): w.run(*args,f.root/'sharded.json',cpu_processes=2)

    def test_shard_failure_no_output(self):
        f,args=self.fixture(); output=f.root/'fail.json'
        with patch.object(w,'execute',side_effect=h.ResourceBlocked('fixture failure')):
            with self.assertRaises(h.ResourceBlocked): w.run(*args,output,cpu_processes=1)
        self.assertFalse(output.exists()); self.assertEqual(list(f.root.glob('.vrs-shards-*')),[])

    def test_cuda_probe_failure_no_fallback(self):
        f,args=self.fixture(); output=f.root/'cuda.json'
        with patch.object(w,'probe',side_effect=h.ResourceBlocked('fixture unavailable')):
            with self.assertRaises(h.ResourceBlocked): w.run(*args,output,gpu_indices=[0,1])
        self.assertFalse(output.exists())
        with self.assertRaises(ValueError): w.run(*args,output,gpu_indices=[0,0])


if __name__=='__main__': unittest.main()

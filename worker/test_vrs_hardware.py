import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock
import vrs_hardware as h


class HardwareTests(unittest.TestCase):
    def setUp(self):
        self.info = dict(allowed=12, ram_total=16*h.GIB, ram_available=13*h.GIB,
                         disk_free=100*h.GIB, gpu=dict(ok=True,index=0,total=16*h.GIB,free=14*h.GIB))
        self.work = dict(ram_base=h.GIB,ram_item=32*h.MIB,vram_base=2*h.GIB,
                         vram_item=64*h.MIB,disk=20*h.GIB,items=10000)

    def test_owner_default_and_budget(self):
        p=h.plan(self.info,self.work)
        self.assertEqual((p['preset'],p['backend'],p['gpu_index']),('performance','cuda',0))
        self.assertLessEqual(p['cpu_workers'],12)
        self.assertLessEqual(self.work['ram_base']+p['batch_ceiling']*self.work['ram_item'],p['ram_budget'])
        self.assertLessEqual(self.work['vram_base']+p['batch_ceiling']*self.work['vram_item'],p['vram_budget'])
        self.assertGreaterEqual(p['ram_reserve'],2*h.GIB)
        self.assertGreaterEqual(p['vram_reserve'],h.GIB)

    def test_high_capacity_not_capped(self):
        big=dict(self.info,allowed=32,ram_total=128*h.GIB,ram_available=110*h.GIB,
                 gpu=dict(ok=True,index=0,total=48*h.GIB,free=45*h.GIB))
        a,b=h.plan(self.info,self.work),h.plan(big,self.work)
        self.assertGreater(b['batch_ceiling'],a['batch_ceiling'])
        self.assertGreater(b['cpu_workers'],a['cpu_workers'])

    def test_preset_order(self):
        batches=[h.plan(self.info,self.work,preset=p)['batch_ceiling'] for p in ('quiet','balanced','performance')]
        self.assertEqual(batches,sorted(batches))
        self.assertGreater(batches[-1],batches[0])

    def test_explicit_cuda_and_auto(self):
        info=dict(self.info,gpu=dict(ok=False,reason='kernel unavailable'))
        with self.assertRaisesRegex(h.ResourceBlocked,'Explicit CUDA'): h.plan(info,self.work,'cuda')
        p=h.plan(info,self.work,'auto')
        self.assertEqual((p['backend'],p['fallback_reason']),('cpu','kernel unavailable'))
        self.assertEqual(h.plan(self.info,self.work,'cpu')['backend'],'cpu')

    def test_low_resources_and_storage(self):
        for info in (dict(self.info,ram_available=h.GIB),dict(self.info,disk_free=24*h.GIB),
                     dict(self.info,gpu=dict(ok=True,index=0,total=16*h.GIB,free=h.GIB))):
            with self.assertRaises(h.ResourceBlocked): h.plan(info,self.work)

    def test_runtime_pressure_no_fallback(self):
        p=h.plan(self.info,self.work)
        h.admit_next(self.info,p,h.MIB,h.MIB)
        for info in (dict(self.info,ram_available=h.GIB),dict(self.info,disk_free=0),
                     dict(self.info,gpu=dict(ok=False)),dict(self.info,gpu=dict(ok=True,index=1,free=14*h.GIB)),
                     dict(self.info,gpu=dict(ok=True,index=0,free=0))):
            with self.assertRaises(h.ResourceBlocked): h.admit_next(info,p,h.MIB,h.MIB)
        with self.assertRaises(h.ResourceBlocked): h.admit_next(self.info,p,p['ram_budget']+1)
        self.assertEqual(p['backend'],'cuda')

    def test_oom_is_not_retried(self):
        for exc in (MemoryError(),RuntimeError('CUDA out of memory')):
            fn=MagicMock(side_effect=exc)
            with self.assertRaises(h.ResourceBlocked): h.bounded_call(fn)
            fn.assert_called_once()
        with self.assertRaisesRegex(RuntimeError,'unrelated'): h.bounded_call(MagicMock(side_effect=RuntimeError('unrelated')))
        self.assertEqual(h.bounded_call(lambda: 7),7)

    def test_invalid_estimates(self):
        for bad in (dict(self.work,ram_item=0),dict(self.work,items=True),dict(self.work,vram_item=0),dict(self.work,extra=1)):
            with self.assertRaises(ValueError): h.plan(self.info,bad)

    def test_cuda_requires_real_operation(self):
        t=MagicMock(); t.cuda.is_available.return_value=True; t.cuda.device_count.return_value=1
        t.cuda.mem_get_info.return_value=(14*h.GIB,16*h.GIB)
        t.cuda.get_device_properties.return_value.name='RTX test fixture'; t.cuda.get_device_capability.return_value=(12,0)
        t.cuda.get_arch_list.return_value=['sm_120']; t.__version__='mock'; t.version.cuda='mock'
        t.ones.return_value.__matmul__.return_value.__eq__.return_value.all.return_value.item.return_value=True
        self.assertTrue(h.cuda_probe(t)['ok']); t.cuda.synchronize.assert_called_once_with(0)
        t.ones.side_effect=RuntimeError('no kernel image')
        self.assertFalse(h.cuda_probe(t)['ok'])
        t.cuda.is_available.return_value=False
        self.assertFalse(h.cuda_probe(t)['ok'])

    def test_actual_review_diagnostics_no_torch(self):
        code='''import sys
class Block:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0]=='torch': raise ImportError('blocked')
sys.meta_path.insert(0,Block())
import vrs_hardware as h
s=h.snapshot('.', 'review')
assert s['allowed']>0 and s['ram_total']>0 and s['gpu'] is None
assert 'torch' not in sys.modules
'''
        subprocess.run([sys.executable,'-c',code],cwd=Path(h.__file__).parent,check=True)


if __name__=='__main__': unittest.main()

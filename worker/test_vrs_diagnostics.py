import json
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch, MagicMock

import vrs_diagnostics as d
import vrs_benchmark as b


class DiagnosticsTests(unittest.TestCase):
    def test_sampling_and_concurrent_phases(self):
        with d.Profiler(.01) as p:
            with ThreadPoolExecutor(max_workers=4) as pool:
                self.assertEqual(list(pool.map(lambda x:p.call('preparation',lambda: x*x),range(20))),[x*x for x in range(20)])
            p.call('inference',lambda: 42)
        r=p.report()
        self.assertEqual(r['phases']['preparation']['calls'],20)
        self.assertEqual(r['phases']['inference']['calls'],1)
        self.assertGreaterEqual(r['samples'],2)
        self.assertGreater(r['sampled_rss_max_bytes'],0)
        self.assertIsNone(r['sampled_cuda_allocated_max_bytes'])
        self.assertFalse(p.thread.is_alive())
        json.dumps(r,allow_nan=False)

    def test_failure_and_single_use(self):
        p=d.Profiler()
        with self.assertRaisesRegex(ValueError,'private fixture'):
            with p: p.call('inference',lambda: (_ for _ in ()).throw(ValueError('private fixture')))
        self.assertEqual(p.report()['status'],'FAILED')
        self.assertEqual(p.report()['phases']['inference']['errors'],1)
        self.assertNotIn('private fixture',json.dumps(p.report()))
        with self.assertRaises(ValueError):
            with p: pass
        for interval in (True,0,6,float('nan')):
            with self.assertRaises(ValueError): d.Profiler(interval)

    def test_cuda_allocator_sampling(self):
        t=MagicMock(); t.cuda.memory_allocated.return_value=10; t.cuda.memory_reserved.return_value=20
        with d.Profiler() as p:
            p.gpu_sample(t,0)
            t.cuda.memory_allocated.return_value=5; p.gpu_sample(t,0)
            t.cuda.memory_allocated.side_effect=RuntimeError('fixture'); p.gpu_sample(t,0)
        self.assertEqual(p.report()['sampled_cuda_allocated_max_bytes'],10)
        self.assertEqual(p.report()['sampled_cuda_reserved_max_bytes'],20)
        self.assertEqual(p.report()['sample_errors'],1)
        t.cuda.synchronize.assert_not_called(); t.cuda.reset_peak_memory_stats.assert_not_called()

    def test_windows_storage_mapping_and_unknown(self):
        with patch.object(d,'Path') as path,patch.object(d.shutil,'which',return_value='powershell.exe'),patch.object(d.subprocess,'run') as run:
            path.return_value.resolve.return_value.drive='C:'
            for value,expected in [('SSD',True),('HDD',False),('Unspecified',None),('SSD\nHDD',None)]:
                run.return_value.stdout=value
                self.assertIs(d.windows_storage('.'),expected)
            args,kw=run.call_args
            self.assertEqual(kw['timeout'],8); self.assertTrue(kw['check']); self.assertIn('UniqueId',args[0][-1]); self.assertNotIn('shell',kw)
            run.side_effect=subprocess.TimeoutExpired('fixture',8)
            self.assertIsNone(d.windows_storage('.'))
            path.return_value.resolve.return_value.drive='\\\\server\\share'
            self.assertIsNone(d.windows_storage('.'))

    def test_review_diagnostics_without_torch(self):
        code='''import sys
class Block:
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0]=='torch': raise ImportError('blocked')
sys.meta_path.insert(0,Block())
import vrs_diagnostics as d
r=d.diagnostic('.', 'review')
assert r['preflight']['status'] in ('NOT_MET','UNVERIFIED')
assert 'torch' not in sys.modules
'''
        subprocess.run([sys.executable,'-c',code],cwd=Path(d.__file__).parent,check=True)

    def test_unique_profiled_benchmark_parity(self):
        r=b.benchmark('cpu',1,8,unique=True,profile=True)
        self.assertTrue(r['exact_parity']); self.assertEqual(r['unique_region_hashes'],8)
        adaptive=next(x for x in r['runs'] if x['mode']=='adaptive')
        self.assertEqual(adaptive['operational']['cache']['hits'],0)
        for name in d.PHASES: self.assertGreater(adaptive['profile']['phases'][name]['calls'],0)
        self.assertEqual(adaptive['profile']['status'],'COMPLETED')
        self.assertGreater(adaptive['profile']['wall_seconds'],0)


if __name__=='__main__': unittest.main()

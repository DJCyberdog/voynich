import json
import unittest
import warnings
from unittest.mock import MagicMock, patch

import torch
import glyphs as g
import test_glyphs
import vrs_backends as b
import vrs_hardware as h


class BackendTests(unittest.TestCase):
    def test_rocm_identity_and_cuda_rejection(self):
        t=MagicMock(); t.version.hip='7.1'; t.cuda.is_available.return_value=True; t.cuda.device_count.return_value=2
        self.assertEqual(b.resolve(t,'rocm',1,'Linux'),(t.cuda,'cuda:1'))
        self.assertFalse(h.cuda_probe(t)['ok']); t.ones.assert_not_called()
        t.version.hip=None
        with self.assertRaises(h.ResourceBlocked): b.resolve(t,'rocm',0,'Linux')

    def test_xpu_and_invalid_index(self):
        t=MagicMock(); t.xpu.is_available.return_value=True; t.xpu.device_count.return_value=2
        self.assertEqual(b.resolve(t,'xpu',1,'Windows'),(t.xpu,'xpu:1'))
        with self.assertRaises(h.ResourceBlocked): b.resolve(t,'xpu',2,'Windows')
        with self.assertRaises(ValueError): b.resolve(t,'xpu',True,'Windows')
        t.xpu.is_available.return_value=False
        with self.assertRaises(h.ResourceBlocked): b.resolve(t,'xpu',0,'Linux')

    def test_directml_isolation(self):
        api=MagicMock(); api.device_count.return_value=1; api.device.return_value=torch.device('privateuseone:0')
        loader=MagicMock(return_value=api)
        self.assertEqual(b.resolve(torch,'directml',0,'Windows',loader),(api,torch.device('privateuseone:0')))
        loader.assert_called_once_with('torch_directml')
        with self.assertRaises(h.ResourceBlocked): b.resolve(torch,'directml',0,'Linux',loader)
        api.device.return_value=torch.device('cpu')
        with self.assertRaises(h.ResourceBlocked): b.resolve(torch,'directml',0,'Windows',loader)
        with self.assertRaisesRegex(h.ResourceBlocked,'probe-only'):
            b.qualify(None,None,None,None,None,None,backend='directml')

    def test_memory_fail_closed(self):
        api=MagicMock(); api.mem_get_info.return_value=(4*h.GIB,8*h.GIB)
        self.assertEqual(b.memory(api,2)['index'],2)
        for value in ((9,8),(-1,8),(True,8),(0,0)):
            api.mem_get_info.return_value=value
            with self.assertRaises(h.ResourceBlocked): b.memory(api,0)
        api.mem_get_info.side_effect=NotImplementedError()
        with self.assertRaises(h.ResourceBlocked): b.memory(api,0)

    def test_real_classifier_and_mismatch(self):
        p=torch.stack([torch.zeros(1024),torch.ones(1024)]); f=torch.full((1,1024),.125)
        self.assertEqual(b.exact_classify(torch,g.classify,f,p,'cpu'),[(0,.015625,.75)])
        classify=MagicMock(side_effect=[[(0,.015625,.75)],[(1,.015625,.75)]])
        with self.assertRaisesRegex(h.ResourceBlocked,'parity'): b.exact_classify(torch,classify,f,p,'cpu')
        def fallback(x,y):
            warnings.warn('Falling back to CPU'); return g.classify(x,y)
        with self.assertRaisesRegex(h.ResourceBlocked,'fallback'): b.exact_classify(torch,fallback,f,p,'cpu')

    def test_probe_result_and_native_status(self):
        api=MagicMock(); api.mem_get_info.return_value=(4*h.GIB,8*h.GIB)
        with patch.object(b,'resolve',return_value=(api,'cpu')):
            result=b.probe('xpu')
            self.assertEqual(result['status'],'PROBE_PASS'); self.assertEqual(result['native_acceptance'],'UNVERIFIED')
            self.assertTrue(result['qualification_available']); api.synchronize.assert_called_once_with(0)
            result=b.probe('directml')
            self.assertEqual(result['status'],'PROBE_PASS'); self.assertFalse(result['qualification_available'])
        # Actual CPU-only environment, explicitly not a native accelerator test.
        if not torch.version.hip:
            self.assertEqual(b.probe('rocm')['status'],'BLOCKED')

    def test_qualification_parity_and_pressure(self):
        f=test_glyphs.GlyphTests(); f.setUp(); self.addCleanup(f.doCleanups)
        out=f.root/'model'; g.train(f.manifest,f.a,f.b,f.alphabet,f.split,out,'cpu')
        args=(f.manifest,f.a,f.alphabet,out/'glyph_model.json',out/'glyph_report.json')
        old=g.predict(*args,f.root/'legacy-e.json','cpu')
        api=MagicMock(); api.mem_get_info.return_value=(6*h.GIB,8*h.GIB)
        info=dict(allowed=4,ram_total=16*h.GIB,ram_available=12*h.GIB,disk_free=100*h.GIB)
        previous=torch.get_num_threads()
        # Simulated transport/telemetry, actual image decode and CPU classifier.
        with patch.object(b,'resolve',return_value=(api,'cpu')),patch.object(h,'snapshot',return_value=info.copy()):
            for backend in ('rocm','xpu'):
                result=b.qualify(*args,f.root/f'{backend}.json',backend=backend,limits={'batch_items':1,'cpu_workers':1})
                self.assertEqual(result['rows'],old['rows']); self.assertEqual(result['excluded_regions'],old['excluded_regions'])
                self.assertEqual(result['environment']['device'],backend)
                self.assertEqual(result['operational']['native_acceptance'],'UNVERIFIED')
                self.assertEqual(result['operational']['batch'],1)
                self.assertEqual(torch.get_num_threads(),previous)
                self.assertEqual(json.loads((f.root/f'{backend}.json').read_text())['rows'],old['rows'])
            with self.assertRaisesRegex(ValueError,'Output already exists'):
                b.qualify(*args,f.root/'xpu.json',backend='xpu')
            with patch.object(b,'exact_classify',side_effect=[[(0,.015625,.75),(1,.015625,.75)],h.ResourceBlocked('fixture parity mismatch')]):
                with self.assertRaises(h.ResourceBlocked): b.qualify(*args,f.root/'bad.json',backend='xpu')
            self.assertFalse((f.root/'bad.json').exists())
            self.assertEqual(torch.get_num_threads(),previous)
            api.mem_get_info.return_value=(0,8*h.GIB)
            with self.assertRaises(h.ResourceBlocked): b.qualify(*args,f.root/'pressure.json',backend='rocm')
            self.assertFalse((f.root/'pressure.json').exists())


if __name__=='__main__': unittest.main()

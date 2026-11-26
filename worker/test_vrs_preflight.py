import tempfile
import unittest
from unittest.mock import patch
import vrs_preflight as p
import vrs_hardware as h


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.info = dict(machine='AMD64', system='Windows', physical=6, allowed=12,
                         ram_total=16*h.GIB, disk_free=60*h.GIB,
                         gpu=dict(ok=True, total=16*h.GIB))

    def run_check(self, profile='cuda', isa=True, ssd=True, os_ok=True, gui=False, screen=(1280,720)):
        with patch.object(h,'snapshot',return_value=self.info), patch.object(p,'avx2',return_value=isa), \
             patch.object(p,'storage_ssd',return_value=ssd), patch.object(p,'os_version',return_value=os_ok), \
             patch.object(p,'display',return_value=screen), patch.object(p,'dependencies',return_value={'x':{'status':'PASS'}}):
            return p.check('.',profile,gui=gui)

    def test_owner_mock_never_certified_by_probes_alone(self):
        r = self.run_check()
        self.assertEqual(r['status'],'UNVERIFIED')
        self.assertEqual(r['checks']['representative_throughput'],'UNKNOWN')

    def test_unknown_not_pass_and_known_failure(self):
        self.assertEqual(self.run_check(ssd=None)['checks']['ssd'],'UNKNOWN')
        for kwargs in ({'isa':False},{'ssd':False},{'os_ok':False}):
            self.assertEqual(self.run_check(**kwargs)['status'],'NOT_MET')

    def test_review_does_not_require_avx2_or_cuda(self):
        self.info['gpu']=None; self.info['ram_total']=8*h.GIB
        r=self.run_check('review',isa=False)
        self.assertEqual(r['checks']['avx2'],'NOT_APPLICABLE')
        self.assertEqual(r['checks']['base'],'PASS')
        self.assertEqual(self.run_check('review',screen=(800,600))['status'],'NOT_MET')

    def test_headless_and_display_unknown(self):
        self.assertEqual(self.run_check()['checks']['display'],'NOT_APPLICABLE')
        self.assertEqual(self.run_check(gui=True,screen=None)['checks']['display'],'UNKNOWN')

    def test_dependency_mismatch_missing(self):
        def version(name):
            if name=='psutil': raise p.md.PackageNotFoundError(name)
            return '0.0'
        with patch.object(p.md,'version',side_effect=version):
            r=p.dependencies('review')
        self.assertEqual(set(r),{'Pillow','psutil'})
        self.assertIsNone(r['psutil']['actual'])
        self.assertTrue(all(x['status']=='NOT_MET' for x in r.values()))

    def test_actual_cpu_features(self):
        self.assertIn(p.avx2('Linux'),(True,False,None))
        self.assertIsNone(p.storage_ssd('.', 'Windows'))
        self.assertIsNone(p.os_version('Other'))


if __name__=='__main__': unittest.main()

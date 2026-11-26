import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import vrs_backend_acceptance as a
import vrs_backends as b


class AcceptanceTests(unittest.TestCase):
    def test_blocked_probe_leaves_no_fixture(self):
        with tempfile.TemporaryDirectory() as d, patch.object(b,'probe',return_value={'status':'BLOCKED','qualification_available':False}):
            self.assertEqual(a.run('xpu',workspace=d)['status'],'BLOCKED')
            self.assertEqual(list(Path(d).iterdir()),[])

    def test_cpu_transport_cannot_pass_native(self):
        import glyphs as g
        def qualify(*args,**kwargs):
            result=g.predict(*args,'cpu'); result['environment']['probe']={'target':'cpu'}; return result
        with tempfile.TemporaryDirectory() as d, patch.object(b,'probe',return_value={'status':'PROBE_PASS','qualification_available':True}),patch.object(b,'qualify',side_effect=qualify):
            result=a.run('directml',workspace=d)
            self.assertEqual(result['status'],'BLOCKED'); self.assertIn('Native target identity',result['reason'])
            self.assertEqual(list(Path(d).iterdir()),[])


if __name__=='__main__': unittest.main()

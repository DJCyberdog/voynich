import unittest
from unittest.mock import patch
from vrs_ui_format import human,parse_gpu,review_fraction,gpu_telemetry

class UiFormatTests(unittest.TestCase):
    def test_human_preserves_denominators_and_status(self):
        text=human(dict(scientific_status='UNADJUDICATED',comparisons=[dict(compared=3,unresolved=0)],review=None))
        for x in ('UNADJUDICATED','compared:  3','unresolved:  0','review:  —'):self.assertIn(x,text)
        self.assertNotIn('{',text)
        self.assertEqual(review_fraction(dict(pending=3,resolved=4,deferred=2)),(4,9))
        self.assertIsNone(review_fraction(None))
        with self.assertRaises(ValueError):review_fraction(dict(pending=-1,resolved=4,deferred=2))

    def test_gpu_parser_denies_missing_or_invalid_telemetry(self):
        self.assertEqual(parse_gpu('0, 12, 512, 16384')[0],dict(index=0,util=12,used_mib=512,total_mib=16384))
        for x in ('','0, N/A, 0, 10','0, 110, 0, 10','0, 10, 11, 10','0, nan, 1, 10','0, 0, 1, 2\n0, 0, 1, 2'):
            with self.assertRaises(ValueError):parse_gpu(x)
        with patch('vrs_ui_format.Path.is_file',return_value=False):self.assertIsNone(gpu_telemetry())

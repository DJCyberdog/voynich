import gzip
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import vrs_hybrid_page as p


class HybridStorageTests(unittest.TestCase):
    def test_plain_and_gzip_roundtrip(self):
        obj=dict(payload=['native vector evidence']*5000,scientific_status='UNADJUDICATED')
        with tempfile.TemporaryDirectory() as tmp:
            a,b,c=(Path(tmp)/name for name in ('page.json','page.json.gz','another.json.gz'))
            for f in (a,b,c):
                p.write(f,obj);self.assertEqual(p.read(f),obj)
            self.assertEqual(b.read_bytes(),c.read_bytes())
            self.assertLess(b.stat().st_size,a.stat().st_size)
            with self.assertRaises(FileExistsError):p.write(b,obj)
    def test_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'page.json.gz';f.write_bytes(gzip.compress(b'x'*4096))
            with patch.object(p,'MAX_DECODED_BYTES',1024):
                with self.assertRaisesRegex(ValueError,'decoded page budget'):p.read(f)
                with self.assertRaisesRegex(ValueError,'decoded page budget'):p.write(Path(tmp)/'new.gz',{'x':'x'*4096})
            with patch.object(p,'MAX_BYTES',10):
                with self.assertRaisesRegex(ValueError,'stored page budget'):p.read(f)
                with self.assertRaisesRegex(ValueError,'stored page budget'):p.write(Path(tmp)/'new.gz',{'x':1})
    def test_ambiguous_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'page.gz'
            for raw in (b'{"a":1,"a":2}',b'{"a":NaN}'):
                f.write_bytes(gzip.compress(raw))
                with self.assertRaises(ValueError):p.read(f)
    def test_corrupt_gzip(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'page.gz';f.write_bytes(gzip.compress(b'{"a":1}')[:-5])
            with self.assertRaisesRegex(ValueError,'invalid hybrid gzip'):p.read(f)

if __name__=='__main__':unittest.main()

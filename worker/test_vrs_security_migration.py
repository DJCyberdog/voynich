import unittest
import vrs_audit_projection as audit
import vrs_rc2_migration as migration


class AuditTests(unittest.TestCase):
    def test_exact_projection(self):
        rows=[('Torch','2.13.0+cpu'),('Pillow','13.0.0'),('psutil','7.2.2'),('setuptools','84.1.0')]
        r=audit.project(rows);self.assertEqual(r['exact']['torch'],'2.13.0+cpu');self.assertEqual(r['advisory_versions']['torch'],'2.13.0');self.assertEqual(set(r['exact']),set(r['advisory_versions']));self.assertFalse(r['binary_audit'])
    def test_fail_closed(self):
        good=[('torch','2.13.0+cpu'),('pillow','13.0.0'),('setuptools','84.1.0')]
        for rows in [good+[('TORCH','2.13.0+cpu')],good+[('other','1+custom')],good+[('a\n','1')],[('torch','2.10.0+cpu'),good[1]],[good[0],('pillow','12.3.0'),good[2]],[good[0],good[1],('setuptools','78.1.0')]]:
            with self.assertRaises(ValueError):audit.project(rows)


class MigrationTests(unittest.TestCase):
    def fixture(self):
        names=['portable_sources.json','old.py','config/portable.json','config/install-cuda.json','config/bootstrap-origin.json','runtime/cuda/python.exe','.venv/cuda/python.exe','bootstrap/python.exe','cache/downloads/wheel','data/source.pdf','workspace/ledger','workspace/outbox','config/private.json','models/glyph.bin','user-note.txt']
        return dict(dirs=['config','runtime','runtime/cuda','.venv','.venv/cuda','bootstrap','cache','cache/downloads','data','workspace','models'],files={n:dict(bytes=10,sha256='a'*64) for n in names},bytes=len(names)*10)
    def test_partition(self):
        inv=self.fixture();s,c=migration.layout(inv,{'old.py','portable_sources.json'},{'new.py','portable_sources.json'},'cuda')
        self.assertEqual(set(s['files']),{'data/source.pdf','workspace/ledger','workspace/outbox','config/private.json','models/glyph.bin','user-note.txt'});self.assertEqual(s['bytes'],60);self.assertEqual(c['omitted_generated_files'],7);self.assertEqual(c['replaced_source_files'],2);self.assertEqual(len(inv['files']),15)
    def test_collisions_and_invalid_scope(self):
        inv=self.fixture();old={'old.py','portable_sources.json'}
        for new in [{'DATA/SOURCE.PDF'}, {'workspace'}, {'user-note.txt/sub.py'}, {'runtime/x.py'}]:
            with self.assertRaises(ValueError):migration.layout(inv,old,new,'cuda')
        with self.assertRaises(ValueError):migration.layout(inv,old,{'new.py'},'auto')
    def test_multiple_plan_or_pending_transaction(self):
        for name in ('config/install-cpu.json','workspace/source-update/journal.json','workspace/source-update/rc2-receipt.json'):
            inv=self.fixture();inv['files'][name]={'bytes':1,'sha256':'b'*64}
            with self.assertRaises(ValueError):migration.layout(inv,{'old.py','portable_sources.json'},{'new.py'},'cuda')

if __name__=='__main__':unittest.main()

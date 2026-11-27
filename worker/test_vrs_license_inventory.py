import tempfile,unittest,zipfile
from pathlib import Path
from vrs_prepare_plan import prepare
from vrs_portable import save,local
from vrs_license_inventory import inventory,member_inventory,clean,dependency_fields,unresolved_license_files
from email.parser import BytesParser

class LicenseInventory(unittest.TestCase):
    def fixture(self,root):
        w=root/'input';w.mkdir();rt=w/'runtime.zip'
        with zipfile.ZipFile(rt,'w') as z:
            z.writestr('python.exe',b'fixture')
            z.writestr('LICENSE.txt',b'runtime notice')
            z.writestr('Lib/ensurepip/_bundled/pip.whl',b'embedded fixture')
        for name,version in [('pillow','13.0.0'),('psutil','7.2.2')]:
            prefix=f'{name}-{version}.dist-info/'
            with zipfile.ZipFile(w/f'{name}-{version}-cp313-cp313-win_amd64.whl','w') as z:
                meta=f'Name: {name}\nVersion: {version}\n'
                if name=='pillow':meta+='License-Expression: MIT\nLicense-File: LICENSE.txt\n'
                z.writestr(prefix+'METADATA',meta)
                if name=='pillow':z.writestr(prefix+'licenses/LICENSE.txt','fixture notice')
        save(root/'portable_sources.json',dict(schema=1,files={}))
        return prepare(root,'review',rt,w)
    def test_report_and_missing_fields(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();p=self.fixture(root)
            r=inventory(root,'review',p['plan'],p['sha256'])
            self.assertFalse(r['redistribution_approved']);self.assertEqual(r['status'],'REVIEW_REQUIRED')
            self.assertEqual(len(r['wheels']),2)
            self.assertEqual(r['wheels'][0]['declared_license_expression'],['MIT'])
            self.assertTrue(r['wheels'][0]['notice_files'])
            self.assertEqual(r['wheels'][0]['unresolved_declared_license_files'],[])
            self.assertTrue(r['wheels'][1]['missing_declared_license'])
            self.assertTrue(r['wheels'][1]['missing_notice_files'])
            self.assertEqual(len(r['runtime']['embedded_wheels']),1)
            self.assertTrue(any(x['member']=='python.exe' for x in r['runtime']['native_components']))
            from vrs_license_inventory import cyclonedx
            bom=cyclonedx(r);self.assertEqual(bom['bomFormat'],'CycloneDX')
            self.assertTrue(any(x['name']=='Lib/ensurepip/_bundled/pip.whl' for x in bom['components'][0]['components']))
            self.assertEqual(r,inventory(root,'review',p['plan'],p['sha256']))
    def test_tampered_asset_and_approval(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();p=self.fixture(root)
            with self.assertRaises(ValueError):inventory(root,'review',p['plan'],'0'*64)
            r=inventory(root,'review',p['plan'],p['sha256']);x=r['wheels'][0]
            local(root,'cache/downloads/'+x['sha256']+'/'+x['file']).write_bytes(b'tampered')
            with self.assertRaises(ValueError):inventory(root,'review',p['plan'],p['sha256'])
    def test_member_collision_and_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.zip'
            for names in (('LICENSE','license'),('../LICENSE',)):
                with zipfile.ZipFile(p,'w') as z:
                    for n in names:z.writestr(n,b'x')
                with zipfile.ZipFile(p) as z:
                    with self.assertRaises(ValueError):member_inventory(z)

    def test_metadata_not_silently_truncated(self):
        value='package; extra == "'+('x'*600)+'"'
        message=BytesParser().parsebytes(('Requires-Dist: '+value+'\n').encode())
        self.assertEqual(dependency_fields(message),[value])
        with self.assertRaises(ValueError):clean('x'*4097)
        message=BytesParser().parsebytes(b'Requires-Dist: dep\n'*257)
        with self.assertRaisesRegex(ValueError,'Dependency metadata quota'):dependency_fields(message)

    def test_locked_candidate_archive(self):
        from vrs_build_portable import build_candidate
        import hashlib,json
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();p=self.fixture(root)
            (root/'README.md').write_bytes(b'synthetic source')
            data=(root/'README.md').read_bytes()
            save(root/'portable_sources.json',dict(schema=1,files={'README.md':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()}))
            (root/'private.txt').write_bytes(b'never bundle')
            output=build_candidate(root,'review',p['plan'],p['sha256'])
            with zipfile.ZipFile(output) as z:
                prefix='Voynich Research Studio/'
                self.assertNotIn(prefix+'private.txt',z.namelist())
                self.assertEqual(z.read(prefix+'bootstrap/python.exe'),b'fixture')
                metadata=json.loads(z.read(prefix+'CANDIDATE.json'));self.assertFalse(metadata['redistribution_approved']);self.assertFalse(metadata['release_approved'])
                from vrs_build_portable import RELEASE_VERSION
                self.assertEqual(metadata['version'],RELEASE_VERSION)
                self.assertEqual(metadata['source_manifest_sha256'],hashlib.sha256(z.read(prefix+'portable_sources.json')).hexdigest())
                self.assertEqual(json.loads(z.read(prefix+'SBOM.cdx.json'))['bomFormat'],'CycloneDX')
                self.assertFalse(json.loads(z.read(prefix+'COMPONENTS.json'))['redistribution_approved'])
                lock=json.loads(z.read(prefix+p['plan']))
                for asset in [lock['runtime'],*lock['wheels']]:
                    name=prefix+'cache/downloads/'+asset['sha256']+'/'+asset['file']
                    self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),asset['sha256'])
            with self.assertRaises(ValueError):build_candidate(root,'review',p['plan'],p['sha256'])

    def test_unresolved_license_file_declarations(self):
        rows=[dict(member='example-1.dist-info/licenses/LICENSE.txt')]
        self.assertEqual(unresolved_license_files('example-1.dist-info/METADATA',
            ['LICENSE.txt','MISSING.txt','../LICENSE.txt'],rows),['MISSING.txt','../LICENSE.txt'])

if __name__=='__main__':unittest.main()

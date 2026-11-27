"""RC2-01 controls; synthetic objects are never independent Voynich annotations."""
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import fitz
import numpy as np
from PIL import Image,ImageDraw
import regions
import vrs_surface as surface
import worker


class SurfaceTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.pdf=self.root/'source.pdf'
        self.make_pdf(self.pdf)
        self.sha=worker.sha(self.pdf)
        self.groups=self.root/'groups.json'
        worker.write(self.groups,{'1':'fixture-meta','2':'fixture-image'})
        for name,value in [('YALE_SHA256',self.sha),('YALE_PAGES',2)]:
            mock=patch.object(surface,name,value);mock.start();self.addCleanup(mock.stop)

    def make_pdf(self,path,overlay=False,extra_vector=False):
        image=Image.new('RGB',(100,100),'white');d=ImageDraw.Draw(image)
        # Retain sparse marks even at each image edge; not a font or glyph label.
        for x,y in [(0,0),(94,0),(0,94),(94,94),(45,45)]:
            d.rectangle((x,y,x+5,y+5),fill='black')
        stream=BytesIO();image.save(stream,format='JPEG',quality=98)
        with fitz.open() as doc:
            for n in (1,2):
                p=doc.new_page(width=200,height=200)
                p.insert_text((20,15),'Yale University Library',fontsize=9)
                p.insert_text((20,28),'Beinecke Rare Book and Manuscript Library',fontsize=7)
                if n==1:p.insert_text((20,60),'MODERN CATALOG ONLY',fontsize=10)
                else:
                    box=fitz.Rect(30,45,170,185)
                    p.insert_image(box,stream=stream.getvalue(),keep_proportion=False)
                    p.draw_rect(box,width=.57);p.draw_rect(box,width=.57)
                    if overlay:p.insert_text((50,80),'unresolved',fontsize=10)
                    if extra_vector:p.draw_line((60,70),(80,80))
                p.insert_text((65,197),f'Page {n} of 2',fontsize=8)
            doc.save(path)

    def test_exact_isolation_and_edge_coverage(self):
        with fitz.open(self.pdf) as doc:
            p1,m1=surface.isolate_page(doc[0],self.sha)
            self.assertEqual(m1['status'],'METADATA_ONLY')
            self.assertTrue(all(v==255 for v in p1.samples))
            p2,m2=surface.isolate_page(doc[1],self.sha)
            self.assertEqual(m2['status'],'IMAGE_ENVELOPE')
            self.assertEqual(m2['script_status'],'UNRESOLVED_WITHIN_IMAGE')
            self.assertEqual(m2['physical_mapping'],'UNVERIFIED')
            img=Image.frombytes('RGB',(p2.width,p2.height),p2.samples)
            a=np.asarray(img)
            x0,y0,x1,y1=m2['pixel_box']
            outside=a.copy();outside[y0:y1,x0:x1]=255
            self.assertTrue(np.all(outside==255))
            for x,y in [(x0+5,y0+5),(x1-6,y0+5),(x0+5,y1-6),(x1-6,y1-6)]:
                self.assertLess(int(a[y,x].mean()),100)
            windows=list(regions.screened_boxes(img,m2['pixel_box']))
            for scale in range(len(regions.SCALES)):
                boxes=[box for s,box,_ in windows if s==scale]
                self.assertEqual(min(b[0] for b in boxes),x0)
                self.assertEqual(min(b[1] for b in boxes),y0)
                self.assertEqual(max(b[2] for b in boxes),x1)
                self.assertEqual(max(b[3] for b in boxes),y1)

    def test_propose_audit_and_legacy_route(self):
        a=regions.audit_yale(self.pdf,self.sha)
        self.assertEqual(a['page_count'],2)
        self.assertEqual(a['pages'][0]['proposals'],0)
        self.assertGreater(a['pages'][1]['proposals'],0)
        out=self.root/'isolated'
        result=regions.propose(self.pdf,self.sha,self.groups,out,[1,2],isolate_yale=True)
        manifest=worker.read(out/'manifest.json')
        self.assertEqual(a['proposals'],result['proposals'])
        self.assertEqual(a['screened'],result['screened'])
        self.assertEqual(manifest['surface_policy'],surface.POLICY)
        self.assertEqual(set(manifest['surfaces']),{'1','2'})
        self.assertEqual({r['page'] for r in manifest['regions']},{2})
        for r in manifest['regions']:
            x0,y0,x1,y1=manifest['surfaces']['2']['pixel_box'];b=r['pixel_box']
            self.assertTrue(x0<=b[0]<b[2]<=x1 and y0<=b[1]<b[3]<=y1)
            self.assertEqual(worker.sha(out/r['file']),r['sha256'])
        legacy=self.root/'legacy'
        regions.propose(self.pdf,self.sha,self.groups,legacy,[1])
        m=worker.read(legacy/'manifest.json')
        self.assertNotIn('surface_policy',m)
        self.assertGreater(len(m['regions']),0)
        self.assertEqual(worker.sha(self.pdf),self.sha)

    def test_refuse_unknown_hash_and_ambiguous_geometry(self):
        with self.assertRaisesRegex(ValueError,'SHA256'):
            regions.audit_yale(self.pdf,'0'*64)
        for name,kwargs,reason in [('overlay',dict(overlay=True),'Text overlaps'),
                                   ('vector',dict(extra_vector=True),'Unclassified vector')]:
            p=self.root/(name+'.pdf');self.make_pdf(p,**kwargs);digest=worker.sha(p)
            with patch.object(surface,'YALE_SHA256',digest):
                with self.assertRaisesRegex(ValueError,reason):
                    regions.propose(p,digest,self.groups,self.root/name,[2],isolate_yale=True)
            self.assertFalse((self.root/name/'manifest.json').exists())

    def test_coordinator_uses_pinned_surface_policy(self):
        import vrs_coordinator as co
        from unittest.mock import Mock
        app=co.Coordinator(self.root)
        app._boundary=Mock();app._admit=Mock()
        attempt=self.root/'attempt';attempt.mkdir()
        manifest={'inputs':{'manuscript':co.ref(self.root,self.pdf),'groups':co.ref(self.root,self.groups)}}
        idx=app._regions('fixture',manifest,attempt)
        rows=list(app._page_manifests(idx))
        self.assertEqual([r[0]['page'] for r in rows],[1,2])
        self.assertEqual(rows[0][2]['surfaces']['1']['status'],'METADATA_ONLY')
        self.assertEqual(rows[1][2]['surface_policy'],surface.POLICY)
        self.assertGreater(rows[1][0]['regions'],0)


if __name__=='__main__':unittest.main()

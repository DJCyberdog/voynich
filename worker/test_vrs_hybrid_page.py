import copy
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import vrs_hybrid_page as p


def fixture():
    source=dict(path='source.pdf',sha256='a'*64)
    manifest=dict(source_sha256=source['sha256'],page_dimensions={'2':[20,20]},regions=[dict(id='r',pixel_box=[0,0,20,20])])
    proposals=[dict(id='r',status='unreviewed',boxes=[[1,1,4,4],[10,10,12,12]])]
    meta=dict(page=2,status='NATIVE_IMAGE',size=[20,20],rgb_sha256='b'*64,native_px_to_pt=[1,1,0,0])
    m=dict(components=[dict(box=[2,2,5,5]),dict(box=[15,15,18,18])],pairs=[dict(box=[2,2,18,18])])
    h=dict(grouping=dict(context=dict(source_sha256=source['sha256'],page=2,image_sha256=meta['rgb_sha256'],page_size=meta['size'],origin=[0,0]),masks={k:m for k in p.MASKS}),native_px_to_pt=meta['native_px_to_pt'],scientific_status='UNADJUDICATED',exclusion_authorized=False)
    return source,2,dict(path='manifest.json',sha256='c'*64),manifest,proposals,meta,h,lambda meta,b:b

class HybridPageTests(unittest.TestCase):
    def test_comparison_and_write(self):
        a=fixture();r=p.assemble(*a);self.assertEqual(r['comparison']['legacy'],2)
        self.assertEqual(r['comparison']['masks']['union'],dict(components=2,pairs=1,legacy_overlap=1,component_overlap=1,pair_overlap=1))
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/'page.json';p.write(f,r);s=json.loads(f.read_text());p.check(s,*a[:5],a[-1]);self.assertEqual(r,s)
            with self.assertRaises(FileExistsError):p.write(f,r)
    def test_tampering(self):
        a=fixture();r=p.assemble(*a);r['comparison']['mapped']=99;r.pop('id');r['id']=p.digest(r)
        with self.assertRaises(ValueError):p.check(r,*a[:5],a[-1])
        b=copy.deepcopy(a[:-1]);b[6]['grouping']['context']['page']=3
        with self.assertRaises(ValueError):p.assemble(*b,a[-1])
    def test_metadata(self):
        a=fixture();m=dict(source_sha256=a[0]['sha256'],page_dimensions={'1':[20,20]},regions=[])
        r=p.assemble(a[0],1,a[2],m,[],dict(page=1,status='METADATA_ONLY'),None,a[-1]);self.assertEqual(r['comparison']['legacy'],0)
    def test_coverage(self):
        boxes=[[0,0,2,2],[1,1,4,4]];s=p.coverage(boxes,[5,5]);self.assertEqual(s[-1,-1],12);self.assertFalse(p.intersects(s,[4,4,5,5]))
        with self.assertRaises(ValueError):p.coverage([[0,0,6,6]],[5,5])

if __name__=='__main__':unittest.main()

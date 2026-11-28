import unittest
import numpy as np
from PIL import Image, ImageDraw
import vrs_region_evidence as r

class RegionTests(unittest.TestCase):
    def test_material(self):
        im=Image.new('RGB',(80,60),(5,5,5));d=ImageDraw.Draw(im);d.rectangle((10,10,69,49),fill=(180,150,120));d.rectangle((25,20,30,35),fill=(5,5,5));before=im.tobytes();m=r.material_hypotheses(im)
        self.assertTrue(m['core'][25,27]);self.assertTrue(m['outside'][0,0]);self.assertTrue(np.all(m['core'].astype(int)+m['uncertain']+m['outside']==1));self.assertEqual(im.tobytes(),before)
    def test_dark_image(self):
        m=r.material_hypotheses(Image.new('RGB',(7,5)));self.assertTrue(m['outside'].all());self.assertFalse(m['core'].any())
    def test_zone(self):
        rows=[dict(id=i,box=[i*10,10,i*10+5,18],flags=['line_context_hint']) for i in range(1,5)];rows.append(dict(id=5,box=[51,10,52,11],flags=['tiny','line_context_hint']));z=r.script_zones(rows);self.assertEqual(len(z),1);self.assertEqual(z[0]['ids'],[1,2,3,4]);self.assertEqual(z[0]['script_status'],'UNRESOLVED')
    def test_record(self):
        im=Image.new('RGB',(10,10),(80,80,80));v=np.zeros((10,10),np.uint16);v[3,3]=1;before=v.copy();kw=dict(source_sha256='a'*64,page=1,origin=(10,20),image_size=(100,100));row=dict(id=1,box=[13,23,14,24],flags=['tiny']);a,m=r.region_record(im,v,6,[row],**kw);b,_=r.region_record(im,v,6,[row],**kw);self.assertEqual(a,b);self.assertFalse(a['exclusion_authorized']);np.testing.assert_array_equal(v,before);self.assertNotEqual(a['id'],r.region_record(im,v,6,[dict(row,flags=['elongated'])],**kw)[0]['id']);kw['page']=2;self.assertNotEqual(a['id'],r.region_record(im,v,6,[row],**kw)[0]['id'])
    def test_invalid(self):
        im=Image.new('RGB',(10,10));v=np.zeros((10,10),np.uint16);kw=dict(source_sha256='a'*64,page=1,origin=(10,20),image_size=(100,100));row=dict(id=1,box=[0,0,1,1],flags=[])
        with self.assertRaises(ValueError):r.region_record(im,v,6,[row],**kw)
        with self.assertRaises(ValueError):r.region_record(im,v+7,6,[],**kw)
        with self.assertRaises(ValueError):r.script_zones([row,row])
if __name__=='__main__':unittest.main()

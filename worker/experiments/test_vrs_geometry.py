import unittest
import numpy as np
from PIL import Image, ImageDraw
import vrs_geometry as g
import vrs_vectors as v

class GeometryTests(unittest.TestCase):
    def test_material(self):
        im=Image.new('RGB',(100,100),(5,5,5)); d=ImageDraw.Draw(im);d.rectangle((12,10,88,90),fill=(170,150,120));d.rectangle((30,30,35,60),fill=(20,20,20))
        masks,core,uncertain=g.leaf_hypotheses(im);self.assertEqual(len(masks),3);self.assertTrue(core[40,32]);self.assertFalse(core[0,0]);self.assertFalse((core&uncertain).any())
    def test_zones(self):
        rows=[dict(id=i,box=[10*i,10,10*i+5,18],flags=['line_context_hint']) for i in range(1,5)]; z=g.script_zones(rows); self.assertEqual(len(z),1); self.assertEqual(z[0]['script_status'],'UNRESOLVED');self.assertEqual(z[0]['ids'],[1,2,3,4])
    def test_identity(self):
        m=np.ones((4,5),bool);kw=dict(source_sha256='a'*64,page=2,page_rgb_sha256='b'*64,origin=(2,3),page_size=(100,100),px_to_pt=(.5,.5,1,1),method='test');r,e,c=g.vector_record(m,**kw);self.assertEqual(r['id'],g.vector_record(m,**kw)[0]['id']);self.assertIn('Q',c);self.assertEqual(r['exact_svg_sha256'],g.digest(e.encode()));kw['page']=3;self.assertNotEqual(r['id'],g.vector_record(m,**kw)[0]['id'])
    def test_medial(self):
        a=np.ones((15,15),bool);a[5:10,5:10]=False; s,d,f=g.medial(a);self.assertFalse((s&~a).any());self.assertEqual(v.euler8(a),v.euler8(s));self.assertEqual(d[0,0],2);self.assertEqual(d[7,7],0)
    def test_renderer(self):
        import cairosvg
        from io import BytesIO
        a=np.ones((12,12),bool);a[3:8,3:8]=False;a[0,0]=False
        for svg in (v.svg(v.contours(a),a.shape),g.curve_svg(v.contours(a),a.shape)):
            rgba=Image.open(BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('RGBA');np.testing.assert_array_equal(np.asarray(rgba)[:,:,3]>=128,a)
if __name__=='__main__':unittest.main()

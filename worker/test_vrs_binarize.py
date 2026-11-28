import unittest
import numpy as np
from PIL import Image, ImageDraw
import vrs_binarize as b


class BinarizeTests(unittest.TestCase):
    def test_stats_against_naive(self):
        a=np.arange(20,dtype=np.uint8).reshape(4,5); p=np.pad(a,1,mode='edge')
        m,s=b.stats(a,3)
        for y,x in np.ndindex(a.shape):
            self.assertAlmostEqual(m[y,x],p[y:y+3,x:x+3].mean())
            self.assertAlmostEqual(s[y,x],p[y:y+3,x:x+3].std())
    def test_uniform(self):
        for v in (0,100,255):
            a=np.full((8,9),v,np.uint8)
            self.assertFalse(b.otsu(a).any())
            for m in ('niblack','sauvola','wolf'):
                self.assertFalse(b.adaptive(a,15,.25,m).any())
    def test_otsu_two_tones(self):
        a=np.array([[5,5,250,250]],np.uint8)
        np.testing.assert_array_equal(b.otsu(a),[[True,True,False,False]])
    def test_synthetic_stroke(self):
        im=Image.new('RGB',(80,70),(210,190,155)); ImageDraw.Draw(im).line((20,20,20,50),fill=(45,35,25),width=3)
        before=im.tobytes(); masks=b.hypotheses(im)
        self.assertEqual(len(masks),37)
        for m in masks.values():
            self.assertEqual(m.shape,(70,80)); self.assertEqual(m.dtype,bool); self.assertTrue(m[30,20])
        self.assertEqual(im.tobytes(),before)
        self.assertFalse(b.agreement([masks[k] for k in b.ENSEMBLE])['union'][5,5])
    def test_agreement(self):
        a=np.array([[True,False,True,False]]); c=np.array([[True,True,False,False]])
        d=b.agreement([a,c]); np.testing.assert_array_equal(d['votes'],[[2,1,1,0]])
        np.testing.assert_array_equal(d['union'],[[True,True,True,False]])
        np.testing.assert_array_equal(d['majority'],[[True,False,False,False]])
        np.testing.assert_array_equal(d['uncertain'],[[False,True,True,False]])
    def test_bad_inputs(self):
        for a in ([],[np.ones((1,1))],[np.ones((1,1),bool),np.ones((2,1),bool)]):
            with self.assertRaises(ValueError): b.agreement(a)
        with self.assertRaises(ValueError): b.stats(np.zeros((2,2),np.uint8),4)
    def test_small_odd_tiles(self):
        a=np.arange(35,dtype=np.uint8).reshape(5,7)
        for tile in (2,3,32):
            c=b.clahe(a,tile); self.assertEqual(c.shape,a.shape); self.assertEqual(c.dtype,np.uint8)


if __name__ == '__main__': unittest.main()

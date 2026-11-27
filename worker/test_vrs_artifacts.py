import unittest
import numpy as np
from PIL import Image
import vrs_artifacts as a

class ArtifactTests(unittest.TestCase):
    def test_diagonal_and_bridge(self):
        m=np.array([[1,0,1,0],[0,1,0,0],[0,0,0,1]],bool)
        labels,n=a.component_labels(m)
        self.assertEqual(n,2); self.assertEqual(labels[0,0],labels[0,2]); self.assertNotEqual(labels[0,0],labels[2,3]); np.testing.assert_array_equal(labels>0,m)
    def test_blank(self):
        labels,rows=a.analyze(Image.new('RGB',(10,10)),np.zeros((10,10),np.uint16),6,origin=(0,0),page_size=(10,10))
        self.assertEqual(rows,[]); self.assertFalse(labels.any())
    def test_flags_preserve_pixels(self):
        im=Image.new('RGB',(100,80),(180,160,140)); votes=np.zeros((80,100),np.uint16)
        votes[5,5]=1; votes[20,10:50]=6; votes[40:45,10:15]=6; votes[40:45,25:30]=6; votes[40:45,40:45]=6; votes[60:72,60:72]=2
        before=im.tobytes(); original=votes.copy(); labels,rows=a.analyze(im,votes,6,origin=(0,0),page_size=(100,80))
        self.assertIn('tiny',rows[0]['flags']); self.assertIn('near_image_edge',rows[0]['flags']); self.assertIn('elongated',rows[1]['flags']); self.assertIn('line_context_hint',rows[2]['flags']); self.assertIn('broad_low_contrast',rows[-1]['flags']); self.assertIn('low_method_agreement',rows[-1]['flags']); self.assertTrue(all(r['script_status']=='UNRESOLVED' for r in rows)); self.assertEqual(im.tobytes(),before); np.testing.assert_array_equal(votes,original); np.testing.assert_array_equal(labels>0,votes>0); self.assertEqual(sum(r['area'] for r in rows),int((votes>0).sum()))
    def test_window_is_not_image_edge(self):
        v=np.zeros((20,20),np.uint16);v[0,0]=6
        _,rows=a.analyze(Image.new('RGB',(20,20)),v,6,origin=(100,200),page_size=(500,500))
        self.assertEqual(rows[0]['box'],[100,200,101,201]); self.assertIn('touches_window_edge',rows[0]['flags']); self.assertNotIn('near_image_edge',rows[0]['flags'])
    def test_invalid(self):
        im=Image.new('RGB',(3,3)); v=np.ones((3,3),np.uint16)
        for votes,n,o,p in [(v,0,(0,0),(3,3)),(v*7,6,(0,0),(3,3)),(v,6,(1,1),(3,3)),(v.astype(float),6,(0,0),(3,3))]:
            with self.assertRaises(ValueError): a.analyze(im,votes,n,origin=o,page_size=p)

if __name__=='__main__': unittest.main()

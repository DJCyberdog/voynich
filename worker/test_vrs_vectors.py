import unittest
import numpy as np
import vrs_vectors as v
from vrs_artifacts import component_labels

class VectorTests(unittest.TestCase):
    def check(self,a):
        before=a.copy(); loops=v.contours(a)
        np.testing.assert_array_equal(v.rasterize(loops,a.shape),a)
        s,f=v.skeleton(a); self.assertFalse((s&~a).any())
        self.assertEqual(component_labels(a)[1],component_labels(s)[1]); self.assertEqual(v.euler8(a),v.euler8(s))
        g=v.graph(s); points={tuple(n['point']) for n in g['nodes']}|{p for path in g['paths'] for p in path}
        self.assertEqual(points,{(int(x),int(y)) for y,x in zip(*np.nonzero(s))})
        edges=[tuple(sorted((p,q))) for path in g['paths'] for p,q in zip(path,path[1:])]
        self.assertEqual(len(edges),len(set(edges))); self.assertEqual(len(edges),g['edge_count'])
        np.testing.assert_array_equal(a,before)
    def test_exhaustive_3x3(self):
        for k in range(512): self.check(np.array([(k>>i)&1 for i in range(9)],bool).reshape(3,3))
    def test_ring(self):
        a=np.ones((9,9),bool); a[3:6,3:6]=False; self.check(a)
        self.assertEqual(len(v.contours(a)),2); self.assertEqual(v.euler8(a),0)
    def test_fallback(self):
        a=np.ones((2,2),bool); s,f=v.skeleton(a); self.assertEqual(f,[1]); np.testing.assert_array_equal(s,a)
    def test_cycle_and_isolated(self):
        a=np.zeros((8,8),bool);a[1,1:5]=a[4,1:5]=True;a[1:5,1]=a[1:5,4]=True;a[7,7]=True
        g=v.graph(a); self.assertEqual(g['edge_count'],12); self.assertEqual(len(g['paths']),1); self.assertEqual(g['paths'][0][0],g['paths'][0][-1]); self.assertIn(0,[n['degree'] for n in g['nodes']]);self.check(a)
    def test_random(self):
        rng=np.random.default_rng(42)
        for _ in range(80): self.check(rng.random((15,19))<rng.random())
    def test_svg(self):
        a=np.array([[True]]); s=v.svg(v.contours(a),a.shape,v.graph(a)); self.assertIn('fill-rule="evenodd"',s);self.assertIn('viewBox="0 0 1 1"',s);self.assertIn('cx="0.5"',s)
    def test_invalid(self):
        with self.assertRaises(ValueError): v.contours(np.ones((3,3)))
        with self.assertRaises(ValueError): v.rasterize([[(0,0),(1,1)]],(2,2))
if __name__=='__main__': unittest.main()

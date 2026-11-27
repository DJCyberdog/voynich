import unittest
import numpy as np
import vrs_reference_regions as r

class Tests(unittest.TestCase):
    def test_xml(self):
        b=b'<folio name="f5r" wordCount="2" width="100" height="100"><word index="0" x="10" y="20" width="30" height="40">x</word><word index="1" x="10" y="20" width="0" height="40">y</word></folio>'
        a=r.parse_words(b,r.digest(b),'f5r');self.assertEqual(a['rows'][0]['box'],[10,20,40,60]);self.assertEqual(a['rejected'],[1])
        for v,h,f in [(b,'0'*64,'f5r'),(b,r.digest(b),'f7r'),(b'<!DOCTYPE a><a/>',r.digest(b'<!DOCTYPE a><a/>'),'f5r')]:
            with self.assertRaises(ValueError):r.parse_words(v,h,f)
    def test_alignment(self):
        a=np.array([[0,0],[100,0],[0,100],[100,100]]);c=np.array([[10,10],[80,20],[20,80]]);t=lambda x:x*2+[10,20]
        z=r.fit_registration(a,t(a),c,t(c));self.assertEqual(z['geometry_status'],'CHECKED');np.testing.assert_allclose(z['matrix'],[[2,0,10],[0,2,20]],atol=1e-8)
        self.assertEqual(r.fit_registration(a,t(a),c,t(c)+10)['geometry_status'],'REJECTED')
        with self.assertRaises(ValueError):r.fit_registration(a,t(a),a[:3],t(a[:3]))
    def test_project(self):
        self.assertEqual(r.project([1,2,4,5],[[2,0,10],[0,2,20]],[100,100]),[12,24,18,30]);self.assertIsNone(r.project([1,2,4,5],[[2,0,-10],[0,2,20]],[100,100]))
    def test_unknown(self):
        z=dict(geometry_status='CHECKED');rows=[dict(id=1,kind='voynichese',box=[1,1,5,5]),dict(id=2,kind='other_handwriting',box=[4,4,8,8])]
        self.assertEqual(r.reference_evidence([3,3,6,6],rows,registration=z)['status'],'UNREGISTERED')
        self.assertEqual(r.reference_evidence([3,3,6,6],rows,registration=z,provenance_verified=True)['classes'],['other_handwriting','voynichese'])
        self.assertEqual(r.reference_evidence([10,10,12,12],rows,registration=z,provenance_verified=True)['status'],'UNRESOLVED')
if __name__=='__main__':unittest.main()

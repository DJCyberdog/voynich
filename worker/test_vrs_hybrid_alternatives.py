import unittest
from unittest.mock import patch
import numpy as np
import vrs_hybrid_alternatives as a


class AlternativesTests(unittest.TestCase):
    def test_split_conservation(self):
        m=np.zeros((7,13),bool);m[:,0:5]=True;m[:,8:]=True;m[3,5:8]=True
        r=dict(id='u',box=[100,200,113,207],area=int(m.sum()))
        opts=a.split_options(m,r);x=next(o for o in opts if o['axis']=='x')
        self.assertEqual(sum(p['area'] for p in x['parts']),r['area'])
        self.assertGreater(x['cut'],100);self.assertLess(x['cut'],113)
        self.assertEqual(a.split_options(np.ones((7,13),bool),r),[])
    def test_lineage_split_and_loss(self):
        p=np.array([[1,1,1,1,0,2]],np.int32);c=np.array([[1,0,0,2,0,0]],np.int32)
        pr=[dict(id='p',area=4),dict(id='q',area=1)];cr=[dict(id='a',area=1),dict(id='b',area=1)]
        r=a.lineage(p,c,pr,cr);self.assertEqual(len(r['links']),2);self.assertEqual(r['parents_without_child'],['q']);self.assertEqual(r['removed_pixels'],3)
        c[0,4]=2
        with self.assertRaises(ValueError):a.lineage(p,c,pr,cr)
    def test_compounds_and_budget(self):
        rows=[dict(id=str(i),box=[i*4,0,i*4+2,3]) for i in range(4)]
        pairs=[dict(members=[str(i),str(i+1)]) for i in range(3)]
        r=a.compounds(rows,pairs,lambda:None)
        self.assertEqual({tuple(x['members']) for x in r},{('0','1','2'),('1','2','3'),('0','1','2','3')})
        with patch.object(a,'MAX_EXPANSIONS',1):
            with self.assertRaises(ValueError):a.compounds(rows,pairs,lambda:None)
    def test_build_deterministic_empty_and_interrupt(self):
        lab=np.zeros((3,4),np.int32);outputs={k:dict(components=[],pairs=[],pixels=0) for k in a.MASKS};labels={k:lab for k in a.MASKS}
        r=a.build(outputs,labels,(0,0));self.assertEqual(r,a.build(outputs,labels,(0,0)));self.assertFalse(r['exclusion_authorized'])
        def stop():raise InterruptedError()
        with self.assertRaises(InterruptedError):a.build(outputs,labels,(0,0),stop)
    def test_invalid_envelope(self):
        lab=np.array([[1,1,0]],np.int32);rows=[dict(id='x',box=[0,0,1,1],area=2)];o={k:dict(components=rows,pairs=[],pixels=2) for k in a.MASKS};ls={k:lab for k in a.MASKS}
        with self.assertRaises(ValueError):a.build(o,ls,(0,0))

if __name__=='__main__':unittest.main()

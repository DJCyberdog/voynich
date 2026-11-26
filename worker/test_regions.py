import unittest
import regions as r
import worker as w
import test_worker as tw


class RegionTests(unittest.TestCase):
    def setUp(self):
        self.f=tw.WorkerTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.root=self.f.root

    def test_edge_coverage(self):
        for size,window in [(101,17),(100,100),(5,1)]:
            s=r.starts(size,window)
            self.assertEqual(s[0],0); self.assertEqual(s[-1]+window,size)
            self.assertEqual(set().union(*(set(range(x,x+window)) for x in s)),set(range(size)))

    def test_deterministic_proposals_and_budget(self):
        f=self.f; a=self.root/'a'; b=self.root/'b'
        x=r.propose(f.pdf,w.sha(f.pdf),f.groups,a,[1]); y=r.propose(f.pdf,w.sha(f.pdf),f.groups,b,[1])
        self.assertEqual(x,y); self.assertGreater(x['proposals'],0)
        self.assertEqual(w.sha(a/'manifest.json'),w.sha(b/'manifest.json'))
        w.dataset(a/'manifest.json')
        with self.assertRaisesRegex(ValueError,'budget exhausted'):
            r.propose(f.pdf,w.sha(f.pdf),f.groups,self.root/'limited',[1],1)
        self.assertFalse((self.root/'limited/manifest.json').exists())

    def test_matching_no_duplicate_credit(self):
        a=[0,0,.5,.5]; b=[.5,.5,1,1]
        self.assertEqual(r.matching([a,a,b],[a,b],.5),2)
        # First proposal can match either; second only the first. Requires reassignment.
        self.assertEqual(r.matching([[0,0,1,.5],a],[a,[.5,0,1,.5]],.5),2)

    def test_reference_checks_and_metrics(self):
        f=self.f; d=self.root/'proposal'; r.propose(f.pdf,w.sha(f.pdf),f.groups,d,[1])
        m=w.read(d/'manifest.json'); ref=self.root/'ref.json'
        data=dict(source_sha256=m['source_sha256'],groups_sha256=m['groups_sha256'],reviewer='synthetic',exhaustive=True,pages={'1':[m['regions'][0]['box']]})
        w.write(ref,data); out=self.root/'eval.json'; x=r.evaluate(d/'manifest.json',ref,out)
        self.assertEqual(x['metrics']['0.7']['proposal_recall'],1)
        self.assertEqual(x['metrics']['0.7']['matched'],1)
        self.assertEqual(x['scientific_status'],'UNADJUDICATED')
        data['exhaustive']=False; w.write(ref,data)
        with self.assertRaisesRegex(ValueError,'Exhaustive'): r.evaluate(d/'manifest.json',ref,self.root/'invalid.json')
        data['exhaustive']=True; data['pages']['2']=[]; w.write(ref,data)
        with self.assertRaisesRegex(ValueError,'exactly'): r.evaluate(d/'manifest.json',ref,self.root/'invalid.json')

if __name__=='__main__': unittest.main()

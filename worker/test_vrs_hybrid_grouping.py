import copy
import json
import unittest
import numpy as np
import vrs_hybrid_grouping as h

# Independent small test adapters for grouping logic only. Production adapters
# are qualified separately against the actual VRS vector engine.
def labels(m):
    out=np.zeros(m.shape,np.int32); n=0
    for y,x in zip(*np.nonzero(m)):
        if out[y,x]: continue
        n+=1; out[y,x]=n; todo=[(y,x)]
        while todo:
            a,b=todo.pop()
            for c in range(max(0,a-1),min(m.shape[0],a+2)):
                for d in range(max(0,b-1),min(m.shape[1],b+2)):
                    if m[c,d] and not out[c,d]: out[c,d]=n;todo.append((c,d))
    return out,n

def contours(m):
    return [[int(x),int(y)] for y,x in zip(*np.nonzero(m))]

def skeleton(m):
    return m.copy(), []

def graph(m):
    return dict(nodes=contours(m), paths=[])


def args():
    return dict(source_sha256='a'*64, image_sha256='b'*64,page=4,origin=(10,20),
                page_size=(100,100),labeler=labels,contourer=contours,
                skeletonizer=skeleton,grapher=graph)

class GroupingTests(unittest.TestCase):
    def test_group_alternatives_and_conservation(self):
        v=np.zeros((12,14),np.uint16);v[3:6,2:4]=6;v[3:6,6:8]=4;v[3,10]=1
        old=v.copy();r=h.build(v,6,**args());u=r['masks']['union'];m=r['masks']['majority'];i=r['masks']['intersection']
        self.assertEqual([u['pixels'],m['pixels'],i['pixels']],[13,12,6]);self.assertEqual([len(u['components']),len(m['components']),len(i['components'])],[3,2,1]);self.assertEqual(len(u['pairs']),2);self.assertEqual(u['components'][0]['box'],[12,23,14,26]);self.assertFalse(r['exclusion_authorized']);np.testing.assert_array_equal(v,old)
    def test_replay_and_identity(self):
        v=np.ones((5,5),np.uint16);r=h.build(v,6,**args());h.validate(json.loads(json.dumps(r)),v,6,**args());kw=args();kw['page']=5;self.assertNotEqual(r['id'],h.build(v,6,**kw)['id']);bad=copy.deepcopy(r);bad['masks']['union']['pixels']=0;bad.pop('id');bad['id']=h.digest(bad)
        with self.assertRaises(ValueError):h.validate(bad,v,6,**args())
    def test_empty_and_stop(self):
        r=h.build(np.zeros((2,2),np.uint16),6,**args());self.assertTrue(all(not v['components'] for v in r['masks'].values()))
        def stop():raise InterruptedError('stop')
        with self.assertRaises(InterruptedError):h.build(np.ones((2,2),np.uint16),6,**dict(args(),boundary=stop))
    def test_invalid(self):
        for v,n in [(np.ones((2,2),float),6),(np.ones((2,2),np.uint16)*7,6),(np.ones((2,2),np.uint16),0)]:
            with self.assertRaises(ValueError):h.build(v,n,**args())
        with self.assertRaises(ValueError):h.build(np.ones((2,2),np.uint16),6,**dict(args(),origin=(100,100)))

class NativeAdapterTests(unittest.TestCase):
    def test_native_engine(self):
        import importlib.util
        if any(importlib.util.find_spec(m) is None for m in ('vrs_binarize','vrs_artifacts','vrs_region_evidence','vrs_vectors')):
            self.skipTest('repository engine modules unavailable in isolated test folder')
        from PIL import Image, ImageDraw
        im=Image.new('RGB',(48,40),(210,190,150));d=ImageDraw.Draw(im);d.rectangle((8,8,12,25),fill=(35,25,15));d.rectangle((16,8,20,25),fill=(35,25,15))
        meta=dict(status='NATIVE_IMAGE',size=list(im.size),rgb_sha256=h.hash_bytes(im.tobytes()),page=2,native_px_to_pt=[.5,.5,10,20])
        r=h.analyze_native(im,source_sha256='a'*64,meta=meta);self.assertEqual(r,h.analyze_native(im,source_sha256='a'*64,meta=meta));self.assertFalse(r['exclusion_authorized']);self.assertTrue(r['grouping']['masks']['union']['components']);self.assertEqual(r['region']['votes_sha256'],r['grouping']['context']['votes_sha256'])
        with self.assertRaises(ValueError):h.analyze_native(im,source_sha256='a'*64,meta=dict(meta,rgb_sha256='0'*64))

if __name__=='__main__':unittest.main()

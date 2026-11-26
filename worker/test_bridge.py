import base64
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import bridge as b
import pipeline as p
import worker as w
import test_worker as tw


class FakeAPI:
    main = 'a'*40
    tip = 'b'*40
    def __init__(self):
        self.files = {}; self.refs = {}; self.prs = []; self.writes = []; self.fail_pr = False
    def blob(self, path, ref, missing=False):
        value = self.files.get((ref,path))
        if value is None and not missing: raise RuntimeError('Missing fixture')
        return value
    def call(self, method, path, data=None, missing=False):
        if method != 'GET': self.writes.append((method,path,data))
        if path == 'git/ref/heads/main': return {'object':{'sha':self.main}}
        if path.startswith('git/ref/heads/'):
            name=path.removeprefix('git/ref/heads/'); return {'object':{'sha':self.refs[name]}} if name in self.refs else None
        if path=='git/refs' and method=='POST':
            self.refs[data['ref'].removeprefix('refs/heads/')]=data['sha']; return {}
        if path.startswith('contents/') and method=='PUT':
            self.files[self.tip,path.removeprefix('contents/')]=base64.b64decode(data['content']); self.refs[data['branch']]=self.tip; return {}
        if path.startswith('compare/'):
            return {'ahead_by':1,'files':[{'filename':k[1],'status':'added'} for k in self.files if k[0]==self.tip]}
        if path.startswith('pulls?'): return self.prs
        if path=='pulls' and method=='POST':
            if self.fail_pr: self.fail_pr=False; raise RuntimeError('Simulated connection loss')
            pr={'number':12,'state':'open','head':{'sha':self.tip,'ref':data['head']},'base':{'ref':data['base']}}; self.prs.append(pr); return pr
        raise AssertionError((method,path))


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.f=tw.WorkerTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.root=self.f.root; self.api=FakeAPI()
        f=self.f
        self.job=dict(schema=1,id='train1',action='train',inputs={k:dict(path=str(v.relative_to(self.root)),sha256=w.sha(v)) for k,v in dict(manifest=f.manifest,left=f.a,right=f.b,split=f.split).items()},options=dict(device='cpu',epochs=2,batch=2))
        self.policy=dict(schema=1,allowed_inputs={v['path']:v['sha256'] for v in self.job['inputs'].values()},actions=['train'],publish=True)
        self.approve()
    def approve(self):
        raw=b.encoded(self.job); self.api.files[self.api.main,'worker/jobs/train1.json']=raw
        self.api.files[self.api.main,'worker/jobs/approved.json']=b.encoded(dict(schema=1,jobs=[dict(id='train1',sha256=b.digest(raw))]))
    def test_real_cpu_job_and_idempotent_pr(self):
        a=b.cycle(self.root,self.api,self.policy,True); self.assertEqual(a['processed'][0]['state'],'COMPLETED'); self.assertEqual(a['published'][0]['number'],12)
        self.assertEqual(len(self.api.writes),3); self.assertTrue(self.api.writes[0][2]['ref'].startswith('refs/heads/worker-results/'))
        report=json.loads(next(v for (ref,path),v in self.api.files.items() if ref==self.api.tip)); self.assertEqual(report['scientific_status'],'UNADJUDICATED')
        self.assertNotIn(str(self.root),json.dumps(report)); self.assertNotIn('rows',report['metrics'])
        self.assertEqual(b.cycle(self.root,self.api,self.policy,True)['processed'],[]); self.assertEqual(len(self.api.writes),3)
    def test_no_upload_without_both_flags(self):
        b.cycle(self.root,self.api,self.policy,False); self.assertEqual(self.api.writes,[])
        self.policy['publish']=False; b.cycle(self.root,self.api,self.policy,True); self.assertEqual(self.api.writes,[])
    def test_reject_hash_policy_and_reuse(self):
        self.api.files[self.api.main,'worker/jobs/train1.json']+=b' '
        with self.assertRaisesRegex(ValueError,'hash mismatch'): b.cycle(self.root,self.api,self.policy)
        self.approve(); self.policy['allowed_inputs']={}
        with self.assertRaisesRegex(ValueError,'not locally approved'): b.cycle(self.root,self.api,self.policy)
        self.policy['allowed_inputs']={v['path']:v['sha256'] for v in self.job['inputs'].values()}
        b.pull(self.root,self.api,self.policy,self.api.main); self.job['options']['epochs']=3; self.approve()
        with self.assertRaisesRegex(ValueError,'reused'): b.cycle(self.root,self.api,self.policy)
    def test_revoked_job_not_processed(self):
        b.pull(self.root,self.api,self.policy,self.api.main)
        del self.api.files[self.api.main,'worker/jobs/approved.json']
        self.assertEqual(b.cycle(self.root,self.api,self.policy,True)['processed'],[]); self.assertEqual(p.status(self.root)[0]['state'],'PENDING')
    def test_resume_publication_after_pr_failure(self):
        self.api.fail_pr=True
        with self.assertRaisesRegex(RuntimeError,'connection loss'): b.cycle(self.root,self.api,self.policy,True)
        self.assertEqual(b.cycle(self.root,self.api,self.policy,True)['published'][0]['number'],12)
        self.assertEqual([x[0] for x in self.api.writes],['POST','PUT','POST','POST'])
    def test_scope_and_aggregate_rejection(self):
        b.cycle(self.root,self.api,self.policy,False)
        original=b.safe_export(self.root,'train1')
        self.assertIn('counts',original['metrics'])
        with patch('pipeline.export',side_effect=lambda root,jid,out:w.write(out,{**original,'metrics':{'counts':{'secret':'bad'}}})):
            with self.assertRaisesRegex(ValueError,'aggregate counts'): b.safe_export(self.root,'train1')
        self.api.files[self.api.tip,'unrelated.txt']=b'bad'
        with self.assertRaisesRegex(ValueError,'PR scope'): b.cycle(self.root,self.api,self.policy,True)
        self.assertFalse(self.api.prs)
    def test_lock_and_redirect(self):
        (self.root/'bridge.lock').touch()
        with self.assertRaises(FileExistsError): b.cycle(self.root,self.api,self.policy)
        self.assertIsNone(b.NoRedirect().redirect_request(None,None,302,'',{},'https://example.org'))

if __name__=='__main__': unittest.main()

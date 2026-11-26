import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import vrs_contract as c
import vrs_repository as r
import vrs_collaboration as coll
import test_vrs_runtime as fixtures

BASE='1'*40; TIP='2'*40; TREE='3'*40; NEW_TREE='4'*40


def prof(name='owner/repo',ident=1,**kw):
    p=dict(schema=1,repository=name,repository_id=ident,visibility='private',base_branch='main',base_commit=BASE,credential_env='VRS_GITHUB_TOKEN_'+str(ident),publish=True,intake=False,head_profile=None); p.update(kw); return p


class Fake:
    def __init__(self,p):
        self.p=p; self.tip=None; self.raw=None; self.path=None; self.pr=None; self.writes=[]; self.fail_pr=False; self.visibility=p['visibility']; self.actual_base=BASE; self.parent=None
    def verify(self):
        if self.visibility!=self.p['visibility']: raise ValueError('Visibility changed')
        return dict(id=self.p['repository_id'],fork=self.parent is not None,parent={'id':self.parent})
    def base(self):
        if self.actual_base!=self.p['base_commit']: raise ValueError('Base changed')
        return self.actual_base
    def blob(self,path,commit,missing=False): return None if commit==BASE else self.raw
    def call(self,m,path,body=None,missing=False):
        if m!='GET': self.writes.append((m,path,body))
        if m=='GET' and path.startswith('git/ref/heads/'): return None if self.tip is None else {'object':{'sha':self.tip}}
        if path=='git/refs': self.tip=BASE; return {}
        if path=='git/commits/'+BASE: return {'tree':{'sha':TREE}}
        if path=='git/commits/'+TIP: return {'tree':{'sha':NEW_TREE}}
        if path=='git/trees/'+TREE+'?recursive=1': return dict(truncated=False,tree=[])
        if path=='git/trees/'+NEW_TREE+'?recursive=1': return dict(truncated=False,tree=[dict(path=self.path,type='blob',mode='100644',sha=hashlib.sha1(b'blob '+str(len(self.raw)).encode()+b'\0'+self.raw).hexdigest())])
        if path=='git/blobs':
            import base64
            self.raw=base64.b64decode(body['content']); return {'sha':hashlib.sha1(b'blob '+str(len(self.raw)).encode()+b'\0'+self.raw).hexdigest()}
        if path=='git/trees': self.path=body['tree'][0]['path']; return {'sha':NEW_TREE}
        if path=='git/commits': return {'sha':TIP}
        if m=='PATCH':
            assert body['force'] is False; self.tip=body['sha']; return {}
        if path=='commits/'+TIP: return {'sha':TIP,'parents':[{'sha':BASE}],'files':[{'filename':self.path,'status':'added'}]}
        if path.startswith('pulls?'): return [] if self.pr is None else [self.pr]
        if path=='pulls':
            if self.fail_pr: raise RuntimeError('Fixture PR failure')
            head=body['head'].split(':')[1]; self.pr=dict(number=7,state='open',head=dict(sha=TIP,ref=head,repo={'id':self.head_id if hasattr(self,'head_id') else self.p['repository_id']}),base=dict(ref='main',sha=BASE,repo={'id':self.p['repository_id']})); return self.pr
        if path=='pulls/7': return self.pr
        raise AssertionError((m,path))


class Integration(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.RuntimeTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups); self.root=self.f.root; self.run=self.f.run_to_review(); self.p=prof(); self.api=Fake(self.p)
        self.f.file('config/repositories.json',dict(schema=1,profiles={'primary':self.p})); self.pub=r.Publisher(self.root,lambda p:self.api)
    def test_automatic_route_and_retry(self):
        self.f.file('config/publication-routes.json',dict(schema=1,routes=[dict(profile='primary',runs='ALL_REPORTABLE')]))
        self.api.fail_pr=True; result=self.pub.sweep(); self.assertEqual(result[0]['state'],'PENDING'); self.assertEqual(self.api.tip,TIP)
        self.api.fail_pr=False; self.assertEqual(self.pub.sweep()[0]['state'],'SENT'); self.assertEqual(self.pub.sweep(),[])
        self.assertEqual(sum(x[1]=='git/commits' for x in self.api.writes),1); self.assertEqual(self.f.app.ledger.outbox()[0]['remote']['pr_number'],7)
        self.assertNotIn(b'local fixture',self.api.raw); self.assertNotIn(b'.pdf',self.api.raw); self.assertNotIn(b'candidate_id',self.api.raw)
    def test_consent_visibility_base_and_tamper(self):
        k=self.pub.enqueue(self.run,'primary'); self.api.visibility='public'; self.assertEqual(self.pub.sweep()[0]['state'],'PENDING'); self.assertEqual(self.api.writes,[])
        self.api.visibility='private'; self.api.actual_base='4'*40; self.assertEqual(self.pub.sweep()[0]['state'],'PENDING'); self.assertEqual(self.api.writes,[])
        self.api.actual_base=BASE; self.api.tip='5'*40
        # Unknown branch tip must not be overwritten. Fake raises runtime error for unexpected commit.
        old=self.api.call
        def call(m,p,*a,**kw):
            if p=='commits/'+'5'*40: raise RuntimeError('Collision')
            return old(m,p,*a,**kw)
        self.api.call=call; self.assertEqual(self.pub.sweep()[0]['state'],'PENDING'); self.assertEqual(self.api.writes,[])
        self.f.file('config/repositories.json',dict(schema=1,profiles={'primary':dict(self.p,publish=False)})); self.assertEqual(self.pub.sweep(),[])
        with self.assertRaises(ValueError): self.pub.enqueue(self.run,'primary')
    def test_two_repositories_fork_and_isolation(self):
        other=prof('owner/second',2); fork=prof('contributor/fork',3); self.p=dict(self.p,head_profile='fork'); apis={1:Fake(self.p),2:Fake(other),3:Fake(fork)}; apis[3].parent=1; apis[1].head_id=3
        self.f.file('config/repositories.json',dict(schema=1,profiles={'primary':self.p,'secondary':other,'fork':fork})); pub=r.Publisher(self.root,lambda p:apis[p['repository_id']]); pub.enqueue(self.run,'primary'); pub.enqueue(self.run,'secondary'); result=pub.sweep(); self.assertEqual([x['state'] for x in result],['SENT','SENT']); self.assertNotEqual(apis[2].raw,apis[3].raw); self.assertTrue(all(x[1]=='pulls' for x in apis[1].writes)); self.assertTrue(all(x[1]!='pulls' for x in apis[3].writes))
        self.f.file('config/repositories.json',dict(schema=1,profiles={'primary':self.p,'secondary':dict(other,credential_env=self.p['credential_env']),'fork':fork})); self.assertRaises(ValueError,r.profiles,self.root)
    def test_remote_tree_and_response_tamper(self):
        self.pub.enqueue(self.run,'primary'); self.api.fail_pr=True; self.pub.sweep(); self.api.fail_pr=False
        old=self.api.call
        def call(m,p,*a,**kw):
            v=old(m,p,*a,**kw)
            if p=='git/trees/'+NEW_TREE+'?recursive=1': v['tree'].append(dict(path='unrelated',mode='100644',type='blob',sha='a'*40))
            return v
        self.api.call=call; self.assertEqual(self.pub.sweep()[0]['state'],'PENDING'); self.assertIsNone(self.api.pr)
        self.api.call=old; self.api.raw+=b' '; self.assertEqual(self.pub.sweep()[0]['state'],'PENDING'); self.assertIsNone(self.api.pr)

    def test_actual_http_request_no_redirect_and_credential_slot(self):
        from unittest.mock import MagicMock
        from urllib.error import HTTPError
        other=prof('owner/second',2)
        with patch.dict(os.environ,{'VRS_GITHUB_TOKEN_1':'secret1','VRS_GITHUB_TOKEN_2':'secret2'}):
            a=r.API(self.p); b=r.API(other)
            for obj,token in [(a,'secret1'),(b,'secret2')]:
                opener=MagicMock(); obj.opener=opener; opener.open.return_value.__enter__.return_value.read.return_value=b'{}'; obj.call('GET')
                req=opener.open.call_args.args[0]; self.assertEqual(req.full_url,'https://api.github.com/repos/'+obj.p['repository']); self.assertEqual(req.get_header('Authorization'),'Bearer '+token)
                opener.open.side_effect=HTTPError(req.full_url,302,'redirect',{},None)
                with self.assertRaisesRegex(RuntimeError,'HTTP 302'): obj.call('GET')
            self.assertIsNone(r.NoRedirect().redirect_request(None,None,None,None,None,None))

    def test_intake_pinned_and_no_execution(self):
        self.api.p=dict(self.p,intake=True); manifest=self.f.file('approved-manifest.json',self.f.m); raw=c.canonical(dict(schema=1,capability='fixed-local-manuscript',manifest=manifest)); self.api.blob=lambda *a:raw
        approved=dict(repository_id=1,commit=BASE,job_id='job',job_sha256=hashlib.sha256(raw).hexdigest(),manifest=manifest)
        self.assertEqual(r.intake(self.root,self.api,'job',approved),self.f.m); self.assertEqual(len(self.f.app.ledger.registered()),1)
        for changed in [dict(approved,commit='4'*40),dict(approved,job_sha256='0'*64)]: self.assertRaises(ValueError,r.intake,self.root,self.api,'job',changed)
        self.assertRaises(ValueError,r.intake,self.root,self.api,'../job',approved)
        self.api.p=dict(self.p,intake=False); self.assertRaises(ValueError,r.intake,self.root,self.api,'job',approved)
    def test_private_blind_bundle_revisions_and_conflicts(self):
        item=self.f.app.review_items(self.run)['items'][0]; choice=dict(kind='false_positive',mappings={}); alternate=dict(kind='deferred',mappings={}); app=coll.Collaboration(self.root)
        p=dict(schema=1,private_export=True,reviewers={'a':'VRS_REVIEW_KEY_A','b':'VRS_REVIEW_KEY_B'},allowed_runs=[self.run]); self.f.file('config/collaboration.json',dict(p,private_export=False))
        with patch.dict(os.environ,{'VRS_REVIEW_KEY_A':'a'*40,'VRS_REVIEW_KEY_B':'b'*40}):
            self.assertRaises(ValueError,app.assign,self.run,item['id'],['a','b']); self.f.file('config/collaboration.json',p)
            a=app.assign(self.run,item['id'],['a','b']); self.assertEqual(a,app.assign(self.run,item['id'],['b','a'])); cohort=a['cohort']; bundles=[c.load(self.root/x) for x in a['assignments']]
            self.assertNotIn('run_id',bundles[0]['payload']); self.assertNotIn('candidate_id',bundles[0]['payload']); self.assertNotEqual(bundles[0]['payload']['assignment'],bundles[1]['payload']['assignment'])
            responses=[]
            for i,b in enumerate(bundles):
                with tempfile.TemporaryDirectory() as d:
                    remote=Path(d); coll.put(remote/'assignment.json',b); responses.append(coll.response(c.load(remote/'assignment.json'),choice,bytes('ab'[i]*40,'ascii')))
            bad=copy.deepcopy(responses[0]); bad['payload']['choice']=alternate; self.assertRaises(ValueError,app.receive,cohort,bad)
            self.assertEqual(app.receive(cohort,responses[0])['status'],'SEALED'); self.assertRaises(ValueError,app.adjudicate,cohort,'curator',choice); self.assertEqual(app.receive(cohort,responses[0])['received'],1)
            self.assertRaises(ValueError,app.receive,cohort,coll.response(bundles[0],alternate,b'a'*40))
            self.assertEqual(app.receive(cohort,responses[1])['replicas'],2); self.assertEqual(len(app.adjudicate(cohort,'curator')['reviews']),2); result=app.adjudicate(cohort,'curator',choice)
            self.assertEqual(self.f.app.review_items(self.run)['snapshot']['resolved'],0); self.f.app.submit(result['decision']); self.assertEqual(self.f.app.review_items(self.run)['snapshot']['resolved'],1); self.assertRaises(ValueError,app.adjudicate,cohort,'curator',choice)


def live_intake_fixture(root=None):
    # Contract-only deterministic input; never register it for computation.
    def ref_bytes(name,data):
        if root is not None:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as f:f.write(data)
        return dict(path=name,sha256=hashlib.sha256(data).hexdigest())
    inputs={role:ref_bytes('vrs116-intake/'+role+'.json',c.canonical(dict(synthetic=True,role=role))) for role in c.ROLES}
    trans=[ref_bytes('vrs116-intake/transcription.txt',b'SYNTHETIC INTAKE ONLY')]
    manifest=dict(schema=1,module=c.MODULE,protocol=c.PROTOCOL,inputs=inputs,transcriptions=trans,
                  backend='cpu',seed=116,run_nonce='0'*32)
    ref=ref_bytes('vrs116-intake/manifest.json',c.canonical(manifest))
    return manifest,ref,c.canonical(dict(schema=1,capability='fixed-local-manuscript',manifest=ref))


def seed_bytes():
    return live_intake_fixture()[2]


class IntakeSeedTests(unittest.TestCase):
    def test_deterministic_contract_only_seed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve()
            manifest,ref,payload=live_intake_fixture(root)
            self.assertEqual(payload,seed_bytes())
            self.assertEqual(c.load(c.artifact(root,ref)),manifest)
            c.manifest(root,manifest)


class LiveSandboxAcceptance(unittest.TestCase):
    def test_two_private_sandboxes(self):
        # Explicit local opt-in; never run against production or with ambient credentials.
        if os.environ.get('VRS116_ENABLE_LIVE_TEST')!='1':self.skipTest('Owner-authorized private VRS-116 sandbox configuration required')
        config=os.environ.get('VRS116_SANDBOX_CONFIG');self.assertTrue(config,'Sandbox config path required')
        path=Path(config).resolve(strict=True)
        raw=path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),os.environ.get('VRS116_APPROVE_SHA256'))
        f=fixtures.RuntimeTests();f.setUp();self.addCleanup(f.doCleanups)
        f.file('config/repositories.json',json.loads(raw))
        ps=r.profiles(f.root);self.assertEqual(len(ps),2)
        for p in ps.values():
            self.assertEqual(p['visibility'],'private');self.assertTrue(p['publish']);self.assertTrue(p['intake'])
            self.assertIsNone(p['head_profile'])
            self.assertNotEqual(p['repository'].casefold(),'djcyberdog/voynich')
        names=list(ps);tokens=[os.environ.get(ps[n]['credential_env']) for n in names]
        self.assertTrue(all(tokens) and tokens[0]!=tokens[1],'Two distinct credentials required')
        fixture,entry,seed=live_intake_fixture(f.root)
        for n in names:
            a=r.API(ps[n]);a.verify();base=a.base()
            approved=dict(repository_id=ps[n]['repository_id'],commit=base,job_id='vrs116-synthetic',job_sha256=hashlib.sha256(seed).hexdigest(),manifest=entry)
            self.assertEqual(r.intake(f.root,a,'vrs116-synthetic',approved),fixture)
            with self.assertRaises(ValueError):r.intake(f.root,a,'vrs116-synthetic',dict(approved,job_sha256='f'*64))
        self.assertEqual(f.app.ledger.registered(),[])
        for i,n in enumerate(names):
            with patch.dict(os.environ,{ps[n]['credential_env']:tokens[1-i]}):
                with self.assertRaisesRegex(RuntimeError,'GitHub HTTP (403|404)'):r.API(ps[n]).verify()
        import secrets
        run=f.run_to_review(dict(f.m,run_nonce=secrets.token_hex(16)))
        # Lose the first real PR acknowledgement, then reconcile by exact bytes/diff.
        class LostAck(r.API):
            lost=False
            def call(self,method,path='',body=None,missing=False):
                result=super().call(method,path,body,missing)
                if method=='POST' and path=='pulls' and not self.__class__.lost:
                    self.__class__.lost=True
                    raise RuntimeError('Synthetic acknowledgement loss after real PR creation')
                return result
        pub=r.Publisher(f.root,LostAck);receipts=[]
        for n in names:
            LostAck.lost=False
            key=pub.enqueue(run,n)
            first=pub.sweep();self.assertEqual(first[0]['state'],'PENDING');self.assertTrue(LostAck.lost)
            second=pub.sweep();self.assertEqual(second[0]['state'],'SENT')
            receipt=second[0]['receipt'];self.assertEqual(receipt['report_sha256'],key)
            self.assertEqual(receipt['repository'],ps[n]['repository'])
            a=r.API(ps[n]);pr=a.call('GET','pulls/'+str(receipt['pr_number']))
            self.assertTrue(pr['draft']);self.assertEqual(pr['state'],'open');a.base()
            self.assertEqual(pub.sweep(),[]);receipts.append(receipt)
        self.assertNotEqual(receipts[0]['report_sha256'],receipts[1]['report_sha256'])
        f.file('config/repositories.json',dict(schema=1,profiles={n:dict(p,publish=False,intake=False) for n,p in ps.items()}))
        for n in names:
            with self.assertRaises(ValueError):pub.enqueue(run,n)
        print(json.dumps(dict(scope='SYNTHETIC_SANDBOX_ONLY',receipts=receipts),sort_keys=True))


if __name__=='__main__': unittest.main()

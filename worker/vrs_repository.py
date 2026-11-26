"""VRS-110–113: explicit local repository trust and aggregate-only transport."""
import argparse
import base64
import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError

import vrs_contract as c
from vrs_core import require
from vrs_ledger import Ledger
from vrs_coordinator import scheduler_lock, inside

VERSION = '0.11.0'
PROFILE_FIELDS = ('schema','repository','repository_id','visibility','base_branch','base_commit','credential_env','publish','intake','head_profile')
SAFE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}')
ENV = re.compile(r'VRS_GITHUB_TOKEN_[A-Z0-9_]{1,64}')
PREFIX = 'vrs-evidence/'


def profile(value):
    c.fields(value,PROFILE_FIELDS)
    require(type(value['schema']) is int and value['schema']==1,'Invalid profile schema')
    require(type(value['repository']) is str and c.REPO.fullmatch(value['repository']) and value['repository'].split('/')[1] not in ('.','..'),'Invalid repository')
    c.number(value['repository_id']); require(value['repository_id']>0,'Missing repository ID')
    require(value['visibility'] in ('public','private','internal'),'Invalid visibility')
    require(type(value['base_branch']) is str and SAFE.fullmatch(value['base_branch']),'Invalid base branch')
    c.digest_ok(value['base_commit'],c.GIT)
    require(type(value['credential_env']) is str and ENV.fullmatch(value['credential_env']),'Invalid credential slot')
    require(type(value['publish']) is bool and type(value['intake']) is bool,'Consent must be explicit')
    require(value['head_profile'] is None or (type(value['head_profile']) is str and SAFE.fullmatch(value['head_profile'])),'Invalid fork profile')
    return value


def profiles(root):
    path=inside(Path(root).resolve(strict=True),'config/repositories.json')
    require(path.is_file() and not path.is_symlink() and not path.parent.is_symlink(),'Local repository profiles required')
    value=c.load(path); c.fields(value,('schema','profiles'))
    require(type(value['schema']) is int and value['schema']==1 and type(value['profiles']) is dict and 0<len(value['profiles'])<=32,'Invalid profiles')
    for k,p in value['profiles'].items():
        require(SAFE.fullmatch(k),'Invalid profile name'); profile(p)
    ps=list(value['profiles'].values())
    for key in ('repository_id','credential_env'):
        require(len({p[key] for p in ps})==len(ps),'Profiles must isolate identities and credentials')
    require(len({p['repository'].casefold() for p in ps})==len(ps),'Duplicate repository')
    for k,p in value['profiles'].items():
        if p['head_profile'] is not None:
            require(p['head_profile'] in value['profiles'] and p['head_profile']!=k,'Unknown fork profile')
            h=value['profiles'][p['head_profile']]
            require(h['head_profile'] is None and h['visibility']==p['visibility'] and h['base_commit']==p['base_commit'],'Fork profile mismatch')
    return value['profiles']


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None


class API:
    def __init__(self,p):
        self.p=profile(p); self.token=os.environ.get(p['credential_env'],'')
        require(self.token and not any(x.isspace() for x in self.token),'Configured credential unavailable')
        self.opener=build_opener(NoRedirect())

    def call(self,method,path='',body=None,missing=False):
        # Paths are built from validated names/digests by the fixed operations below.
        req=Request('https://api.github.com/repos/'+self.p['repository']+('/'+path if path else ''),method=method,
                    data=None if body is None else c.canonical(body),headers={'Authorization':'Bearer '+self.token,'Accept':'application/vnd.github+json','User-Agent':'VRS/0.11.0','X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json'})
        try:
            with self.opener.open(req,timeout=30) as res:
                raw=res.read(4_000_001); require(len(raw)<=4_000_000,'GitHub response limit'); return json.loads(raw)
        except HTTPError as exc:
            if missing and exc.code==404: return None
            raise RuntimeError('GitHub HTTP '+str(exc.code)) from None

    def verify(self):
        r=self.call('GET'); p=self.p
        require(r['id']==p['repository_id'] and r['full_name'].casefold()==p['repository'].casefold() and r['visibility']==p['visibility'],'Repository identity/visibility changed')
        return r

    def base(self):
        ref=self.call('GET','git/ref/heads/'+quote(self.p['base_branch'],safe=''))
        require(ref['object']['sha']==self.p['base_commit'],'Base commit changed; reauthorize locally')
        return self.p['base_commit']

    def blob(self,path,commit,missing=False):
        c.digest_ok(commit,c.GIT)
        v=self.call('GET','contents/'+quote(path,safe='/')+'?'+urlencode({'ref':commit}),missing=missing)
        if v is None: return None
        require(v['type']=='file' and v['encoding']=='base64' and type(v['size']) is int and 0<=v['size']<=c.MAX_JSON,'Invalid remote blob')
        raw=base64.b64decode(''.join(v['content'].split()),validate=True)
        require(len(raw)==v['size'],'Blob length mismatch'); return raw


def intake(root,api,job_id,approved):
    """Optional manual retrieval only: returns already approved local manifest; never executes."""
    require(api.p['intake'] is True and SAFE.fullmatch(job_id),'Intake disabled or invalid ID')
    api.verify(); commit=api.base()
    c.fields(approved,('repository_id','commit','job_id','job_sha256','manifest'))
    require(approved['repository_id']==api.p['repository_id'] and approved['commit']==commit and approved['job_id']==job_id,'Stale or unapproved job')
    raw=api.blob('worker/jobs/'+job_id+'.json',commit)
    require(hashlib.sha256(raw).hexdigest()==approved['job_sha256'],'Job digest mismatch')
    expected=dict(schema=1,capability='fixed-local-manuscript',manifest=approved['manifest'])
    require(raw==c.canonical(expected),'Unexpected remote capability or payload')
    manifest=c.load(c.artifact(root,approved['manifest'])); c.manifest(root,manifest)
    return manifest


def report_bytes(report,key,p):
    # Never accept generic export JSON, even if a local outbox row was edited.
    c.fields(report,('schema','module','protocol','app_version','run_id','repository','research_commit','worker_sha256','backend','seed','source_sha256','transcription_sha256','stages','classification','review','technical_status','scientific_status'))
    require(c.digest(report)==key and report['repository']==p['repository'] and report['research_commit']==p['base_commit'],'Report binding mismatch')
    require(report['schema']==1 and report['module']==c.MODULE and report['protocol']==c.PROTOCOL and report['app_version']==c.VERSION and report['scientific_status']=='UNADJUDICATED','Invalid report scope')
    for k in ('run_id','worker_sha256'): c.digest_ok(report[k])
    require(report['backend'] in ('cpu','cuda') and report['technical_status'] in ('COMPLETED','FAILED','PARTIAL'),'Invalid report status')
    c.number(report['seed'],2**32-1); c.fields(report['source_sha256'],c.ROLES)
    require(type(report['transcription_sha256']) is list and 1<=len(report['transcription_sha256'])<=12,'Invalid transcript hashes')
    for h in [*report['source_sha256'].values(),*report['transcription_sha256']]: c.digest_ok(h)
    c.fields(report['stages'],c.STAGES)
    for r in report['stages'].values():
        c.fields(r,('state','reason','receipt_sha256','artifact_sha256')); require(r['state'] in c.STATES and r['reason'] in c.REASONS,'Invalid stage'); c.digest_ok(r['receipt_sha256'])
        if r['artifact_sha256'] is not None: c.digest_ok(r['artifact_sha256'])
    for name,keys in [('classification',('total','accepted','abstained','failed')),('review',('resolved','pending','deferred'))]:
        row=report[name]
        if row is not None:
            c.fields(row,keys)
            for v in row.values(): c.number(v)
    return c.canonical(report)


def publish(target,head,report,key,gate=lambda:None):
    p=target.p; hp=head.p
    require(p['publish'] is True and hp['publish'] is True,'Publication disabled')
    raw=report_bytes(report,key,p); tr=target.verify(); hr=head.verify(); base=target.base()
    if head is not target:
        require(hr.get('fork') is True and hr.get('parent',{}).get('id')==tr['id'] and hp['visibility']==p['visibility'],'Unapproved fork relationship')
        require(head.base()==base,'Fork base mismatch')
    branch=PREFIX+key; path='worker/evidence/vrs/'+key+'.json'
    refpath='git/ref/heads/'+quote(branch,safe='/')
    existing=head.call('GET',refpath,missing=True)
    if existing is None:
        gate(); head.call('POST','git/refs',dict(ref='refs/heads/'+branch,sha=base)); existing=head.call('GET',refpath)
    tip=existing['object']['sha']; c.digest_ok(tip,c.GIT)
    if tip==base:
        require(head.blob(path,base,missing=True) is None,'Evidence path exists in base')
        parent=head.call('GET','git/commits/'+base); tree=parent['tree']['sha']; c.digest_ok(tree,c.GIT)
        gate(); blob=head.call('POST','git/blobs',dict(content=base64.b64encode(raw).decode('ascii'),encoding='base64'))['sha']; c.digest_ok(blob,c.GIT)
        require(blob==hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),'Git blob identity mismatch')
        gate(); tree=head.call('POST','git/trees',dict(base_tree=tree,tree=[dict(path=path,mode='100644',type='blob',sha=blob)]))['sha']; c.digest_ok(tree,c.GIT)
        gate(); tip=head.call('POST','git/commits',dict(message='VRS aggregate '+key,tree=tree,parents=[base]))['sha']; c.digest_ok(tip,c.GIT)
        # Non-forced ref update rejects unrelated concurrent commits.
        require(head.call('GET',refpath)['object']['sha']==base,'Evidence branch moved')
        gate(); head.call('PATCH','git/refs/heads/'+quote(branch,safe='/'),dict(sha=tip,force=False))
    def verify_tip():
        require(head.call('GET',refpath)['object']['sha']==tip,'Evidence branch moved')
        commit=head.call('GET','commits/'+tip)
        require(commit['sha']==tip and [x['sha'] for x in commit['parents']]==[base],'Branch collision or extra commits')
        files=commit['files']; require(len(files)==1 and files[0]['filename']==path and files[0]['status']=='added','Unexpected evidence diff')
        def entries(commit_id):
            value=head.call('GET','git/trees/'+commit_id+'?recursive=1')
            require(value.get('truncated') is False and type(value['tree']) is list,'Incomplete remote tree')
            out={}
            for e in value['tree']:
                require(e['path'] not in out,'Duplicate remote tree path')
                if e['type']!='tree': out[e['path']]=(e['mode'],e['type'],e['sha'])
            return out
        parent=head.call('GET','git/commits/'+base); child=head.call('GET','git/commits/'+tip)
        old=entries(parent['tree']['sha']); new=entries(child['tree']['sha'])
        expected=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        require(path not in old and new.pop(path,None)==('100644','blob',expected) and old==new,'Remote tree delta mismatch')
        require(head.blob(path,tip)==raw,'Remote bytes mismatch')
    verify_tip(); target.verify(); target.base()
    owner=hp['repository'].split('/')[0]; selector=owner+':'+branch
    query='pulls?'+urlencode(dict(state='all',head=selector,base=p['base_branch'],per_page=100))
    found=target.call('GET',query); require(type(found) is list and len(found)<100,'Ambiguous PR search')
    if not found:
        gate(); pr=target.call('POST','pulls',dict(title='VRS aggregate '+key[:12],body='Aggregate evidence only. Scientific status: UNADJUDICATED.',head=selector,base=p['base_branch'],draft=True))
    else:
        require(len(found)==1,'Ambiguous evidence PR'); pr=found[0]
    c.number(pr['number']); require(pr['number']>0,'Invalid PR number')
    pr=target.call('GET','pulls/'+str(pr['number']))
    require(pr['state']=='open' and pr['head']['sha']==tip and pr['head']['ref']==branch and pr['head']['repo']['id']==hp['repository_id'] and pr['base']['repo']['id']==p['repository_id'] and pr['base']['ref']==p['base_branch'] and pr['base']['sha']==base,'PR binding mismatch')
    verify_tip(); gate(); target.base()
    return dict(report_sha256=key,repository=p['repository'],pr_number=pr['number'],commit_sha=tip)


class Publisher:
    def __init__(self,root,factory=API):
        self.root=Path(root).resolve(strict=True); self.factory=factory
        self.home=inside(self.root,'workspace/vrs095'); db=inside(self.root,'workspace/vrs095/ledger.sqlite'); require(db.is_file(),'Existing local ledger required'); self.ledger=Ledger(self.root,db)

    def enqueue(self,run,name):
        p=profiles(self.root)[name]; require(p['publish'],'Publication disabled')
        return self.ledger.enqueue(run,p['repository'],p['base_commit'],[p['repository']],publish=True)

    def auto_enqueue(self,ps):
        path=inside(self.root,'config/publication-routes.json')
        if not path.exists(): return []
        require(not path.is_symlink(),'Unsafe routes path'); data=c.load(path); c.fields(data,('schema','routes'))
        require(type(data['schema']) is int and data['schema']==1 and type(data['routes']) is list and len(data['routes'])<=32,'Invalid routes')
        checked=[]
        for route in data['routes']:
            c.fields(route,('profile','runs')); name=route['profile']; require(name in ps and ps[name]['publish'],'Route not authorized')
            runs=route['runs']; require(runs=='ALL_REPORTABLE' or (type(runs) is list and len(runs)<=10000),'Invalid route scopes')
            if type(runs) is list:
                for run in runs: c.digest_ok(run)
            checked.append((name,runs))
        with self.ledger._tx() as conn:
            ready=[r['id'] for r in conn.execute("SELECT id FROM runs WHERE token IS NULL AND control IN ('BLOCKED','FAILED','COMPLETED')")]
        results=[]
        for name,runs in checked:
            for run in ready:
                if runs!='ALL_REPORTABLE' and run not in runs: continue
                try: results.append(self.enqueue(run,name))
                except (ValueError,OSError,KeyError): continue
        return results

    def sweep(self):
        results=[]
        with scheduler_lock(self.home/'publisher.lock'):
            self.auto_enqueue(profiles(self.root))
            for row in self.ledger.outbox():
                if row['state']!='PENDING': continue
                ps=profiles(self.root); matches=[p for p in ps.values() if p['repository']==row['repository'] and p['publish']]
                if len(matches)!=1: continue
                p=matches[0]; key=row['id']; token=None
                try:
                    token,report=self.ledger.claim_report(key,[p['repository']],publish=True)
                    # Regenerate the exact report from verified local receipts before transport.
                    with self.ledger._tx() as conn:
                        q=self.ledger._row(conn,'outbox',key); run=self.ledger._row(conn,'runs',q['run_id']); m,rs,_=self.ledger._validate(run)
                        c.verify_evidence(report,self.root,m,rs,p['repository'],p['base_commit'],[p['repository']],run['backend'],run['worker'])
                    a=self.factory(p); h=a if p['head_profile'] is None else self.factory(ps[p['head_profile']])
                    configured=[os.environ.get(x['credential_env']) for x in ps.values()]; configured=[x for x in configured if x]
                    require(len(set(configured))==len(configured),'Repository credentials not isolated')
                    def gate():
                        require(profiles(self.root)==ps,'Repository consent changed')
                        a.verify(); a.base()
                        if h is not a: h.verify(); h.base()
                    gate()
                    remote=publish(a,h,report,key,gate); self.ledger.finish_report(key,token,remote); token=None
                    results.append(dict(id=key,state='SENT',receipt=remote))
                except (ValueError,RuntimeError,OSError,KeyError,TypeError) as exc:
                    if token is not None: self.ledger.finish_report(key,token)
                    results.append(dict(id=key,state='PENDING',error=type(exc).__name__))
        return results

    def recover(self,key,generation,confirmed):
        with scheduler_lock(self.home/'publisher.lock'):
            self.ledger.recover_report(key,generation,publisher_confirmed_stopped=confirmed)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('root',type=Path); sub=p.add_subparsers(dest='action',required=True)
    q=sub.add_parser('check'); q.add_argument('profile'); q=sub.add_parser('enqueue'); q.add_argument('run'); q.add_argument('profile')
    q=sub.add_parser('intake'); q.add_argument('profile'); q.add_argument('job'); q.add_argument('approval',type=Path)
    sub.add_parser('once'); q=sub.add_parser('watch'); q.add_argument('--interval',type=int,default=60)
    q=sub.add_parser('recover'); q.add_argument('key'); q.add_argument('generation',type=int); q.add_argument('--confirm-stopped',action='store_true')
    a=p.parse_args()
    try:
        if a.action=='check':
            api=API(profiles(a.root)[a.profile]); api.verify(); result=dict(status='READ_PASS',commit=api.base())
        elif a.action=='intake':
            from vrs_coordinator import inside
            root=a.root.resolve(strict=True); approval=c.load(inside(root,a.approval)); api=API(profiles(root)[a.profile]); result=intake(root,api,a.job,approval)
        else:
            pub=Publisher(a.root)
            if a.action=='enqueue': result=dict(id=pub.enqueue(a.run,a.profile))
            elif a.action=='recover': pub.recover(a.key,a.generation,a.confirm_stopped); result=dict(status='RECOVERED')
            elif a.action=='once': result=pub.sweep()
            else:
                require(30<=a.interval<=3600,'Invalid interval')
                while True:
                    print(json.dumps(pub.sweep()),flush=True); time.sleep(a.interval)
        print(json.dumps(result,indent=2)); return 0
    except KeyboardInterrupt: return 130
    except (ValueError,RuntimeError,OSError,KeyError,TypeError) as exc:
        print(json.dumps(dict(status='BLOCKED',error=type(exc).__name__))); return 1


if __name__=='__main__': raise SystemExit(main())

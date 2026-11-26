"""VRS-114/115: explicit private offline assignments; no automatic adjudication."""
import argparse
import base64
import hashlib
import hmac
import io
import json
import os
import secrets
from pathlib import Path

import vrs_contract as c
from vrs_core import require
from vrs_desktop_api import Desktop,safe
from vrs_coordinator import scheduler_lock
from vrs_repository import SAFE


def key(slot):
    require(type(slot) is str and slot.startswith('VRS_REVIEW_KEY_') and SAFE.fullmatch(slot),'Invalid reviewer key slot')
    value=os.environ.get(slot,''); require(len(value)>=32,'Reviewer key unavailable'); return value.encode()


def signed(payload,secret):
    return dict(payload=payload,mac=hmac.new(secret,c.canonical(payload),hashlib.sha256).hexdigest())


def verified(envelope,secret):
    c.fields(envelope,('payload','mac')); c.digest_ok(envelope['mac'])
    require(hmac.compare_digest(signed(envelope['payload'],secret)['mac'],envelope['mac']),'Bundle authentication failed'); return envelope['payload']


def put(path,obj):
    """Same-filesystem no-replace publication; interrupted temp is never imported."""
    raw=c.canonical(obj); path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        require(not path.is_symlink() and path.read_bytes()==raw,'Conflicting immutable bundle'); return
    tmp=path.with_name('.'+secrets.token_hex(16)+'.tmp')
    try:
        with os.fdopen(os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        try: os.link(tmp,path)
        except FileExistsError: require(not path.is_symlink() and path.read_bytes()==raw,'Conflicting immutable bundle')
    finally: tmp.unlink(missing_ok=True)


def policy(root):
    v=c.load(safe(root,'config/collaboration.json')); c.fields(v,('schema','private_export','reviewers','allowed_runs'))
    require(type(v['schema']) is int and v['schema']==1 and type(v['private_export']) is bool,'Invalid collaboration consent')
    require(type(v['reviewers']) is dict and 2<=len(v['reviewers'])<=16,'Independent reviewer slots required')
    require(all(SAFE.fullmatch(x) for x in v['reviewers']),'Invalid reviewer ID')
    slots=list(v['reviewers'].values()); require(len(set(slots))==len(slots) and all(type(s) is str and s.startswith('VRS_REVIEW_KEY_') and SAFE.fullmatch(s) for s in slots),'Reviewer credentials must be isolated')
    require(type(v['allowed_runs']) is list,'Explicit private run allowlist required')
    for r in v['allowed_runs']: c.digest_ok(r)
    return v


def validate_choice(v,inventory):
    c.fields(v,('kind','mappings')); require(v['kind'] in ('glyph','false_positive','compound','deferred'),'Invalid review disposition')
    maps=v['mappings']; require(type(maps) is dict,'Invalid mapping')
    if v['kind']!='glyph': require(not maps,'Unexpected mapping'); return
    require(set(maps)==set(inventory),'Every convention requires a disposition')
    for n,r in maps.items():
        c.fields(r,('state','label')); require(r['state'] in ('mapped','absent','unknown'),'Invalid mapping state')
        require((r['state']=='mapped' and r['label'] in inventory[n]) or (r['state']!='mapped' and r['label'] is None),'Invalid label')


def response(bundle,choice,secret):
    a=verified(bundle,secret); c.fields(a,('schema','assignment','reviewer','inventory','image','image_sha256'))
    require(a['schema']==1,'Unsupported assignment'); c.digest_ok(a['assignment']); require(SAFE.fullmatch(a['reviewer']),'Invalid reviewer')
    raw=base64.b64decode(a['image'],validate=True); require(hashlib.sha256(raw).hexdigest()==a['image_sha256'],'Image digest mismatch')
    validate_choice(choice,a['inventory'])
    return signed(dict(schema=1,assignment=a['assignment'],reviewer=a['reviewer'],assignment_sha256=c.digest(a),choice=choice),secret)


class Collaboration:
    def __init__(self,root):
        self.root=Path(root).resolve(strict=True); self.desktop=Desktop(self.root)
        self.home=safe(self.root,'workspace/vrs110/private'); self.home.mkdir(parents=True,exist_ok=True)

    def current(self,run,candidate):
        offset=0
        while offset is not None:
            q=self.desktop.review(run,offset=offset,limit=100)
            for item in q['items']:
                if item['id']==candidate: return q,item
            offset=q['next_offset']
        raise ValueError('Candidate not currently reviewable')

    def assign(self,run,candidate,reviewers):
        p=policy(self.root); require(p['private_export'] and run in p['allowed_runs'],'Private export not authorized')
        require(type(reviewers) is list and 2<=len(reviewers)<=16 and len(set(reviewers))==len(reviewers) and set(reviewers)<=set(p['reviewers']),'Distinct approved reviewers required')
        reviewers=sorted(reviewers); keys={r:key(p['reviewers'][r]) for r in reviewers}; require(len(set(keys.values()))==len(keys),'Reviewer keys not isolated')
        with scheduler_lock(self.home/'collaboration.lock'):
            q,item=self.current(run,candidate); im,box=self.desktop.crop(item)
            # Crop only, no page/locus, model suggestion, owner label, or raw context metadata.
            stream=io.BytesIO(); im.crop(box).save(stream,format='PNG'); raw=stream.getvalue(); require(len(raw)<=400000,'Assignment image too large')
            scope=dict(run_id=run,candidate_id=candidate,queue_sha256=q['snapshot']['queue_sha256'],revision=item['revision'],reviewers=reviewers,inventory=q['inventory'],image_sha256=hashlib.sha256(raw).hexdigest())
            cohort=c.digest(scope); folder=safe(self.root,'workspace/vrs110/private/'+cohort); folder.mkdir(exist_ok=True)
            record=folder/'assignment.json'
            if record.exists():
                saved=c.load(record); require(saved['scope']==scope,'Assignment conflict'); ids=saved['ids']
            else:
                ids={r:secrets.token_hex(32) for r in reviewers}; put(record,dict(scope=scope,ids=ids))
            for r in reviewers:
                a=dict(schema=1,assignment=ids[r],reviewer=r,inventory=q['inventory'],image=base64.b64encode(raw).decode('ascii'),image_sha256=scope['image_sha256'])
                put(folder/(r+'.assignment.json'),signed(a,keys[r]))
            return dict(cohort=cohort,assignments=[str((folder/(r+'.assignment.json')).relative_to(self.root)) for r in reviewers])

    def load(self,cohort):
        c.digest_ok(cohort); folder=safe(self.root,'workspace/vrs110/private/'+cohort); record=c.load(folder/'assignment.json')
        require(c.digest(record['scope'])==cohort,'Assignment binding mismatch'); return folder,record

    def receive(self,cohort,envelope):
        p=policy(self.root)
        with scheduler_lock(self.home/'collaboration.lock'):
            folder,record=self.load(cohort); scope=record['scope']; r=envelope['payload']['reviewer']
            require(p['private_export'] and scope['run_id'] in p['allowed_runs'] and r in record['ids'] and r in p['reviewers'],'Reviewer or run not authorized')
            secret=key(p['reviewers'][r]); v=verified(envelope,secret); c.fields(v,('schema','assignment','reviewer','assignment_sha256','choice'))
            a=verified(c.load(folder/(r+'.assignment.json')),secret)
            require(v['schema']==1 and v['assignment']==record['ids'][r] and v['assignment_sha256']==c.digest(a),'Stale or foreign assignment')
            validate_choice(v['choice'],scope['inventory'])
            dest=folder/(r+'.response.json')
            if dest.exists(): put(dest,envelope) # exact retry only
            else:
                q,item=self.current(scope['run_id'],scope['candidate_id']); require(q['snapshot']['queue_sha256']==scope['queue_sha256'] and item['revision']==scope['revision'],'Stale decision revision')
                put(dest,envelope)
            return self.status(cohort)

    def status(self,cohort):
        folder,record=self.load(cohort); reviewers=record['scope']['reviewers']; n=sum((folder/(r+'.response.json')).is_file() for r in reviewers)
        return dict(cohort=cohort,received=n,expected=len(reviewers),unique_candidates=1,replicas=len(reviewers),status='SEALED' if n<len(reviewers) else 'READY_FOR_CURATOR')

    def adjudicate(self,cohort,curator,choice=None):
        """Return a revision-bound local decision draft; never automatically submit it."""
        p=policy(self.root)
        with scheduler_lock(self.home/'collaboration.lock'):
            folder,record=self.load(cohort); scope=record['scope']; require(self.status(cohort)['status']=='READY_FOR_CURATOR','Reviews still sealed')
            require(SAFE.fullmatch(curator) and curator not in scope['reviewers'],'Separate curator required')
            require(p['private_export'] and scope['run_id'] in p['allowed_runs'],'Consent revoked')
            results=[]
            for r in scope['reviewers']:
                secret=key(p['reviewers'][r]); v=verified(c.load(folder/(r+'.response.json')),secret); a=verified(c.load(folder/(r+'.assignment.json')),secret)
                require(v['reviewer']==r and v['assignment']==record['ids'][r] and v['assignment_sha256']==c.digest(a),'Review binding mismatch'); validate_choice(v['choice'],scope['inventory']); results.append(v['choice'])
            q,item=self.current(scope['run_id'],scope['candidate_id']); require(item['revision']==scope['revision'] and q['snapshot']['queue_sha256']==scope['queue_sha256'],'Stale decision revision')
            if choice is None: return dict(reviews=results,scientific_status='UNADJUDICATED')
            validate_choice(choice,scope['inventory']); decision=dict(schema=1,run_id=scope['run_id'],candidate_id=scope['candidate_id'],queue_sha256=scope['queue_sha256'],expected_revision=scope['revision'],reviewer=curator,**choice)
            put(folder/'adjudication.json',dict(decision=decision,reviews_sha256=[c.digest(x) for x in results],unanimous=all(x==results[0] for x in results)))
            return dict(decision=decision,reviews=results,scientific_status='UNADJUDICATED')


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('root',type=Path); sub=p.add_subparsers(dest='action',required=True)
    q=sub.add_parser('assign'); q.add_argument('run'); q.add_argument('candidate'); q.add_argument('reviewers',nargs='+')
    q=sub.add_parser('respond'); q.add_argument('assignment'); q.add_argument('choice'); q.add_argument('key_slot'); q.add_argument('output')
    q=sub.add_parser('receive'); q.add_argument('cohort'); q.add_argument('response')
    q=sub.add_parser('status'); q.add_argument('cohort'); q=sub.add_parser('adjudicate'); q.add_argument('cohort'); q.add_argument('curator'); q.add_argument('choice',nargs='?')
    a=p.parse_args(); root=a.root.resolve(strict=True)
    try:
        if a.action=='respond':
            v=response(c.load(safe(root,a.assignment)),c.load(safe(root,a.choice)),key(a.key_slot)); put(safe(root,a.output),v); result=dict(status='SAVED')
        else:
            app=Collaboration(root)
            if a.action=='assign': result=app.assign(a.run,a.candidate,a.reviewers)
            elif a.action=='receive': result=app.receive(a.cohort,c.load(safe(root,a.response)))
            elif a.action=='status': result=app.status(a.cohort)
            else: result=app.adjudicate(a.cohort,a.curator,c.load(safe(root,a.choice)) if a.choice else None)
        print(json.dumps(result,indent=2)); return 0
    except (ValueError,OSError,RuntimeError,KeyError,TypeError) as exc:
        print(json.dumps(dict(status='BLOCKED',error=type(exc).__name__))); return 1


if __name__=='__main__': raise SystemExit(main())

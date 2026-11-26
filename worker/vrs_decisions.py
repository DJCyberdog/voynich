"""VRS-097: append-only local review revisions and exact dependency wakeup."""
import hashlib
import json
import vrs_contract as c
from vrs_core import require
from vrs_exceptions import ExceptionQueue


class Decisions:
    def __init__(self, ledger):
        self.ledger=ledger; self.root=ledger.root; self.queue=ExceptionQueue(ledger)
        with ledger._tx() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS vrs096_decisions (run_id TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(run_id,id,revision), FOREIGN KEY(run_id,id) REFERENCES vrs095_queue_items(run_id,id))')

    def snapshot(self, conn, run):
        base=self.queue._summary(conn,run); latest={}; hashes=hashlib.sha256(); revisions={}
        for row in conn.execute('SELECT id,revision,payload,digest FROM vrs096_decisions WHERE run_id=? ORDER BY id,revision',(run,)):
            obj=json.loads(row['payload']); raw=c.canonical(obj); key=row['id']; rev=row['revision']
            require(c.digest(obj)==row['digest'] and raw.decode('ascii')==row['payload'] and obj['candidate_id']==key and obj['run_id']==run and obj['queue_sha256']==base['queue_sha256'] and rev==revisions.get(key,0)+1 and obj['expected_revision']==rev-1,'Decision history mismatch')
            revisions[key]=rev; latest[key]=obj; hashes.update(raw+b'\n')
        resolved=sum(d['kind'] in ('glyph','false_positive') for d in latest.values()); deferred=len(latest)-resolved
        pending=base['classification']['abstained']-len(latest); require(pending>=0,'Decision denominator mismatch')
        return dict(queue_sha256=base['queue_sha256'],decision_sha256=hashes.hexdigest(),pending=pending,resolved=resolved,deferred=deferred),latest

    def submit(self, decision, inventories, identity):
        c.fields(decision,('schema','run_id','queue_sha256','candidate_id','expected_revision','reviewer','kind','mappings'))
        require(type(decision['schema']) is int and decision['schema']==1 and type(decision['reviewer']) is str and 0<len(decision['reviewer'].strip())<=128,'Invalid decision identity')
        for k in ('run_id','queue_sha256','candidate_id'): c.digest_ok(decision[k])
        c.number(decision['expected_revision']); kind=decision['kind']; require(kind in ('glyph','false_positive','compound','deferred'),'Invalid decision kind')
        maps=decision['mappings']; require(type(maps) is dict,'Invalid mappings')
        if kind=='glyph':
            require(set(maps)==set(inventories),'Every loaded convention requires a disposition')
            for name,row in maps.items():
                c.fields(row,('state','label')); require(row['state'] in ('mapped','absent','unknown'),'Invalid mapping disposition')
                require((row['state']=='mapped' and row['label'] in inventories[name][0]) or (row['state']!='mapped' and row['label'] is None),'Invalid mapping label')
        else: require(not maps,'Non-glyph decision cannot map labels')
        run=decision['run_id']; self.queue.seed(run)
        with self.ledger._tx() as conn:
            row=self.ledger._row(conn,'runs',run); manifest,receipts,_=self.ledger._validate(row)
            require(row['worker']==identity and row['token'] is None,'Run identity or ownership mismatch')
            snap,_=self.snapshot(conn,run); require(snap['queue_sha256']==decision['queue_sha256'],'Stale queue')
            key=decision['candidate_id']; item=conn.execute('SELECT payload FROM vrs095_queue_items WHERE run_id=? AND id=?',(run,key)).fetchone(); require(item is not None,'Unknown candidate')
            c.artifact(self.root,json.loads(item[0])['crop'])
            rev=decision['expected_revision']+1; digest=c.digest(decision)
            previous=conn.execute('SELECT MAX(revision) FROM vrs096_decisions WHERE run_id=? AND id=?',(run,key)).fetchone()[0] or 0
            if previous==rev:
                old=conn.execute('SELECT digest FROM vrs096_decisions WHERE run_id=? AND id=? AND revision=?',(run,key,rev)).fetchone()[0]
                require(old==digest,'Stale or conflicting decision'); return snap
            require(row['control'] in ('BLOCKED','PAUSED') and receipts['exception_review']['reason']=='REVIEW_PENDING','Run not waiting for authorized review')
            require(previous==rev-1,'Stale decision revision')
            conn.execute('INSERT INTO vrs096_decisions VALUES (?,?,?,?,?)',(run,key,rev,c.canonical(decision).decode('ascii'),digest))
            self.ledger._event(conn,run,'REVIEW_DECISION',dict(candidate_id=key,revision=rev,decision_sha256=digest))
            snap,_=self.snapshot(conn,run)
            if not snap['pending'] and not snap['deferred'] and row['control']=='BLOCKED':
                conn.execute("UPDATE runs SET control='READY' WHERE id=?",(run,)); self.ledger._event(conn,run,'REVIEW_DEPENDENCY_READY',dict(decision_sha256=snap['decision_sha256']))
            return snap

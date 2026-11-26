"""VRS-140 read-only schema-1 workspace preflight; never migrates or authorizes execution."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

import vrs_contract as c
from vrs_core import require, sha
from vrs_desktop_api import ReadLedger, ReadDecisions, safe, pinned

VERSION='0.14.0-preflight.1'
CORE={'runs','history','outbox'}
QUEUE={'vrs095_queue_runs','vrs095_queue_items'}

def inspect(root, current_worker=None):
    root=Path(root).resolve(strict=True)
    if current_worker is not None:c.digest_ok(current_worker)
    db=safe(root,'workspace/vrs095/ledger.sqlite')
    require(db.is_file(),'Existing ledger required')
    def no_sidecars():
        for suffix in ('-wal','-shm','-journal'):
            require(not safe(root,'workspace/vrs095/ledger.sqlite'+suffix).exists(),'Stop writer and resolve SQLite sidecar before preflight')
    no_sidecars()
    before=sha(db)
    ledger=ReadLedger(root)
    counts=dict(runs=0,history=0,outbox=0,queue_items=0,decision_revisions=0,foreign_worker=0,locked=0)
    states={}; outbox_states={}; digest=hashlib.sha256()
    def bind(tag,obj):
        digest.update(c.canonical([tag,obj])+b'\n')
    def validate_refs(value):
        # Verify explicit path/hash envelopes, including historical receipt and crop references.
        if isinstance(value,dict):
            if set(value)=={'path','sha256'}:pinned(root,value)
            else:
                for v in value.values():validate_refs(v)
        elif isinstance(value,list):
            for v in value:validate_refs(v)
    with ledger._tx() as conn:
        require(conn.execute('PRAGMA journal_mode').fetchone()[0]=='delete','Unsupported journal mode for offline preflight')
        require([r[0] for r in conn.execute('PRAGMA integrity_check')]==['ok'],'SQLite integrity check failed')
        require(not conn.execute('PRAGMA foreign_key_check').fetchone(),'Ledger foreign key violation')
        tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        require(CORE<=tables,'Missing core ledger tables')
        require(not QUEUE&tables or QUEUE<=tables,'Incomplete exception queue schema')
        require('vrs096_decisions' not in tables or QUEUE<=tables,'Decision schema without queue')
        bind('tables',sorted(tables))
        for row in conn.execute('SELECT * FROM runs ORDER BY id'):
            run=row['id']; c.digest_ok(row['worker']); manifest,receipts,_=ledger._validate(row)
            require(row['backend']==('cuda' if manifest['backend']=='cuda' else 'cpu'),'Frozen backend mismatch')
            counts['runs']+=1;states[row['control']]=states.get(row['control'],0)+1
            if row['token'] is not None:counts['locked']+=1
            if current_worker is not None and row['worker']!=current_worker:counts['foreign_worker']+=1
            if row['checkpoint']:
                cp=json.loads(row['checkpoint']);require(cp['stage']==ledger._next(receipts),'Checkpoint stage mismatch');pinned(root,cp['artifact'])
            validate_refs(manifest);validate_refs(receipts)
            bind('run',dict(row))
            if QUEUE<=tables and conn.execute('SELECT 1 FROM vrs095_queue_runs WHERE run_id=?',(run,)).fetchone():
                decisions=ReadDecisions(ledger)
                if 'vrs096_decisions' in tables:
                    snap,_=decisions.snapshot(conn,run);bind('decision_snapshot',snap)
                else:bind('queue_snapshot',decisions.queue._summary(conn,run))
                for item in conn.execute('SELECT * FROM vrs095_queue_items WHERE run_id=? ORDER BY position',(run,)):
                    validate_refs(json.loads(item['payload']));bind('queue_item',dict(item));counts['queue_items']+=1
                if 'vrs096_decisions' in tables:
                    for item in conn.execute('SELECT * FROM vrs096_decisions WHERE run_id=? ORDER BY id,revision',(run,)):
                        bind('decision',dict(item));counts['decision_revisions']+=1
        for item in conn.execute('SELECT * FROM history ORDER BY seq'):
            validate_refs(json.loads(item['payload']));bind('history',dict(item));counts['history']+=1
        for item in conn.execute('SELECT * FROM outbox ORDER BY id'):
            validate_refs(json.loads(item['report']));bind('outbox',dict(item));counts['outbox']+=1
            outbox_states[item['state']]=outbox_states.get(item['state'],0)+1
            if item['token'] is not None:counts['locked']+=1
    no_sidecars()
    require(sha(db)==before,'Ledger changed during preflight')
    return dict(schema=1,version=VERSION,scope='READ_ONLY_LEDGER_PREFLIGHT',status='BLOCKED_ACTIVE_OWNERSHIP' if counts['locked'] else 'PREFLIGHT_PASS',ledger_sha256=before,logical_sha256=digest.hexdigest(),counts=counts,run_states=states,outbox_states=outbox_states,worker_comparison=current_worker is not None,automatic_migration=False,execution_authorized=False,scientific_status='UNADJUDICATED')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('--current-worker');a=p.parse_args()
    try:result=inspect(a.root,a.current_worker)
    except (ValueError,OSError,sqlite3.Error,KeyError,TypeError,RuntimeError) as exc:
        print(json.dumps(dict(status='BLOCKED',error_type=type(exc).__name__,automatic_migration=False,execution_authorized=False)));return 1
    print(json.dumps(result,sort_keys=True,indent=2));return 0 if result['status']=='PREFLIGHT_PASS' else 1

if __name__=='__main__':raise SystemExit(main())

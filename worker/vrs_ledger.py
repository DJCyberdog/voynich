"""VRS 0.9.3: local fixed-scope durable run journal and aggregate outbox.

Trusted local workspace, single database on local disk. No stage execution,
network access, remote jobs or experiment design. Recovery is explicitly fenced;
never recover a live worker or reuse its mutable output paths.
"""
import json
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import vrs_contract as c
from vrs_core import require

VERSION = '0.9.3'
DB_SCHEMA = 1


class Ledger:
    def __init__(self, root, db):
        self.root = Path(root).resolve(strict=True)
        self.db = Path(db).resolve()
        require(self.db.parent.is_dir(), 'Database parent must exist')
        with self._tx() as conn:
            version = conn.execute('PRAGMA user_version').fetchone()[0]
            require(version in (0, DB_SCHEMA), 'Unsupported ledger schema')
            if version == 0:
                require(not conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), 'Unversioned database is not empty')
                conn.execute('CREATE TABLE runs (id TEXT PRIMARY KEY, manifest TEXT NOT NULL, backend TEXT NOT NULL, worker TEXT NOT NULL, receipts TEXT NOT NULL, control TEXT NOT NULL, token TEXT, checkpoint TEXT, generation INTEGER NOT NULL DEFAULT 0)')
                conn.execute('CREATE TABLE outbox (id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), repository TEXT NOT NULL, report TEXT NOT NULL, state TEXT NOT NULL, token TEXT, remote TEXT, generation INTEGER NOT NULL DEFAULT 0)')
                conn.execute('CREATE TABLE history (seq INTEGER PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), kind TEXT NOT NULL, payload TEXT NOT NULL)')
                conn.execute('PRAGMA user_version=1')

    @contextmanager
    def _tx(self):
        conn = sqlite3.connect(self.db, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('PRAGMA synchronous=FULL')
            conn.execute('BEGIN IMMEDIATE')
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _encode(obj):
        return c.canonical(obj).decode('ascii')

    @staticmethod
    def _row(conn, table, key):
        require(table in ('runs', 'outbox'), 'Invalid table')
        row = conn.execute(f'SELECT * FROM {table} WHERE id=?', (key,)).fetchone()
        require(row is not None, 'Unknown record')
        return row

    @staticmethod
    def _next(receipts):
        return next((stage for stage in c.STAGES if receipts[stage]['state'] != 'COMPLETED'), None)

    def _validate(self, row):
        manifest = json.loads(row['manifest'])
        require(c.manifest(self.root, manifest) == row['id'], 'Manifest binding mismatch')
        receipts = json.loads(row['receipts'])
        c.fields(receipts, c.STAGES)
        used = {c.artifact(self.root, x) for x in [*manifest['inputs'].values(), *manifest['transcriptions']]}
        previous = True
        for stage in c.STAGES:
            item = receipts[stage]
            c.receipt(self.root, item, row['id'], stage)
            require(previous or (item['state'] in ('PENDING', 'BLOCKED') and item['reason'] in ('NOT_STARTED', 'DEPENDENCY')), 'Stage bypasses dependency')
            previous = previous and item['state'] == 'COMPLETED'
            if item['artifact'] is not None:
                path = c.artifact(self.root, item['artifact'])
                require(path not in used, 'Stage artifact aliases another artifact')
                used.add(path)
        review = receipts['exception_review']['counts']
        classification = receipts['glyph_classification']['counts']
        if review is not None:
            require(classification is not None and sum(review.values()) == classification['abstained'], 'Review denominator mismatch')
        return manifest, receipts, used

    def register(self, manifest, actual_backend, worker_sha256):
        run = c.manifest(self.root, manifest)
        c.digest_ok(worker_sha256)
        require(actual_backend in ('cpu', 'cuda') and manifest['backend'] in ('auto', actual_backend), 'Backend mismatch')
        raw = self._encode(manifest)
        receipts = {s: dict(schema=c.SCHEMA, run_id=run, stage=s, state='PENDING', reason='NOT_STARTED', artifact=None, counts=None) for s in c.STAGES}
        with self._tx() as conn:
            old = conn.execute('SELECT * FROM runs WHERE id=?', (run,)).fetchone()
            if old:
                require((old['manifest'], old['backend'], old['worker']) == (raw, actual_backend, worker_sha256), 'Run identity conflict')
            else:
                conn.execute('INSERT INTO runs (id,manifest,backend,worker,receipts,control) VALUES (?,?,?,?,?,?)', (run,raw,actual_backend,worker_sha256,self._encode(receipts),'READY'))
        return run

    def _event(self, conn, run, kind, payload):
        conn.execute('INSERT INTO history (run_id,kind,payload) VALUES (?,?,?)', (run,kind,self._encode(payload)))

    def history(self, run):
        with self._tx() as conn:
            self._row(conn, 'runs', run)
            return [dict(seq=r['seq'], kind=r['kind'], payload=json.loads(r['payload'])) for r in conn.execute('SELECT * FROM history WHERE run_id=? ORDER BY seq', (run,))]

    def status(self, run):
        with self._tx() as conn:
            row = self._row(conn, 'runs', run)
            receipts = json.loads(row['receipts'])
            return dict(run_id=run, control=row['control'], locked=row['token'] is not None, generation=row['generation'], next_stage=self._next(receipts), receipts=receipts, checkpoint=json.loads(row['checkpoint']) if row['checkpoint'] else None)

    def claim(self, run):
        with self._tx() as conn:
            row = self._row(conn, 'runs', run)
            require(row['control'] == 'READY' and row['token'] is None, 'Run is not claimable')
            _, receipts, used = self._validate(row)
            stage = self._next(receipts)
            require(stage is not None, 'Run already completed')
            if row['checkpoint']:
                cp = json.loads(row['checkpoint'])
                require(cp['stage'] == stage and c.artifact(self.root, cp['artifact']) not in used, 'Checkpoint binding mismatch')
            token = secrets.token_hex(32)
            conn.execute('UPDATE runs SET token=?,generation=generation+1 WHERE id=?', (token,run))
            return token

    def _owned(self, conn, run, token):
        row = self._row(conn, 'runs', run)
        require(type(token) is str and row['token'] is not None and row['token'] == token, 'Stale or missing worker token')
        return row

    def _immutable(self, conn, run, artifact):
        if artifact is None:
            return
        for row in conn.execute('SELECT payload FROM history WHERE run_id=?', (run,)):
            old = json.loads(row['payload']).get('artifact')
            if old is not None and old['path'] == artifact['path']:
                require(old == artifact, 'Historical artifact path must be immutable')

    def checkpoint(self, run, token, stage, artifact):
        with self._tx() as conn:
            row = self._owned(conn, run, token)
            require(row['control'] in ('READY', 'PAUSE_REQUESTED', 'CANCEL_REQUESTED'), 'Run not active')
            _, receipts, used = self._validate(row)
            require(stage == self._next(receipts), 'Checkpoint stage mismatch')
            path = c.artifact(self.root, artifact)
            require(path not in used, 'Checkpoint aliases input or receipt artifact')
            if row['checkpoint']:
                old = json.loads(row['checkpoint'])['artifact']
                require(old['path'] != artifact['path'] or old == artifact, 'Checkpoint path must be immutable')
            self._immutable(conn, run, artifact)
            self._event(conn, run, 'CHECKPOINT', dict(stage=stage, artifact=artifact))
            conn.execute('UPDATE runs SET checkpoint=? WHERE id=?', (self._encode(dict(stage=stage, artifact=artifact)),run))

    def record(self, run, token, item):
        with self._tx() as conn:
            row = self._owned(conn, run, token)
            require(row['control'] == 'READY', 'Stop requested')
            _, receipts, used = self._validate(row)
            stage = self._next(receipts)
            require(stage is not None, 'Run already completed')
            c.receipt(self.root, item, run, stage)
            require(item['state'] != 'PENDING', 'Cannot record pending as progress')
            old = receipts[stage]
            if item['artifact'] is not None:
                path = c.artifact(self.root, item['artifact'])
                require(path not in used or item == old, 'Stage artifact aliases another artifact')
            if stage == 'exception_review' and item['counts'] is not None:
                require(sum(item['counts'].values()) == receipts['glyph_classification']['counts']['abstained'], 'Review denominator mismatch')
            self._immutable(conn, run, item['artifact'])
            self._event(conn, run, 'RECEIPT', item)
            receipts[stage] = item
            control = ('COMPLETED' if self._next(receipts) is None else 'READY') if item['state'] == 'COMPLETED' else ('FAILED' if item['state'] == 'FAILED' else 'BLOCKED')
            new_token = token if control == 'READY' else None
            conn.execute('UPDATE runs SET receipts=?,control=?,token=?,checkpoint=NULL WHERE id=?', (self._encode(receipts),control,new_token,run))
            return control

    def request_stop(self, run, cancel=False):
        with self._tx() as conn:
            row = self._row(conn, 'runs', run)
            require(row['control'] in ('READY','BLOCKED','PAUSED','PAUSE_REQUESTED','CANCEL_REQUESTED'), 'Run not stoppable')
            require(cancel or row['control'] != 'CANCEL_REQUESTED', 'Cannot downgrade cancellation')
            state = ('CANCEL_REQUESTED' if cancel else 'PAUSE_REQUESTED') if row['token'] else ('CANCELLED' if cancel else 'PAUSED')
            conn.execute('UPDATE runs SET control=? WHERE id=?', (state,run))

    def release(self, run, token):
        with self._tx() as conn:
            row = self._owned(conn, run, token)
            state = {'PAUSE_REQUESTED':'PAUSED','CANCEL_REQUESTED':'CANCELLED'}.get(row['control'],row['control'])
            conn.execute('UPDATE runs SET control=?,token=NULL WHERE id=?', (state,run))

    def recover(self, run, expected_generation, *, worker_confirmed_stopped=False):
        require(worker_confirmed_stopped is True, 'Confirm old worker stopped before recovery')
        with self._tx() as conn:
            row = self._row(conn, 'runs', run)
            require(row['token'] is not None and type(expected_generation) is int and row['generation'] == expected_generation, 'Recovery generation mismatch')
            state = {'PAUSE_REQUESTED':'PAUSED','CANCEL_REQUESTED':'CANCELLED'}.get(row['control'],row['control'])
            conn.execute('UPDATE runs SET control=?,token=NULL WHERE id=?', (state,run))

    def resume(self, run):
        with self._tx() as conn:
            row = self._row(conn, 'runs', run)
            require(row['token'] is None and row['control'] in ('BLOCKED','PAUSED','FAILED'), 'Run not resumable')
            self._validate(row)
            conn.execute('UPDATE runs SET control=? WHERE id=?', ('READY',run))

    def enqueue(self, run, repository, research_commit, allowed_repositories, *, publish=False):
        require(publish is True, 'Publication not locally enabled')
        with self._tx() as conn:
            row = self._row(conn, 'runs', run)
            require(row['token'] is None and row['control'] in ('BLOCKED','FAILED','COMPLETED'), 'Run not in reportable state')
            manifest, receipts, _ = self._validate(row)
            report = c.evidence(self.root, manifest, receipts, repository, research_commit, allowed_repositories, row['backend'], row['worker'])
            key = c.digest(report)
            raw = self._encode(report)
            old = conn.execute('SELECT * FROM outbox WHERE id=?', (key,)).fetchone()
            if old:
                require(old['report'] == raw and old['repository'] == repository, 'Outbox identity conflict')
            else:
                conn.execute('INSERT INTO outbox (id,run_id,repository,report,state) VALUES (?,?,?,?,?)', (key,run,repository,raw,'PENDING'))
        return key

    def outbox(self):
        with self._tx() as conn:
            return [dict(id=r['id'], repository=r['repository'], state=r['state'], generation=r['generation'], remote=json.loads(r['remote']) if r['remote'] else None) for r in conn.execute('SELECT * FROM outbox ORDER BY id')]

    def claim_report(self, key, allowed_repositories, *, publish=False):
        require(publish is True, 'Publication not locally enabled')
        with self._tx() as conn:
            row = self._row(conn, 'outbox', key)
            require(row['state'] == 'PENDING' and row['token'] is None, 'Report not claimable')
            require(type(allowed_repositories) in (tuple, list, set, frozenset) and row['repository'] in allowed_repositories, 'Repository not locally authorized')
            report = json.loads(row['report'])
            require(c.digest(report) == key and report['repository'] == row['repository'], 'Outbox digest mismatch')
            token = secrets.token_hex(32)
            conn.execute('UPDATE outbox SET state=?,token=?,generation=generation+1 WHERE id=?', ('SENDING',token,key))
            return token, report

    def finish_report(self, key, token, remote=None):
        """Transport supplies a verified remote receipt; None retries publication, not compute."""
        with self._tx() as conn:
            row = self._row(conn, 'outbox', key)
            require(row['state'] == 'SENDING' and type(token) is str and row['token'] == token, 'Stale or missing publication token')
            if remote is None:
                conn.execute('UPDATE outbox SET state=?,token=NULL WHERE id=?', ('PENDING',key))
                return
            c.fields(remote, ('report_sha256','repository','pr_number','commit_sha'))
            require(remote['report_sha256'] == key and remote['repository'] == row['repository'], 'Remote receipt binding mismatch')
            c.number(remote['pr_number'])
            require(remote['pr_number'] > 0, 'Invalid PR number')
            c.digest_ok(remote['commit_sha'], c.GIT)
            conn.execute('UPDATE outbox SET state=?,token=NULL,remote=? WHERE id=?', ('SENT',self._encode(remote),key))

    def recover_report(self, key, expected_generation, *, publisher_confirmed_stopped=False):
        require(publisher_confirmed_stopped is True, 'Confirm old publisher stopped before recovery')
        with self._tx() as conn:
            row = self._row(conn, 'outbox', key)
            require(row['state'] == 'SENDING' and type(expected_generation) is int and row['generation'] == expected_generation, 'Publication recovery generation mismatch')
            conn.execute('UPDATE outbox SET state=?,token=NULL WHERE id=?', ('PENDING',key))

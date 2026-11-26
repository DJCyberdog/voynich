"""VRS-095 alpha.2: durable local exception index, not a recognition or review policy.
The same trusted local schema-1 ledger transaction binds queue imports to receipts.
No decision writes, network, automatic wakeup, or scientific acceptance.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import vrs_contract as c
from vrs_core import require
from vrs_ledger import Ledger

VERSION = '0.9.5-alpha.2'
TABLES = ('vrs095_queue_schema', 'vrs095_queue_runs', 'vrs095_queue_items')
REASONS = ('UNKNOWN', 'LOW_CONFIDENCE', 'OUT_OF_DISTRIBUTION', 'UNSUPPORTED_INVENTORY',
           'AMBIGUOUS_SEGMENTATION', 'COMPOUND_SEGMENTATION', 'CONFLICT')
MAX_PAGE_JSON = 32 * 1024 * 1024


def load_page(path):
    def unique(pairs):
        obj = {}
        for k, v in pairs:
            require(k not in obj, 'Duplicate JSON key')
            obj[k] = v
        return obj
    def reject(_):
        raise ValueError('Invalid JSON constant')
    with path.open('rb') as f:
        raw = f.read(MAX_PAGE_JSON + 1)
    require(len(raw) <= MAX_PAGE_JSON, 'Page artifact exceeds local size limit')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=reject)


def box_key(box):
    require(type(box) is list and len(box) == 4 and all(type(v) is int and 0 <= v <= 2**31-1 for v in box), 'Invalid candidate box')
    require(box[0] < box[2] and box[1] < box[3], 'Empty candidate box')
    return tuple(box)


def pages(data):
    require(type(data) is list and 1 <= len(data) <= 213, 'Invalid page index')
    ids = [r['page'] for r in data]
    require(all(type(p) is int and p > 0 for p in ids) and ids == sorted(set(ids)), 'Invalid page order')
    return ids


def candidate_id(run, page, region, crop, box):
    return c.digest(dict(run_id=run, page=page, region_id=region, crop=crop, box=box))


def outcomes(root, run, manifest, receipts):
    """Yield every proposed occurrence with its explicit outcome in source order.

    The VRS-096 producer must emit this versioned outcome index. Accepted/failed
    rows remain in that immutable artifact; only abstentions become queue items.
    """
    def read(ref): return load_page(c.artifact(root, ref))
    r = receipts['script_regions']; s = receipts['glyph_segmentation']; p = receipts['glyph_classification']
    require(all(x['state'] == 'COMPLETED' for x in (r,s,p)), 'Classification not completed')
    regions, seg, result = (read(x['artifact']) for x in (r,s,p))
    for data, stage in ((regions,'script_regions'),(seg,'glyph_segmentation'),(result,'glyph_classification')):
        require(type(data['schema']) is int and data['schema'] == 1 and data['run_id'] == run and data['stage'] == stage and data['scientific_status'] == 'UNADJUDICATED', 'Outcome stage binding mismatch')
    require(regions['kind'] == 'INK_PROPOSALS_ONLY' and seg['kind'] == 'UNREVIEWED_BOX_PROPOSALS_ONLY', 'Unsupported proposal contract')
    c.fields(result, ('schema','run_id','stage','scientific_status','kind','source','model_sha256','policy_sha256','references_sha256','pages'))
    require(result['kind'] == 'OCCURRENCE_OUTCOMES_V1' and seg['source'] == r['artifact'] and result['source'] == s['artifact'], 'Outcome source binding mismatch')
    for key, role in (('model_sha256','model'),('policy_sha256','recognition_policy'),('references_sha256','references')):
        require(result[key] == manifest['inputs'][role]['sha256'], 'Outcome model/policy/reference binding mismatch')
    require(pages(regions['pages']) == pages(seg['pages']) == pages(result['pages']), 'Page coverage mismatch')
    for rr, ss, pp in zip(regions['pages'],seg['pages'],result['pages']):
        page = rr['page']
        c.fields(pp, ('page','outcomes'))
        mp = c.artifact(root,rr['manifest']); m = load_page(mp)
        a = read(ss['proposals']); b = read(pp['outcomes'])
        c.fields(b, ('schema','run_id','page','source','rows'))
        require(type(b['schema']) is int and b['schema'] == 1 and b['run_id'] == run and type(b['page']) is int and b['page'] == page and b['source'] == ss['proposals'], 'Outcome page binding mismatch')
        require(a['source'] == rr['manifest'] and set(m['page_dimensions']) == {str(page)}, 'Proposal page binding mismatch')
        ids = [x['id'] for x in m['regions']]
        require(len(ids) == rr['regions'] == len(set(ids)) and ids == [x['id'] for x in a['regions']], 'Region coverage mismatch')
        require(type(b['rows']) is list, 'Invalid outcome rows')
        lookup = {}
        for row in b['rows']:
            c.fields(row, ('region_id','box','outcome','reason','uncertainty'))
            require(type(row['region_id']) is str and 0 < len(row['region_id']) <= 128, 'Invalid region ID')
            key = row['region_id'], box_key(row['box'])
            require(key not in lookup, 'Duplicate outcome occurrence')
            allowed = {'ACCEPTED': ('NONE',), 'ABSTAINED': REASONS, 'FAILED': ('PROCESSING_ERROR',)}
            require(row['outcome'] in allowed and row['reason'] in allowed[row['outcome']], 'Invalid outcome reason')
            u = row['uncertainty']
            require(u is None or (type(u) in (int,float) and 0 <= u <= 1 and math.isfinite(u)), 'Invalid uncertainty')
            lookup[key] = row
        count = 0
        for region, proposal in zip(m['regions'],a['regions']):
            rid = region['id']
            require(type(rid) is str and 0 < len(rid) <= 128 and region['page'] == page and proposal['status'] == 'unreviewed', 'Invalid region binding')
            raw = region['file']
            require(type(raw) is str and not Path(raw).is_absolute(), 'Invalid crop path')
            crop = dict(path=(mp.parent.relative_to(root)/raw).as_posix(),sha256=region['sha256'])
            c.artifact(root,crop)
            px = box_key(region['pixel_box']); width,height = px[2]-px[0],px[3]-px[1]
            for box in proposal['boxes']:
                coords = box_key(box)
                require(coords[2] <= width and coords[3] <= height, 'Candidate outside crop')
                key = rid,coords
                require(key in lookup, 'Missing or duplicate proposed occurrence')
                row = lookup.pop(key); count += 1
                payload = dict(id=candidate_id(run,page,rid,crop,box),run_id=run,page=page,region_id=rid,box=box,crop=crop,
                               reason=row['reason'],uncertainty=row['uncertainty'],model_sha256=result['model_sha256'],
                               policy_sha256=result['policy_sha256'],references_sha256=result['references_sha256'])
                yield row['outcome'], payload
        require(not lookup and count == ss['candidates'], 'Extra outcomes or candidate count mismatch')


class ExceptionQueue:
    def __init__(self, ledger):
        self.ledger = ledger
        self.root = ledger.root
        with ledger._tx() as conn:
            names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            found = names.intersection(TABLES)
            require(not found or found == set(TABLES), 'Incomplete exception schema')
            if not found:
                conn.execute('CREATE TABLE vrs095_queue_schema (version INTEGER PRIMARY KEY CHECK(version=1))')
                conn.execute('INSERT INTO vrs095_queue_schema VALUES (1)')
                conn.execute('CREATE TABLE vrs095_queue_runs (run_id TEXT PRIMARY KEY REFERENCES runs(id), receipt_sha TEXT NOT NULL, counts TEXT NOT NULL, queue_sha TEXT NOT NULL)')
                conn.execute("CREATE TABLE vrs095_queue_items (run_id TEXT NOT NULL REFERENCES vrs095_queue_runs(run_id), position INTEGER NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL, state TEXT NOT NULL CHECK(state='PENDING'), PRIMARY KEY(run_id,id), UNIQUE(run_id,position))")
            require([r[0] for r in conn.execute('SELECT version FROM vrs095_queue_schema')] == [1], 'Unsupported exception schema')

    def seed(self, run):
        """Import exactly once; a crash or invalid last row rolls back the whole import."""
        with self.ledger._tx() as conn:
            row = self.ledger._row(conn,'runs',run)
            require(row['token'] is None, 'Active worker owns run')
            manifest, receipts, _ = self.ledger._validate(row)
            classified = receipts['glyph_classification']
            require(classified['state'] == 'COMPLETED', 'Classification not completed')
            receipt_sha = c.digest(classified)
            prior = conn.execute('SELECT * FROM vrs095_queue_runs WHERE run_id=?',(run,)).fetchone()
            if prior:
                require(prior['receipt_sha'] == receipt_sha, 'Queue receipt changed')
            else:
                require(row['control'] == 'READY' and receipts['exception_review']['state'] == 'PENDING', 'Run is not ready for initial queue import')
                conn.execute('INSERT INTO vrs095_queue_runs VALUES (?,?,?,?)',(run,receipt_sha,'{}',''))
            counts = dict(total=0,accepted=0,abstained=0,failed=0); digest = hashlib.sha256(); pos=0
            for outcome,payload in outcomes(self.root,run,manifest,receipts):
                counts['total'] += 1; counts[outcome.lower()] += 1
                if outcome != 'ABSTAINED': continue
                raw = c.canonical(payload); digest.update(raw+b'\n')
                if prior:
                    saved = conn.execute('SELECT id,payload,state FROM vrs095_queue_items WHERE run_id=? AND position=?',(run,pos)).fetchone()
                    require(saved is not None and tuple(saved) == (payload['id'],raw.decode('ascii'),'PENDING'), 'Queue replay mismatch')
                else:
                    conn.execute('INSERT INTO vrs095_queue_items VALUES (?,?,?,?,?)',(run,pos,payload['id'],raw.decode('ascii'),'PENDING'))
                pos += 1
            require(counts == classified['counts'], 'Outcome denominator mismatch')
            require(conn.execute('SELECT COUNT(*) FROM vrs095_queue_items WHERE run_id=?',(run,)).fetchone()[0] == pos, 'Queue denominator mismatch')
            key=digest.hexdigest(); encoded=c.canonical(counts).decode('ascii')
            if prior:
                require(prior['queue_sha'] == key and prior['counts'] == encoded, 'Queue snapshot changed')
            else:
                conn.execute('UPDATE vrs095_queue_runs SET counts=?,queue_sha=? WHERE run_id=?',(encoded,key,run))
                self.ledger._event(conn,run,'EXCEPTION_QUEUE_SEEDED',dict(receipt_sha256=receipt_sha,queue_sha256=key,counts=counts))
            return self._summary(conn,run)

    def _summary(self, conn, run):
        row = self.ledger._row(conn,'runs',run)
        q = conn.execute('SELECT * FROM vrs095_queue_runs WHERE run_id=?',(run,)).fetchone()
        require(q is not None, 'Queue not initialized')
        item = json.loads(row['receipts'])['glyph_classification']
        require(item['state'] == 'COMPLETED' and c.digest(item) == q['receipt_sha'], 'Queue receipt changed')
        c.receipt(self.root,item,run,'glyph_classification')
        counts=json.loads(q['counts']); require(counts == item['counts'], 'Queue denominator changed')
        digest=hashlib.sha256(); pos=0
        for r in conn.execute('SELECT position,id,payload,state FROM vrs095_queue_items WHERE run_id=? ORDER BY position',(run,)):
            value=json.loads(r['payload']); raw=c.canonical(value)
            require(r['position']==pos and r['state']=='PENDING' and value['id']==r['id'] and value['run_id']==run and raw.decode('ascii')==r['payload'], 'Invalid queue item')
            digest.update(raw+b'\n'); pos+=1
        require(pos == counts['abstained'] and digest.hexdigest() == q['queue_sha'], 'Queue snapshot mismatch')
        return dict(run_id=run,queue_sha256=q['queue_sha'],classification=counts,pending=pos,resolved=0,deferred=0,
                    dependency='WAITING_FOR_REVIEW' if pos else 'NO_EXCEPTIONS',dependent_stage='transcription_alignment',
                    run_control=row['control'],scientific_status='UNADJUDICATED')

    def summary(self, run):
        with self.ledger._tx() as conn: return self._summary(conn,run)

    def items(self, run, *, offset=0, limit=100):
        c.number(offset); c.number(limit,1000); require(limit>0,'Invalid page size')
        with self.ledger._tx() as conn:
            info=self._summary(conn,run); result=[]
            for row in conn.execute('SELECT payload FROM vrs095_queue_items WHERE run_id=? AND position>=? ORDER BY position LIMIT ?',(run,offset,limit)):
                value=json.loads(row['payload']); c.artifact(self.root,value['crop']); result.append(value)
            return dict(summary=info,items=result,next_offset=offset+len(result) if offset+len(result)<info['pending'] else None)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('root',type=Path); p.add_argument('action',choices=('seed','summary','items')); p.add_argument('run'); p.add_argument('--offset',type=int,default=0); p.add_argument('--limit',type=int,default=100)
    a=p.parse_args()
    try:
        root=a.root.resolve(strict=True); db=root/'workspace/vrs095/ledger.sqlite'
        for path in (root/'workspace',root/'workspace/vrs095',db):
            require(not path.is_symlink() and not getattr(path,'is_junction',lambda:False)(),'Workspace link forbidden')
        require(db.is_file(),'Existing coordinator ledger required')
        q=ExceptionQueue(Ledger(root,db))
        result=q.items(a.run,offset=a.offset,limit=a.limit) if a.action=='items' else getattr(q,a.action)(a.run)
        print(json.dumps(result,indent=2,allow_nan=False)); return 0
    except (ValueError,OSError,RuntimeError,KeyError,TypeError) as exc:
        print(json.dumps(dict(status='BLOCKED',reason=type(exc).__name__+': '+str(exc)))); return 1


if __name__=='__main__': raise SystemExit(main())

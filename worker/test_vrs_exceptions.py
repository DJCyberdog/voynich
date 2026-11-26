import copy
import hashlib
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import vrs_contract as c
from vrs_core import sha
from vrs_ledger import Ledger
from vrs_exceptions import ExceptionQueue


class QueueTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name); self.db=self.root/'ledger.sqlite'; self.ledger=Ledger(self.root,self.db)
        self.q=ExceptionQueue(self.ledger)
        self.m=dict(schema=1,module=c.MODULE,protocol=c.PROTOCOL,backend='cpu',seed=7,run_nonce='1'*32,
                    inputs={role:self.file(role,role) for role in c.ROLES},transcriptions=[self.file('eva','text')])

    def file(self,name,value):
        path=self.root/name; path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,sort_keys=True),encoding='utf-8')
        return dict(path=name,sha256=sha(path))

    def receipt(self,run,stage,artifact,counts=None):
        return dict(schema=1,run_id=run,stage=stage,state='COMPLETED',reason='NONE',artifact=artifact,counts=counts)

    def fixture(self,nonce='1',empty=False,mutate=None,counts_override=None,locked=False):
        m=dict(self.m,run_nonce=nonce*32); run=self.ledger.register(m,'cpu','a'*64)
        prefix=nonce+'/'; token=self.ledger.claim(run)
        rp=[]; sp=[]; cp=[]; counts=dict(total=0,accepted=0,abstained=0,failed=0)
        for page in (1,2):
            regs=[]; props=[]; rows=[]
            if not empty:
                for rid in ('a','b'):
                    crop=self.file(prefix+f'p{page}/{rid}.png','same bytes')
                    regs.append(dict(id=rid,page=page,file=rid+'.png',sha256=crop['sha256'],pixel_box=[10,20,30,40]))
                    boxes=[[1,1,4,5],[5,1,9,5]]
                    props.append(dict(id=rid,status='unreviewed',boxes=boxes))
                    for i,box in enumerate(boxes):
                        outcome,reason=(('ABSTAINED','UNKNOWN') if i==0 else ('ACCEPTED','NONE')) if rid=='a' else (('ABSTAINED','CONFLICT') if i==0 else ('FAILED','PROCESSING_ERROR'))
                        rows.append(dict(region_id=rid,box=box.copy(),outcome=outcome,reason=reason,uncertainty=.8 if outcome=='ABSTAINED' else None))
                        counts['total']+=1; counts[outcome.lower()]+=1
            mr=self.file(prefix+f'p{page}/manifest.json',dict(page_dimensions={str(page):[100,100]},regions=regs))
            sr=self.file(prefix+f'p{page}/proposals.json',dict(source=mr,regions=props))
            result=dict(schema=1,run_id=run,page=page,source=sr,rows=list(reversed(rows)))
            if page==2 and mutate: mutate(result)
            cr=self.file(prefix+f'p{page}/outcomes.json',result)
            rp.append(dict(page=page,manifest=mr,regions=len(regs)))
            sp.append(dict(page=page,proposals=sr,candidates=sum(len(x['boxes']) for x in props)))
            cp.append(dict(page=page,outcomes=cr))
        def index(stage,kind,**extra):
            return self.file(prefix+stage+'.json',dict(schema=1,run_id=run,stage=stage,scientific_status='UNADJUDICATED',kind=kind,**extra))
        r=index('script_regions','INK_PROPOSALS_ONLY',pages=rp)
        s=index('glyph_segmentation','UNREVIEWED_BOX_PROPOSALS_ONLY',source=r,pages=sp)
        p=index('glyph_classification','OCCURRENCE_OUTCOMES_V1',source=s,pages=cp,model_sha256=m['inputs']['model']['sha256'],policy_sha256=m['inputs']['recognition_policy']['sha256'],references_sha256=m['inputs']['references']['sha256'])
        for stage,ref in zip(c.STAGES[:3],(r,s,p)):
            self.ledger.record(run,token,self.receipt(run,stage,ref,(counts_override or counts) if stage=='glyph_classification' else None))
        if not locked: self.ledger.release(run,token)
        return run,token

    def test_only_abstentions_and_distinct_occurrences(self):
        run,_=self.fixture(); info=self.q.seed(run)
        self.assertEqual(info['classification'],dict(total=8,accepted=2,abstained=4,failed=2))
        self.assertEqual((info['pending'],info['dependency'],info['dependent_stage']),(4,'WAITING_FOR_REVIEW','transcription_alignment'))
        rows=self.q.items(run)['items']; self.assertEqual(len({r['id'] for r in rows}),4)
        self.assertEqual(len({r['crop']['sha256'] for r in rows}),1)
        self.assertEqual([r['page'] for r in rows],[1,1,2,2])
        self.assertEqual([r['reason'] for r in rows],['UNKNOWN','CONFLICT']*2)
        self.assertEqual(self.ledger.status(run)['next_stage'],'exception_review')
        self.assertEqual(self.ledger.status(run)['control'],'READY')
        self.assertEqual(self.ledger.outbox(),[])

    def test_restart_idempotent_pagination_and_history(self):
        run,_=self.fixture(); first=self.q.seed(run)
        q=ExceptionQueue(Ledger(self.root,self.db)); self.assertEqual(q.seed(run),first)
        a=q.items(run,limit=2); b=q.items(run,offset=a['next_offset'],limit=2)
        self.assertIsNone(b['next_offset']); self.assertEqual(a['items']+b['items'],q.items(run)['items'])
        self.assertEqual(len([r for r in self.ledger.history(run) if r['kind']=='EXCEPTION_QUEUE_SEEDED']),1)
        with self.assertRaises(ValueError): q.items(run,limit=0)
        with self.assertRaises(ValueError): q.items(run,offset=-1)

    def test_concurrent_seed_exactly_once(self):
        run,_=self.fixture()
        with ThreadPoolExecutor(max_workers=2) as pool:
            a,b=pool.map(lambda _:ExceptionQueue(Ledger(self.root,self.db)).seed(run),range(2))
        self.assertEqual(a,b); self.assertEqual(len(self.q.items(run)['items']),4)
        self.assertEqual(len([r for r in self.ledger.history(run) if r['kind']=='EXCEPTION_QUEUE_SEEDED']),1)

    def test_late_duplicate_rolls_back_everything(self):
        run,_=self.fixture(mutate=lambda x:x['rows'].append(copy.deepcopy(x['rows'][0])))
        with self.assertRaisesRegex(ValueError,'Duplicate outcome'): self.q.seed(run)
        with self.ledger._tx() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM vrs095_queue_runs').fetchone()[0],0)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM vrs095_queue_items').fetchone()[0],0)
        self.assertEqual(self.ledger.status(run)['next_stage'],'exception_review')

    def test_missing_and_extra_occurrences(self):
        run,_=self.fixture(mutate=lambda x:x['rows'].pop())
        with self.assertRaisesRegex(ValueError,'Missing'): self.q.seed(run)
        run,_=self.fixture('2',mutate=lambda x:x['rows'][0].update(box=[12,12,15,15]))
        with self.assertRaisesRegex(ValueError,'Missing'): self.q.seed(run)
        run,_=self.fixture('3',mutate=lambda x:x['rows'].append(dict(x['rows'][0],box=[12,12,15,15])))
        with self.assertRaisesRegex(ValueError,'Extra'): self.q.seed(run)

    def test_denominator_and_reason_rejection(self):
        run,_=self.fixture(counts_override=dict(total=8,accepted=3,abstained=3,failed=2))
        with self.assertRaisesRegex(ValueError,'denominator'): self.q.seed(run)
        run,_=self.fixture('2',mutate=lambda x:x['rows'][0].update(reason='NONE'))
        with self.assertRaisesRegex(ValueError,'outcome reason'): self.q.seed(run)
        run,_=self.fixture('3',mutate=lambda x:x['rows'][0].update(uncertainty=True))
        with self.assertRaisesRegex(ValueError,'uncertainty'): self.q.seed(run)

    def test_locked_and_unclassified_run_rejected(self):
        run,_=self.fixture(locked=True)
        with self.assertRaisesRegex(ValueError,'Active worker'): self.q.seed(run)
        other=self.ledger.register(dict(self.m,run_nonce='9'*32),'cpu','a'*64)
        with self.assertRaisesRegex(ValueError,'not completed'): self.q.seed(other)

    def test_empty_queue_is_not_scientific_acceptance(self):
        run,_=self.fixture(empty=True); info=self.q.seed(run)
        self.assertEqual(info['pending'],0); self.assertEqual(info['dependency'],'NO_EXCEPTIONS')
        self.assertEqual(info['queue_sha256'],hashlib.sha256(b'').hexdigest())
        self.assertEqual(info['scientific_status'],'UNADJUDICATED')
        self.assertEqual(self.ledger.status(run)['next_stage'],'exception_review')

    def test_tamper_crop_and_stored_queue(self):
        run,_=self.fixture(); self.q.seed(run)
        item=self.q.items(run)['items'][0]; path=self.root/item['crop']['path']; path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'hash mismatch'): self.q.items(run)
        with self.assertRaisesRegex(ValueError,'hash mismatch'): self.q.seed(run)
        with self.ledger._tx() as conn:
            row=conn.execute('SELECT payload FROM vrs095_queue_items WHERE run_id=? AND position=0',(run,)).fetchone()
            value=json.loads(row[0]); value['reason']='LOW_CONFIDENCE'
            conn.execute('UPDATE vrs095_queue_items SET payload=? WHERE run_id=? AND position=0',(c.canonical(value).decode('ascii'),run))
        with self.assertRaisesRegex(ValueError,'snapshot mismatch'): self.q.summary(run)

    def test_distinct_runs_and_moved_workspace(self):
        import shutil
        a,_=self.fixture(); b,_=self.fixture('2'); self.q.seed(a); self.q.seed(b)
        self.assertTrue(set(x['id'] for x in self.q.items(a)['items']).isdisjoint(x['id'] for x in self.q.items(b)['items']))
        with tempfile.TemporaryDirectory() as d:
            moved=Path(d)/'moved root'; shutil.copytree(self.root,moved)
            q=ExceptionQueue(Ledger(moved,moved/'ledger.sqlite'))
            self.assertEqual(q.items(a),self.q.items(a)); self.assertEqual(q.items(b),self.q.items(b))


if __name__=='__main__': unittest.main()

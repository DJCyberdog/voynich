import unittest
import subprocess
from pathlib import Path
from unittest.mock import patch
import worker as w
import pipeline as p
import test_worker as tw


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.fixture = tw.WorkerTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root

    def job(self, jid, action, inputs, options=None):
        path=self.root/(jid+'.json')
        w.write(path,dict(schema=1,id=jid,action=action,inputs={k:dict(path=str(Path(v).relative_to(self.root)),sha256=w.sha(v)) for k,v in inputs.items()},options=options or {}))
        return path

    def test_proposals(self):
        f=self.fixture
        a=p.propose(f.pdf,w.sha(f.pdf),f.groups,self.root/'p1',[1])
        b=p.propose(f.pdf,w.sha(f.pdf),f.groups,self.root/'p2',[1])
        self.assertGreater(a['proposals'],0); self.assertEqual(a,b)
        self.assertEqual(w.sha(self.root/'p1/manifest.json'),w.sha(self.root/'p2/manifest.json'))
        self.assertEqual(len(w.dataset(self.root/'p1/manifest.json')['regions']),a['proposals'])

    def test_queue_train_predict_export(self):
        f=self.fixture
        job=self.job('train1','train',dict(manifest=f.manifest,left=f.a,right=f.b,split=f.split),dict(device='cpu',epochs=2,batch=2))
        self.assertEqual(p.submit(self.root,job),'train1')
        with self.assertRaises(FileExistsError): p.submit(self.root,job)
        self.assertEqual(p.process(self.root)[0]['state'],'COMPLETED')
        self.assertEqual(p.process(self.root),[])
        output=self.root/'outputs/train1'
        j=self.job('predict1','predict',dict(manifest=f.manifest,checkpoint=output/'checkpoint.pt',report=output/'report.json'),dict(device='cpu',batch=2))
        p.submit(self.root,j); self.assertEqual(p.process(self.root)[0]['state'],'COMPLETED')
        pred=w.read(self.root/'outputs/predict1/predictions.json')
        self.assertEqual(sum(pred['counts'].values()),8)
        self.assertTrue(all(x['label'] in w.LABELS for x in pred['rows']))
        p.export(self.root,'predict1',self.root/'share.json')
        shared=w.read(self.root/'share.json'); self.assertNotIn('rows',shared['metrics']); self.assertNotIn('environment',shared['metrics'])
        self.assertNotIn(str(self.root),(self.root/'share.json').read_text())
        with (self.root/'outputs/predict1/predictions.json').open('a') as f: f.write(' ')
        with self.assertRaisesRegex(ValueError,'Report changed'): p.export(self.root,'predict1',self.root/'share.json')

    def test_git_import(self):
        f=self.fixture; job=self.job('git1','prepare',dict(pdf=f.pdf,review=f.review,groups=f.groups))
        repo=self.root/'clone'; repo.mkdir()
        def git(*args): return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,text=True).stdout.strip()
        git('init'); dest=repo/'worker/jobs/git1.json'; dest.parent.mkdir(parents=True); dest.write_bytes(job.read_bytes())
        git('add','.'); git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','fixture'); commit=git('rev-parse','HEAD')
        with self.assertRaisesRegex(ValueError,'hash/size'): p.import_git(self.root,repo,commit,'worker/jobs/git1.json','0'*64)
        self.assertEqual(p.import_git(self.root,repo,commit,'worker/jobs/git1.json',w.sha(job)),'git1')
        self.assertEqual(p.process(self.root)[0]['state'],'COMPLETED')

    def test_malformed_job_and_watch(self):
        jobs=self.root/'jobs'; jobs.mkdir(); (jobs/'broken.json').write_text('{')
        self.assertEqual(p.process(self.root)[0]['state'],'FAILED')
        self.assertEqual(p.process(self.root),[])
        with patch('pipeline.process',return_value=[]), patch('pipeline.time.sleep',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): p.watch(self.root,1)

    def test_queue_reject_and_retry(self):
        f=self.fixture
        job=self.job('prep','prepare',dict(pdf=f.pdf,review=f.review,groups=f.groups))
        p.submit(self.root,job)
        with patch('worker.prepare',side_effect=OSError('simulated')):
            self.assertEqual(p.process(self.root)[0]['state'],'FAILED')
        self.assertEqual(p.process(self.root),[])
        self.assertEqual(p.process(self.root,retry='prep')[0]['state'],'COMPLETED')
        bad=w.read(job); bad['id']='bad'; bad['inputs']['pdf']['path']='../escape.pdf'
        with self.assertRaisesRegex(ValueError,'escapes workspace'): p.validate(self.root,bad)
        bad=w.read(job); bad['options']['shell']='cmd'
        with self.assertRaisesRegex(ValueError,'Unsupported'): p.validate(self.root,bad)
        bad=w.read(job); bad['inputs']['pdf']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'hash mismatch'): p.validate(self.root,bad)
        lock=self.root/'worker.lock'; lock.write_text('existing')
        with self.assertRaises(FileExistsError): p.process(self.root)
        self.assertEqual(lock.read_text(),'existing'); lock.unlink()

if __name__=='__main__': unittest.main()

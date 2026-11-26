import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from vrs_worker_log import WorkerLog
from vrs_portable_logs import records

class TestWorkerLog(unittest.TestCase):
    def test_lifecycle_and_safe_stage(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve()
            with patch.dict(os.environ,{'VRS_PORTABLE_LOG_ROOT':str(root)}):
                w=WorkerLog(root);w.start();w.sweep([{'run_id':'a'*64,'control':'BLOCKED','stage':'exception_review','reason':'PRIVATE_TOKEN'},{'run_id':'bad','control':'READY'},{'run_id':'b'*64,'control':'ERROR'}]);w.stop()
            rows=records(root);self.assertEqual([r['event'] for r in rows],['WORKER_START','JOB_STATE','JOB_STATE','WORKER_STOP']);self.assertEqual(rows[1]['stage'],'exception_review');self.assertNotIn('PRIVATE_TOKEN',json.dumps(rows));self.assertNotIn('state',rows[2])
    def test_legacy_and_logging_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve()
            with patch.dict(os.environ,{'VRS_PORTABLE_LOG_ROOT':''}):WorkerLog(root).start()
            self.assertEqual(records(root),[])
            with patch.dict(os.environ,{'VRS_PORTABLE_LOG_ROOT':str(root)}),patch('vrs_worker_log.event',side_effect=OSError('disk')):
                w=WorkerLog(root);w.start();self.assertTrue(w.logging_failed)

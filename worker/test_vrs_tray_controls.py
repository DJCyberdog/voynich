import unittest
from unittest.mock import Mock
import vrs_tray_controls as t


def row(ident, state, locked=False, stage='glyph_segmentation', reason='NONE'):
    return dict(id=ident, control=state, locked=locked, stage=stage, reason=reason)


class TrayControlsTests(unittest.TestCase):
    def view(self, rows=(), state='RUNNING', ident='s', configured=True):
        return t.snapshot(dict(state=state,id=ident),rows,configured,'key')

    def test_start_stop(self):
        for state in t.STARTABLE:
            self.assertEqual(t.target(self.view(state=state),'start'),(state,'s'))
        self.assertIsNone(t.target(self.view(state='UNKNOWN'),'start'))
        self.assertIsNone(t.target(self.view(state='STOP_REQUESTED'),'stop'))
        self.assertEqual(t.target(self.view(),'stop'),('s',))
        self.assertIsNone(t.target(self.view(state='STOPPED',configured=False),'start'))

    def test_only_unambiguous_runs(self):
        rows=[row('a','READY',True),row('b','PAUSED'),row('c','BLOCKED',stage='exception_review',reason='REVIEW_PENDING')]
        v=self.view(rows);self.assertEqual(v.review,1);self.assertEqual(t.target(v,'pause'),('s','a'));self.assertEqual(t.target(v,'resume'),('s','b'))
        self.assertIsNone(t.target(self.view(rows+[row('d','READY')]),'pause'))
        self.assertIsNone(t.target(self.view([row('b','PAUSED',True)]),'resume'))
        self.assertIsNone(t.target(self.view([rows[2]]),'resume'))
        self.assertIsNone(t.target(self.view(rows,configured=False),'pause'))

    def test_stale_target_refused(self):
        api=Mock();v=self.view([row('a','READY')]);expected=t.target(v,'pause')
        for fresh in (self.view([row('b','READY')]),self.view([row('a','READY')],ident='new'),self.view([row('a','READY'),row('b','READY')])):
            with self.assertRaises(ValueError):t.execute(api,'python','pause',expected,fresh)
        self.assertEqual(api.mock_calls,[])

    def test_dispatch_exact_target(self):
        api=Mock();v=self.view([row('a','READY')]);t.execute(api,'python','pause',t.target(v,'pause'),v);api.control.assert_called_once_with('python','pause','a')
        t.execute(api,'python','stop',t.target(v,'stop'),v);api.stop.assert_called_once_with(expected_session='s')
        v=self.view(state='STOPPED');t.execute(api,'python','start',t.target(v,'start'),v);api.start.assert_called_once_with('python')

    def test_unknown_action_refused(self):
        api=Mock()
        with self.assertRaises(ValueError):t.execute(api,'python','cancel',('s',),self.view())
        self.assertEqual(api.mock_calls,[])

if __name__=='__main__':unittest.main()

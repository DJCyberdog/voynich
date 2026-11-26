import unittest
from unittest.mock import Mock
import test_active_review as fixtures
import active_review as ar
import tray_client as t
import worker as w


class TrayTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.ActiveReviewTests(); f.setUp(); self.addCleanup(f.doCleanups); self.f=f
        self.config=f.root/'tray.json'
        self.row=dict(id='batch1',reviewer='owner',manifest=f.manifest.name,predictions=f.pred.name,references=f.refs.name,output=f.out.name)
        self.data=dict(schema=1,poll_seconds=5,notify_at=2,cooldown_seconds=60,sessions=[self.row]); w.write(self.config,self.data)

    def test_counts_and_review_binding(self):
        m=t.Monitor(self.config); self.assertEqual(m.poll(),[t.Status('batch1',3,0)])
        s,rows,d=ar.open_session(self.f.manifest,self.f.pred,self.f.refs,self.f.out,'owner')
        d['decisions'][rows[0]['id']]=dict(kind='false_positive',mapping=ar.empty_mapping(s),note=''); w.write(self.f.out,d)
        self.assertEqual(m.poll(),[t.Status('batch1',2,1)])
        d['binding']['reviewer']='different'; w.write(self.f.out,d)
        self.assertEqual(m.poll()[0].state,'blocked')

    def test_invalid_config_and_alias(self):
        self.data['sessions'].append(dict(self.row,id='batch2')); w.write(self.config,self.data)
        with self.assertRaisesRegex(ValueError,'Duplicate review output'): t.configuration(self.config)
        self.data['sessions']=[dict(self.row,output=self.row['manifest'])]; w.write(self.config,self.data)
        with self.assertRaisesRegex(ValueError,'aliases'): t.configuration(self.config)
        self.data['sessions']=[self.row]; self.data['poll_seconds']=0; w.write(self.config,self.data)
        with self.assertRaisesRegex(ValueError,'poll_seconds'): t.configuration(self.config)

    def test_notifications_threshold_and_cooldown(self):
        n=t.Notices(); s=lambda k,p:t.Status(k,p,0)
        self.assertFalse(n.due([s('a',1)],2,60,0)); self.assertTrue(n.due([s('a',2)],2,60,1))
        self.assertFalse(n.due([s('a',3)],2,60,2)); self.assertTrue(n.due([s('a',3)],2,60,61))
        self.assertFalse(n.due([s('a',3)],2,60,200)); self.assertFalse(n.due([s('a',0)],2,60,201))
        self.assertTrue(n.due([s('a',2)],2,60,202)); self.assertTrue(n.due([s('b',2)],2,60,262))
        self.assertFalse(n.due([t.Status('bad',99,state='blocked')],2,60,400))

    def test_launch_single_window_and_fresh_config(self):
        proc=Mock(); proc.poll.return_value=None; spawn=Mock(return_value=proc); c=t.Controller(t.Monitor(self.config),spawn)
        self.assertIn('3 Glyphen',c.refresh(0)); self.assertTrue(c.open_next()); self.assertFalse(c.open_next())
        args=spawn.call_args.args[0]; self.assertTrue(args[1].endswith('review_client.py')); self.assertEqual(spawn.call_args.kwargs,{'shell':False}); self.assertEqual(spawn.call_count,1)
        proc.poll.return_value=0; self.data['sessions']=[]; w.write(self.config,self.data)
        self.assertFalse(c.open_next()); self.assertEqual(spawn.call_count,1)

    def test_bad_sources_and_recovery(self):
        m=t.Monitor(self.config); self.assertEqual(m.poll()[0].pending,3)
        old=self.f.pred.read_bytes(); self.f.pred.write_text('{')
        self.assertEqual(m.poll()[0].state,'blocked'); self.f.pred.write_bytes(old)
        self.assertEqual(m.poll()[0].pending,3)
        c=t.Controller(m); self.config.write_text('{'); self.assertIsNone(c.refresh()); self.assertIn('Konfiguration',c.title()); self.assertFalse(c.open_next())

    def test_tray_lifecycle_fake_backend(self):
        class Fake:
            Menu=lambda *x:x
            MenuItem=lambda *x,**kw:x
            class Icon:
                HAS_NOTIFICATION=True
                def __init__(self,*a,**kw): self.menu=kw['menu']; self.visible=False; self.messages=[]
                def notify(self,*a): self.messages.append(a)
                def run(self,setup):
                    import time
                    setup(self); deadline=time.monotonic()+5
                    while not self.messages and time.monotonic()<deadline: time.sleep(.01)
                    assert self.messages and self.visible
                    self.menu[-1][1](self,None)
                def stop(self): pass
        t.run_tray(self.config,Fake)
        self.assertFalse(self.config.with_name(self.config.name+'.tray.lock').exists())
        lock=self.config.with_name(self.config.name+'.tray.lock'); lock.write_text('existing')
        with self.assertRaises(FileExistsError): t.run_tray(self.config,Fake)
        self.assertEqual(lock.read_text(),'existing')

if __name__=='__main__': unittest.main()

import os
import unittest
import tkinter as tk
import test_active_review as fixtures
import review_client as rc
import active_review as ar
import worker as w


class ReviewClientTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.ActiveReviewTests(); f.setUp(); self.addCleanup(f.doCleanups); self.f=f
    def session(self):
        f=self.f; return rc.Session(f.manifest,f.pred,f.refs,f.out,'owner')
    def test_defer_resume_and_revision(self):
        s=self.session(); first=s.next(); self.assertEqual(s.counts(),(3,0,3,0))
        s.defer(first['id']); second=s.next(); self.assertNotEqual(first['id'],second['id'])
        s.save(second['id'],'false_positive',{}); self.assertEqual(s.counts(),(3,1,2,1))
        s=self.session(); self.assertEqual(s.next()['id'],first['id']); self.assertEqual(s.counts(),(3,1,2,0))
        s.save(second['id'],'uncertain',{}); self.assertEqual(s.data['revisions'][0]['previous']['kind'],'false_positive')
        self.assertEqual(self.session().data['decisions'][second['id']]['kind'],'uncertain')
    def test_unreviewed_and_concurrent_edit(self):
        s=self.session(); rid=s.next()['id']; other=self.session()
        with self.assertRaisesRegex(ValueError,'Mark each'): s.save(rid,'glyph',ar.empty_mapping(s.schemes))
        s.save(rid,'glyph',ar.empty_mapping(s.schemes,'not_in_inventory'))
        with self.assertRaisesRegex(ValueError,'extern geändert'): other.save(rid,'false_positive',{})
        self.assertEqual(self.session().data['decisions'][rid]['kind'],'glyph')
    def test_box_proposals_never_change_candidate(self):
        s=self.session(); row=s.next(); rid=row['id']; boxes=[[1,1,4,4],[4,1,7,4]]
        with self.assertRaisesRegex(ValueError,'nur als'):s.save(rid,'false_positive',{},proposed_boxes=boxes)
        with self.assertRaisesRegex(ValueError,'Ungültige'):s.save(rid,'compound',{},proposed_boxes=[[-1,1,4,4]])
        s.save(rid,'compound',{},proposed_boxes=boxes); self.assertEqual(self.session().data['decisions'][rid]['proposed_boxes'],boxes)
        self.assertEqual(self.session().by_id[rid]['box'],row['box'])
        self.assertEqual(self.session().data['decisions'][rid]['kind'],'compound')
    def test_search_and_preferences(self):
        s=self.session(); self.assertEqual(rc.preferred(s.schemes),('EVA-test','STA-test'))
        self.assertEqual([x[0] for x in rc.search_entries(s.schemes['EVA-test'],'X')],['x']); self.assertEqual(rc.search_entries(s.schemes['EVA-test'],'missing'),[])
    @unittest.skipUnless(os.environ.get('DISPLAY') or os.name=='nt','GUI display required')
    def test_actual_gui(self):
        root=tk.Tk(); self.addCleanup(root.destroy); s=self.session(); c=rc.Client(root,s); root.update()
        first=c.row['id']; c.panes[0].search.insert(0,'missing'); root.update(); self.assertEqual(len(c.panes[0].buttons),0)
        c.panes[0].search.delete(0,'end'); root.update(); c.panes[0].buttons['x'].invoke(); c.panes[1].buttons['y'].invoke()
        c.actions['Speichern · Ctrl+Enter'].invoke(); root.update(); self.assertEqual(s.data['decisions'][first]['mapping']['EVA-test']['label'],'x')
        second=c.row['id']; c.actions['Später · F4'].invoke(); root.update(); self.assertNotEqual(c.row['id'],second)
        c.actions['False Positive · F2'].invoke(); root.update(); self.assertIsNone(c.row); c.actions['Später · F4'].invoke(); root.update(); self.assertEqual(c.row['id'],second)
        _,_,scale,ox,oy=c.geometry; c.context.event_generate('<ButtonPress-1>',x=int(ox+scale),y=int(oy+scale)); c.context.event_generate('<ButtonRelease-1>',x=int(ox+5*scale),y=int(oy+5*scale)); root.update()
        self.assertTrue(c.proposed); c.actions['Segmentierung · F3'].invoke(); root.update(); self.assertEqual(s.counts(),(3,3,0,0)); self.assertEqual(s.data['decisions'][second]['kind'],'compound'); self.assertIn('proposed_boxes',s.data['decisions'][second])

if __name__=='__main__': unittest.main()

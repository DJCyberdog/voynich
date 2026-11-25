import os
import unittest
from unittest.mock import patch
import glyph_review as gui
import test_glyphs as tg
import worker as w


class GlyphReviewTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('DISPLAY') or os.name=='nt','GUI display required')
    def test_edit_save_resume(self):
        import tkinter as tk
        from tkinter import ttk
        f=tg.GlyphTests(); f.setUp(); self.addCleanup(f.doCleanups)
        out=f.root/'gui.json'; original=tk.Tk; seen=[]; errors=[]
        def open_gui(edit):
            def create(*a,**kw):
                root=original(*a,**kw)
                def exercise():
                    try:
                        children=root.winfo_children(); seen.append(children[0].cget('text'))
                        if edit:
                            panel=children[2]; listing=panel.winfo_children()[0]; controls=panel.winfo_children()[1]
                            listing.selection_set(0); listing.event_generate('<ButtonRelease-1>'); root.update()
                            selector=controls.winfo_children()[0]; selector.set('X')
                            controls.winfo_children()[1].invoke()
                            nav=children[-1]; nav.winfo_children()[2].invoke(); nav.winfo_children()[1].invoke()
                    except Exception as e: errors.append(e)
                    finally: root.destroy()
                root.after(120,exercise); root.after(2500,root.destroy); return root
            with patch('tkinter.Tk',side_effect=create): gui.review(f.manifest,f.alphabet,out,'reviewer')
        open_gui(True); self.assertFalse(errors,errors)
        row=w.read(out)['regions']['r0']; self.assertEqual(row['glyphs'][0]['label'],'X'); self.assertEqual(row['status'],'single_line')
        open_gui(False); self.assertIn('2/4',seen[-1]); self.assertFalse(errors,errors)
        with self.assertRaisesRegex(ValueError,'belongs'): gui.review(f.manifest,f.alphabet,out,'other')

if __name__=='__main__': unittest.main()

import os
import unittest
from unittest.mock import patch
import test_worker as tw
import worker as w


class GuiTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('DISPLAY') or os.name=='nt','GUI display required')
    def test_annotation_buttons_and_resume(self):
        import tkinter as tk
        f=tw.WorkerTests(); f.setUp(); self.addCleanup(f.doCleanups)
        output=f.root/'gui.json'; original=tk.Tk; observed=[]
        def open_gui(first):
            def create(*args,**kwargs):
                root=original(*args,**kwargs)
                def inspect():
                    try:
                        observed.append(root.winfo_children()[0].cget('text'))
                        if first:
                            buttons={b.cget('text'):b for b in root.winfo_children()[-1].winfo_children()}
                            buttons['1 Script'].invoke(); buttons['2 Non-script'].invoke()
                    finally: root.destroy()
                root.after(100,inspect); root.after(2000,root.destroy)
                return root
            with patch('tkinter.Tk',side_effect=create): w.annotate(f.manifest,output,'gui-reviewer')
        open_gui(True); a=w.read(output)
        self.assertEqual(list(a['labels'].values()),['script','non_script'])
        open_gui(False); self.assertIn('3/8',observed[-1])
        with self.assertRaisesRegex(ValueError,'belongs to someone else'):
            w.annotate(f.manifest,output,'another-reviewer')

if __name__=='__main__': unittest.main()

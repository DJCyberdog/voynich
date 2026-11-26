"""CI-only gallery of actual Tk widgets using exclusively generated synthetic fixtures."""
import argparse
import os
import sys
import time
from pathlib import Path
import tkinter as tk
from unittest.mock import patch
from PIL import ImageGrab,Image,ImageDraw
from vrs_desktop_api import Desktop
from vrs_core import sha
from vrs_monitor import Monitor
from test_vrs_runtime import RuntimeTests
from vrs_portable_ui import launch

def run(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    f=RuntimeTests();f.setUp()
    try:
        pending=f.run_to_review()
        completed=f.run_to_review(dict(f.m,run_nonce='2'*32))
        for i,item in enumerate(f.app.review_items(completed,limit=1000)['items']):f.app.submit(f.decision(completed,item,'glyph' if i==0 else 'false_positive'))
        f.app.sweep();f.app.sweep()
        # Generated shapes, not authentic EVA or STA glyphs or manuscript evidence.
        refs=[]
        for scheme,labels in [('Eva-',['a','b']),('STA1',['A1','B1'])]:
            entries=[]
            for i,label in enumerate(labels):
                path=f.root/f'synthetic-reference-{scheme}-{i}.png'
                im=Image.new('RGB',(100,80),'#e1d1a9');d=ImageDraw.Draw(im);d.ellipse((20,20,65,60),outline='#4a382b',width=5);d.line((65,20,65,70),fill='#4a382b',width=4);im.save(path)
                entries.append(dict(label=label,samples=[dict(file=path.name,sha256=sha(path),source='SYNTHETIC reference shape')]))
            refs.append(dict(id=scheme,name=scheme,version='fixture',source='SYNTHETIC',coverage='fixture',entries=entries))
        catalog=f.file('synthetic-catalog.json',dict(schema=1,preview=True,schemes=refs))
        api=Desktop(f.root)
        for theme in ('dark','light'):
            cfg=api.settings();cfg.update(theme=theme,language='de',reviewer='synthetic-fixture',interpreter=sys.executable,catalog=catalog['path'],geometry='1280x800');api.save_settings(cfg)
            captured=[];original=Monitor.__init__
            def init(self,*args,**kwargs):original(self,*args,**kwargs);captured.append(self)
            def exercise(w):
                app=captured[0];w.geometry('1280x800+10+10')
                def settle():
                    deadline=time.monotonic()+25
                    while time.monotonic()<deadline:
                        w.update();time.sleep(.02)
                        if app.future is None and app.pending_view is None:
                            w.update()
                            if app.future is None and app.pending_view is None:return
                    raise RuntimeError('Screenshot UI settle timeout')
                def capture(name):
                    settle();w.update_idletasks();w.update()
                    x,y=w.winfo_rootx(),w.winfo_rooty();width,height=w.winfo_width(),w.winfo_height()
                    ImageGrab.grab(bbox=(x,y,x+width,y+height)).save(out/f'{theme}-{name}.png')
                try:
                    settle();capture('home')
                    app.run=pending;app.request_view('Review');settle()
                    app.labels.selection_set(0);app.sample();settle();capture('review')
                    app.request_view('Jobs');settle();app.jobs_tree.selection_set(pending);app.job_detail();settle();capture('jobs')
                    app.request_view('Evidence');settle();app.ev_run.set(completed);app.load_evidence();settle();capture('evidence')
                    app.request_view('Sources');settle();app.task(app.api.sources,app.result);capture('sources')
                    app.request_view('Logs');capture('logs')
                    app.request_view('Settings');capture('settings')
                    w.geometry('1024x650+10+10');app.run=pending;app.request_view('Review');settle();capture('review-compact')
                    assert app.kindbox.winfo_ismapped() and app.canvas.winfo_width()>150
                    for widget in [app.draft_button,app.submit_button,*app.zoom_controls]:
                        assert widget.winfo_ismapped() and widget.winfo_width()>=widget.winfo_reqwidth() and widget.winfo_height()>=widget.winfo_reqheight(),str(widget)
                    app.request_view('Home');settle();assert app.home_review.winfo_height()>=app.home_review.winfo_reqheight()
                finally:
                    settle();app.close()
            # Actual portable UI classes and generated data; only installed-profile
            # detection is substituted on Linux, where the Windows .venv is absent.
            with patch('vrs_portable_ui.active',return_value={'profile':'cpu'}),patch('vrs_portable_ui.exe',return_value=Path(sys.executable)),patch.object(Monitor,'__init__',init),patch.object(tk.Tk,'mainloop',exercise):
                launch(f.root,'start')
    finally:f.doCleanups()
    print('SYNTHETIC_GUI_GALLERY_PASS')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.output)

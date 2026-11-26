"""Portable desktop entry point and bounded local log viewer."""
import sys
from pathlib import Path
from vrs_portable import active, exe, need, environment
from vrs_portable_logs import event, crash, records, export, LEVELS, MODULES


def launch(root,action):
    from vrs_operations import Operations
    s=active(root)
    if action=='stop':
        ops=Operations(root); state=ops.session()['state']
        if state in ('RUNNING','STOP_REQUESTED'):
            import time
            ops.stop(); event(root,'worker','INFO','STOP_REQUESTED',state='STOP_REQUESTED')
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                if ops.session()['state']=='STOPPED':return
                time.sleep(.25)
            raise ValueError('Worker stop not confirmed')
        need(state in ('STOPPED','NOT_MANAGED'),'Worker recovery required before maintenance'); return
    import tkinter as tk
    from tkinter import ttk
    from vrs_monitor import Monitor, DE
    from vrs_desktop_api import Desktop
    from vrs_portable import local
    cfg=Desktop(root).settings()
    # Portable launcher manages its own interpreter only. No implicit external interpreter.
    if s['profile']!='review':cfg['interpreter']=str(exe(root,s['profile']))
    else:cfg['interpreter']=''
    Desktop(root).save_settings(cfg)
    DE.update({'Logs':'Protokolle','Log export':'Diagnose exportieren'})
    class Portable(Monitor):
        def build(self):
            super().build(); nav=self.nav['Home'].master; b=ttk.Button(nav,text=self.t('Logs'),command=lambda:self.show('Logs')); b.pack(fill='x',pady=4,before=self.nav['Settings']); self.nav['Logs']=b;self.w.bind('<Control-7>',lambda e:self.request_view('Logs'))
        def page_logs(self):
            self.title('Logs','Technical logs only / keine wissenschaftliche Evidenz'); bar=ttk.Frame(self.body); bar.pack(fill='x'); self.log_level=tk.StringVar(value='TRACE'); self.log_module=tk.StringVar(value='all'); self.log_query=tk.StringVar()
            ttk.Combobox(bar,textvariable=self.log_level,values=LEVELS,state='readonly',width=10).pack(side='left'); ttk.Combobox(bar,textvariable=self.log_module,values=('all',*MODULES),state='readonly',width=14).pack(side='left'); ttk.Entry(bar,textvariable=self.log_query,width=20).pack(side='left'); ttk.Button(bar,text=self.t('Refresh'),command=self.load_logs).pack(side='left'); ttk.Button(bar,text=self.t('Log export'),command=self.log_export).pack(side='left')
            self.log_text=tk.Text(self.body,wrap='word'); self.log_text.pack(fill='both',expand=True); self.load_logs()
        def load_logs(self):
            import json
            level=self.log_level.get(); module=self.log_module.get(); search=self.log_query.get()
            def done(rows):
                self.log_text.configure(state='normal'); self.log_text.delete('1.0','end'); self.log_text.insert('end','\n'.join(json.dumps(r,ensure_ascii=True) for r in rows)); self.log_text.configure(state='disabled')
            self.task(lambda:records(self.api.root,level,None if module=='all' else module,search),done)
        def log_export(self):self.task(lambda:export(self.api.root),lambda p:self.status.set('Local diagnostic ZIP saved: '+p.name))
        def refresh(self):
            if self.view=='Logs':self.load_logs()
            else:super().refresh()
        def switch(self):
            # Portable app root is fixed; do not open another workspace implicitly.
            self.status.set('Portable workspace root fixed; launch other copy separately')
    w=tk.Tk(); app=Portable(w,root); w.report_callback_exception=lambda typ,val,tb:crash(root,'application',val.with_traceback(tb)); event(root,'application','INFO','GUI_OPEN'); w.mainloop(); event(root,'application','INFO','GUI_CLOSE')


if __name__=='__main__':
    root=Path(sys.argv[1]).resolve(strict=True)
    try:launch(root,sys.argv[2])
    except Exception as e:crash(root,'application',e); sys.exit(1)

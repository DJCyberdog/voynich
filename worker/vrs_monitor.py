"""VRS operations desktop. Explicit optional Windows tray; no startup registration."""
import argparse
import json
import os
import queue
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

import vrs_desktop
from vrs_desktop import App, DE
from vrs_operations import Operations
import vrs_tray_controls as tray_controls
from vrs_build_portable import RELEASE_VERSION as VERSION
from vrs_ui_format import human,gpu_telemetry,review_fraction,brand_icon

DE.update({'Jobs':'Jobs & Ressourcen','Evidence':'Evidenz','Start worker':'Worker starten','Stop worker':'Worker stoppen','Pause':'Pausieren','Resume':'Fortsetzen','Cancel':'Abbrechen','Resource ceilings':'Ressourcengrenzen','Save ceilings':'Grenzen speichern','CPU threads':'CPU-Threads','RAM estimate MiB':'RAM-Schätzung MiB','Disk estimate MiB':'Speicherschätzung MiB','Export local preview':'Lokale Vorschau speichern','Enable tray':'Tray aktivieren','Hide to tray':'In Tray minimieren','Open':'Öffnen','Exit desktop':'Oberfläche beenden','No automatic accuracy claim':'Keine automatische Genauigkeitsaussage','Actual checkpoint progress':'Tatsächlicher Checkpoint-Fortschritt','Local managed worker':'Lokal verwalteter Worker','Review required':'Review erforderlich','No GPU telemetry':'Keine GPU-Messung','Ceilings apply after worker restart; 0 = default':'Grenzen gelten nach Worker-Neustart; 0 = Standard','Refresh evidence':'Evidenz aktualisieren','Diagnostics':'Diagnose','Compared regions':'Verglichene Regionen','Unresolved regions':'Ungeklärte Regionen'})


DE.update({'Request pending':'Anfrage läuft','Request acknowledged':'Anfrage bestätigt','Request failed':'Anfrage fehlgeschlagen','RUNNING':'Läuft','STOP_REQUESTED':'Stopp angefordert','STOPPED':'Gestoppt','PAUSE_REQUESTED':'Pause angefordert','PAUSED':'Pausiert','CANCEL_REQUESTED':'Abbruch angefordert','CANCELLED':'Abgebrochen','READY':'Bereit','UNKNOWN':'Zustand unbekannt'})

DE.update({'Pause single run':'Einzelnen Run pausieren','Resume single run':'Einzelnen Run fortsetzen','Mute notifications':'Benachrichtigungen stummschalten','Review runs':'Review-Runs','NOT_MANAGED':'Nicht verwaltet','NOT_RUNNING':'Nicht aktiv','FAILED':'Fehlgeschlagen'})

class Notifications:
    """Coalesce by parked-run set; no candidate details or repeated idle alerts."""
    def __init__(self): self.last=None; self.last_time=-1e9
    def next(self,count,key,now):
        if count is None: return False  # Unknown is not an empty review queue.
        if not count: self.last=None; return False
        if key==self.last or now-self.last_time<30: return False
        self.last=key; self.last_time=now; return True


class Monitor(App):
    def __init__(self,window,root):
        self.tray=None; self.tray_ready=False; self.events=queue.Queue(); self.notices=Notifications(); self.last_tick=0; self.last_detail=0; self.close_pending=False; self.pending_view=None
        self.tray_context=(None,'',tray_controls.Snapshot()); self.tray_muted=False; self.tray_feedback=''; self.tray_busy=False
        super().__init__(window,root); self.api=Operations(root); self.w.title('Voynich Research Studio · '+VERSION); self.w.after(250,self.tick)

    def build(self):
        super().build(); self.w.title('Voynich Research Studio · '+VERSION)
        # Reuse the original shell rather than duplicate UI design.
        nav=self.nav['Home'].master
        for name in ('Jobs','Evidence'):
            b=ttk.Button(nav,text=self.t(name),style='Nav.TButton',command=lambda n=name:self.request_view(n)); b.pack(fill='x',pady=2,before=self.nav['Settings']); self.nav[name]=b
        for name,button in self.nav.items():button.configure(command=lambda n=name:self.request_view(n))
        ttk.Button(nav,text=self.t('Enable tray'),command=self.enable_tray).pack(fill='x',pady=4)
        ttk.Button(nav,text=self.t('Hide to tray'),command=self.hide).pack(fill='x',pady=4)
        self.w.bind('<Control-j>',lambda e:self.request_view('Jobs')); self.w.bind('<Control-e>',lambda e:self.request_view('Evidence'))
        for index,name in enumerate(('Home','Review','Sources','Jobs','Evidence','Settings'),1):
            self.w.bind('<Control-'+str(index)+'>',lambda e,n=name:self.request_view(n))

    def request_view(self,name):
        if self.close_pending or self.closing:return 'break'
        if self.future is not None:self.pending_view=name
        else:
            self.pending_view=None
            self.show(name)
            if name in self.nav:self.nav[name].focus_set()
        return 'break'

    def page_home(self):
        super().page_home();self.tree.bind('<Return>',lambda e:self.open_selected())

    def switch(self):
        super().switch(); self.api=Operations(self.api.root); self.notices=Notifications(); self.reset_tray_context()

    def settings_done(self,value):
        super().settings_done(value); self.reset_tray_context()

    def reset_tray_context(self):
        self.tray_context=(str(self.api.root),self.cfg['interpreter'],tray_controls.Snapshot())
        self.tray_feedback=''; self.last_tick=0; self.update_tray()

    def quiet_task(self,fn,done):
        if self.future is not None:return
        self.future=self.pool.submit(fn)
        def poll():
            if self.closing:return
            if not self.future.done():self.w.after(30,poll);return
            future=self.future; self.future=None
            try:done(future.result())
            except Exception:self.status.set('Monitoring unavailable - refresh manually')
        self.w.after(30,poll)

    def refresh(self):
        if self.view=='Jobs': self.load_jobs()
        elif self.view=='Evidence': self.load_evidence()
        else: super().refresh()

    def page_jobs(self):
        self.title('Jobs',self.t('Actual checkpoint progress')+' · '+self.t('Local managed worker'))
        bar=ttk.Frame(self.body);bar.pack(fill='x',pady=(0,6));self.cpu_metric=self.metric(bar,'CPU');self.ram_metric=self.metric(bar,'RAM');self.gpu_metric=self.metric(bar,'GPU / VRAM')
        self.telemetry=tk.StringVar(value='—');ttk.Label(self.body,textvariable=self.telemetry,style='Muted.TLabel',wraplength=740).pack(fill='x')
        tools=ttk.Frame(self.body); tools.pack(fill='x',pady=6)
        for text,action in [('Start worker',self.start_worker),('Stop worker',self.stop_worker),('Refresh',self.load_jobs),('Diagnostics',self.diagnostics)]: ttk.Button(tools,text=self.t(text),command=action).pack(side='left',padx=(0,5))
        self.control_feedback=tk.StringVar(value='—');ttk.Label(self.body,textvariable=self.control_feedback,style='Muted.TLabel',wraplength=740).pack(fill='x')
        self.jobs_tree=ttk.Treeview(self.body,columns=('state','stage','progress','reason'),show='tree headings',height=6)
        for key,label,width in [('#0','Run',105),('state','Status',105),('stage','Stage',150),('progress','Stages',65),('reason','Reason',150)]: self.jobs_tree.heading(key,text=label); self.jobs_tree.column(key,width=width,minwidth=45)
        self.jobs_tree.pack(fill='both',expand=True);self.job_progress=ttk.Progressbar(self.body,mode='determinate',maximum=1,value=0);self.job_progress.pack(fill='x',pady=(4,0)); self.jobs_tree.bind('<<TreeviewSelect>>',lambda e:self.job_detail()); self.jobs_tree.bind('<Return>',lambda e:self.job_detail()); self.jobs_tree.bind('<Double-1>',lambda e:self.job_detail())
        ctrl=ttk.Frame(self.body); ctrl.pack(fill='x',pady=5)
        for name,action in [('Pause','pause'),('Resume','resume'),('Cancel','cancel')]: ttk.Button(ctrl,text=self.t(name),command=lambda a=action:self.run_control(a)).pack(side='left',padx=(0,5))
        ttk.Button(ctrl,text=self.t('Review'),command=self.review_job).pack(side='right')
        self.job_text=tk.Text(self.body,height=5,bg=self.p['panel'],fg=self.p['fg'],wrap='word',relief='flat'); self.job_text.pack(fill='both',expand=True); self.job_text.configure(state='disabled');self.job_value=None;ttk.Button(ctrl,text=self.t('Raw JSON'),command=lambda:self.raw_dialog(self.job_value)).pack(side='right',padx=6)
        ceilings=ttk.Frame(self.body); ceilings.pack(fill='x',pady=4); self.capvars={}; cfg=self.api.settings_ops()
        for column,(key,label) in enumerate([('cpu_threads','CPU threads'),('ram_mib','RAM estimate MiB'),('disk_mib','Disk estimate MiB')]):
            v=tk.StringVar(value=str(cfg[key]));self.capvars[key]=v;ttk.Label(ceilings,text=self.t(label)).grid(row=0,column=column,sticky='w',padx=(0,8));ttk.Entry(ceilings,textvariable=v,width=8).grid(row=1,column=column,sticky='ew',padx=(0,8));ceilings.columnconfigure(column,weight=1)
        ttk.Button(ceilings,text=self.t('Save ceilings'),command=self.save_caps).grid(row=1,column=3,sticky='e'); ttk.Label(self.body,text=self.t('Ceilings apply after worker restart; 0 = default'),style='Muted.TLabel').pack(anchor='w'); self.load_jobs()

    def selected_job(self):
        sel=self.jobs_tree.selection(); return sel[0] if sel else None

    def load_jobs(self,automatic=False):
        if self.view!='Jobs' or self.future is not None: return
        selected=self.selected_job(); api=self.api; read_detail=not automatic or time.monotonic()-self.last_detail>=15
        if read_detail:self.last_detail=time.monotonic()
        def work():
            rows=api.jobs(); data=api.resources();data['gpu_telemetry']=gpu_telemetry(); detail=api.detail(selected) if selected and read_detail and any(r['id']==selected for r in rows) else None
            return rows,data,detail
        (self.quiet_task if automatic else self.task)(work,self.jobs_loaded)

    def jobs_loaded(self,result):
        rows,data,detail=result; selected=self.selected_job(); tree=self.jobs_tree
        present={r['id'] for r in rows}
        for iid in tree.get_children():
            if iid not in present: tree.delete(iid)
        for row in rows:
            iid=row['id']; values=(row['control']+(' *' if row['locked'] else ''),row['stage'] or 'DONE',f"{row['completed']}/{row['total']}",row['reason']); kw=dict(text=iid[:12]+'…',values=values)
            if tree.exists(iid):
                # Avoid Tcl updates for unchanged rows, preserving selection and scroll.
                if tree.item(iid,'text')!=kw['text'] or tuple(tree.item(iid,'values'))!=values:tree.item(iid,**kw)
            else: tree.insert('','end',iid=iid,**kw)
        if selected and tree.exists(selected) and tree.selection()!=(selected,): tree.selection_set(selected)
        ram=(data['ram_total']-data['ram_available'])/1024**3; total=data['ram_total']/1024**3; disk=data['disk_free']/1024**3
        rss=data['worker'].get('rss'); rss_text=f' · RSS {rss/1024**2:.0f} MiB' if rss is not None else ''
        self.telemetry.set(f"CPU {data['cpu_percent']:.1f}% · {data['allowed']} threads | RAM {ram:.1f}/{total:.1f} GiB | Disk free {disk:.1f} GiB\nWorker: {data['worker']['state']}{rss_text} · {self.t('Evidence mode')}: {data['worker'].get('evidence_mode','—')} · {self.t('No GPU telemetry')}")
        if hasattr(self,'cpu_metric'):
            self.cpu_metric.configure(text=f"{data['cpu_percent']:.0f}%");self.ram_metric.configure(text=f'{ram:.1f} / {total:.1f} GiB')
            devices=data.get('gpu_telemetry');self.gpu_metric.configure(text=(f"{devices[0]['util']:.0f}% · {devices[0]['used_mib']/1024:.1f}/{devices[0]['total_mib']/1024:.1f} GiB" if devices else '—'))
            if devices:self.telemetry.set(self.telemetry.get().replace(self.t('No GPU telemetry'),'NVIDIA · device '+str(devices[0]['index'])+' · device-wide'))
            row=next((r for r in rows if r['id']==selected),None);self.job_progress.configure(maximum=row['total'] if row else 1,value=row['completed'] if row else 0)
        if detail: self.write_text(self.job_text,detail)
        if self.tray_ready:
            from vrs_contract import digest
            waiting=sorted(r['id'] for r in rows if r['stage']=='exception_review' and r['reason']=='REVIEW_PENDING' and r['control']=='BLOCKED')
            self.tray_loaded(tray_controls.snapshot(data['worker'],rows,bool(self.cfg['interpreter']),digest(waiting)))

    def write_text(self,widget,value):
        if widget is getattr(self,'job_text',None):
            self.job_value=value
            if 'receipts' in value:
                receipts=value['receipts'];self.job_progress.configure(maximum=max(1,len(receipts)),value=sum(r['state']=='COMPLETED' for r in receipts.values()))
        widget.configure(state='normal');widget.delete('1.0','end');widget.insert('end',human(value));widget.configure(state='disabled')

    def job_detail(self):
        if self.view!='Jobs' or self.future is not None:return
        run=self.selected_job()
        if run: self.task(lambda:self.api.detail(run),lambda v:self.write_text(self.job_text,v))

    def review_job(self):
        if self.future is None and self.selected_job(): self.run=self.selected_job(); self.show('Review')

    def run_control(self,action):
        run=self.selected_job(); interpreter=self.cfg['interpreter']
        if not run or self.future is not None: return
        if not interpreter: messagebox.showinfo('VRS',self.t('Compute Python'),parent=self.w); return
        if action=='cancel' and not messagebox.askyesno('VRS',self.t('Cancel')+'?',parent=self.w):return
        self.control_request(action.capitalize(),lambda:self.api.control(interpreter,action,run))

    def diagnostics(self): self.task(self.api.diagnostics,lambda v:self.write_text(self.job_text,v))

    def control_request(self,label,fn):
        if self.future is not None:return
        self.control_feedback.set(self.t(label)+' · '+self.t('Request pending'))
        def work():
            try:return True,fn()
            except Exception as exc:return False,str(exc)
        def done(result):
            ok,value=result
            if ok:
                state=value.get('control',value.get('state','UNKNOWN'))
                self.control_feedback.set(self.t(label)+' · '+self.t('Request acknowledged')+' · '+self.t(state))
            else:
                self.control_feedback.set(self.t(label)+' · '+self.t('Request failed'))
                messagebox.showerror('VRS',value,parent=self.w)
            self.load_jobs(automatic=True)
        self.task(work,done)

    def start_worker(self):
        if self.future is not None:return
        interpreter=self.cfg['interpreter']
        if not interpreter: messagebox.showinfo('VRS',self.t('Compute Python'),parent=self.w);return
        self.control_request('Start worker',lambda:self.api.start(interpreter))

    def stop_worker(self): self.control_request('Stop worker',self.api.stop)

    def save_caps(self):
        try: value={k:int(v.get()) for k,v in self.capvars.items()}
        except ValueError: messagebox.showerror('VRS','Invalid number',parent=self.w); return
        self.task(lambda:self.api.save_ops(value),lambda v:self.status.set(self.t('Ceilings apply after worker restart; 0 = default')))

    def page_evidence(self):
        self.title('Evidence',self.t('No automatic accuracy claim')+' · UNADJUDICATED'); bar=ttk.Frame(self.body); bar.pack(fill='x'); self.ev_run=tk.StringVar(value=self.run or ''); self.ev_combo=ttk.Combobox(bar,textvariable=self.ev_run,state='readonly',width=20); self.ev_combo.pack(side='left',fill='x',expand=True); self.ev_combo.bind('<<ComboboxSelected>>',lambda e:self.load_evidence()); ttk.Button(bar,text=self.t('Refresh evidence'),command=self.load_evidence).pack(side='left',padx=5); ttk.Button(bar,text=self.t('Export local preview'),command=self.export).pack(side='left'); self.ev_value=None;ttk.Button(bar,text=self.t('Raw JSON'),command=lambda:self.raw_dialog(self.ev_value)).pack(side='left',padx=5);cards=ttk.Frame(self.body);cards.pack(fill='x',pady=(12,0));self.ev_review=self.metric(cards,self.t('Resolved'));self.ev_compared=self.metric(cards,self.t('Compared regions'));self.ev_unresolved=self.metric(cards,self.t('Unresolved regions'));self.ev_text=tk.Text(self.body,bg=self.p['panel'],fg=self.p['fg'],wrap='word',relief='flat',padx=10,pady=10); self.ev_text.pack(fill='both',expand=True,pady=10); self.ev_text.configure(state='disabled')
        def loaded(rows):
            ids=[r['id'] for r in rows]; self.ev_combo.configure(values=ids)
            if ids and self.ev_run.get() not in ids: self.ev_run.set(ids[0])
            self.load_evidence()
        self.task(self.api.jobs,loaded)

    def load_evidence(self):
        run=self.ev_run.get()
        if run and self.future is None:self.task(lambda:self.api.evidence(run),self.evidence_loaded)

    def evidence_loaded(self,value):
        self.ev_value=value;fraction=review_fraction(value['review']);self.ev_review.configure(text=f'{fraction[0]} / {fraction[1]}' if fraction else '—')
        comparisons=value['comparisons'];self.ev_compared.configure(text=str(sum(x['compared'] for x in comparisons)) if comparisons else '—');self.ev_unresolved.configure(text=str(sum(x['unresolved'] for x in comparisons)) if comparisons else '—');self.write_text(self.ev_text,value)

    def export(self):
        run=self.ev_run.get()
        if run:self.task(lambda:self.api.export_preview(run),lambda v:self.status.set(v))

    def enable_tray(self):
        if self.tray is not None:return
        if os.name!='nt': messagebox.showinfo('VRS','Native tray requires Windows; worker remains independent.',parent=self.w);return
        try:
            import pystray
            im=brand_icon(64)
            def item(label,action):
                return pystray.MenuItem(self.t(label),lambda *_:self.enqueue_tray(action),enabled=lambda _:self.tray_enabled(action))
            menu=pystray.Menu(pystray.MenuItem(self.t('Open'),lambda *_:self.events.put('show'),default=True),pystray.MenuItem(self.t('Review'),lambda *_:self.events.put('review')),pystray.Menu.SEPARATOR,item('Start worker','start'),item('Stop worker','stop'),item('Pause single run','pause'),item('Resume single run','resume'),pystray.Menu.SEPARATOR,pystray.MenuItem(self.t('Mute notifications'),lambda *_:self.events.put('mute'),checked=lambda _:self.tray_muted),pystray.MenuItem(self.t('Exit desktop'),lambda *_:self.events.put('exit')))
            icon=pystray.Icon('VRS',im,'Voynich Research Studio',menu)
            def setup(icon):
                try:icon.visible=True;self.events.put('ready')
                except Exception:self.events.put('tray_failed')
            self.tray=icon; icon.run_detached(setup=setup)
        except Exception:
            self.tray=None; messagebox.showerror('VRS','Optional Windows tray unavailable',parent=self.w)

    def tray_enabled(self,action):
        # Tray callbacks read immutable Python state only; never access Tk.
        return not self.tray_busy and not self.close_pending and self.future is None and tray_controls.target(self.tray_context[2],action) is not None

    def enqueue_tray(self,action):
        context=self.tray_context
        expected=tray_controls.target(context[2],action)
        if expected is not None:self.events.put(('control',action,context[:2],expected))

    def update_tray(self):
        if not self.tray_ready or self.tray is None:return
        v=self.tray_context[2]
        try:
            self.tray.title=('VRS · '+self.t(v.state)+' · '+('—' if v.review is None else str(v.review))+' '+self.t('Review runs')+(' · '+self.tray_feedback if self.tray_feedback else ''))[:120]
            self.tray.update_menu()
        except Exception:self.status.set('Notification area unavailable')

    def tray_loaded(self,view):
        self.tray_context=(str(self.api.root),self.cfg['interpreter'],view)
        self.update_tray(); self.notice_done((view.review,view.review_key))

    def tray_request(self,action,context,expected):
        current=(str(self.api.root),self.cfg['interpreter'])
        if self.future is not None or self.tray_busy or self.close_pending or current!=context:
            self.tray_feedback=self.t('Request failed')+' · '+self.t('Busy');self.update_tray();return
        api=self.api; interpreter=current[1]; self.tray_busy=True
        self.tray_feedback=self.t('Request pending'); self.update_tray()
        def work():
            try:
                result=tray_controls.execute(api,interpreter,action,expected,api.tray_snapshot(bool(interpreter)))
                return True,result
            except Exception:return False,{}
        def done(result):
            self.tray_busy=False; ok,value=result
            state=value.get('control',value.get('state','UNKNOWN'))
            self.tray_feedback=self.t('Request acknowledged')+' · '+self.t(state) if ok else self.t('Request failed')
            self.tray_context=(current[0],current[1],tray_controls.Snapshot())
            self.last_tick=0;self.update_tray()
        # Keep hidden-window controls nonmodal. State is refreshed by tick.
        self.quiet_task(work,done)

    def hide(self):
        if self.tray_ready:self.w.withdraw()
        else:self.status.set(self.t('Enable tray'))

    def notice_done(self,result):
        count,key=result
        if self.tray_ready and not self.tray_muted and self.notices.next(count,key,time.monotonic()) and self.tray.HAS_NOTIFICATION:
            try:self.tray.notify(f'{count} · '+self.t('Review required'),'Voynich Research Studio')
            except Exception: self.status.set('Notification unavailable')

    def tick(self):
        if self.closing:return
        while True:
            try: action=self.events.get_nowait()
            except queue.Empty:break
            if action=='ready':self.tray_ready=True;self.last_tick=0;self.update_tray()
            elif isinstance(action,tuple) and action[0]=='control':self.tray_request(*action[1:])
            elif action=='mute':self.tray_muted=not self.tray_muted;self.update_tray()
            elif action=='tray_failed':
                self.tray_ready=False;self.w.deiconify();self.status.set('Notification area unavailable')
                if self.tray is not None:
                    try:self.tray.stop()
                    except Exception:pass
                    self.tray=None
            elif action in ('show','review') and not self.close_pending:
                self.w.deiconify(); self.w.lift()
                if action=='review':self.request_view('Review')
            elif action=='exit':self.close()
            if self.closing:return
        if self.close_pending:
            if self.future is None:self.close();return
            self.w.after(250,self.tick);return
        if self.pending_view is not None and self.future is None:
            name=self.pending_view;self.pending_view=None;self.request_view(name)
        now=time.monotonic()
        if self.future is None and now-self.last_tick>=3:
            self.last_tick=now
            if self.tray_ready and (self.w.state()=='withdrawn' or self.view!='Jobs'):
                api=self.api; configured=bool(self.cfg['interpreter'])
                def read_tray():
                    try:return api.tray_snapshot(configured)
                    except Exception:return tray_controls.Snapshot()
                self.quiet_task(read_tray,self.tray_loaded)
            elif self.view=='Jobs':self.load_jobs(automatic=True)
        self.w.after(250,self.tick)

    def close(self):
        if self.closing:return
        if self.future is not None:
            self.close_pending=True;self.pending_view=None;self.w.deiconify();self.status.set(self.t('Busy'));return
        self.close_pending=True;self.pending_view=None
        if self.tray is not None:
            try:self.tray.stop()
            except Exception:self.status.set('Tray stop unavailable')
            finally:self.tray=None;self.tray_ready=False
        super().close()


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('root',type=Path); a=p.parse_args(); w=tk.Tk(); Monitor(w,a.root); w.mainloop()


if __name__=='__main__': main()

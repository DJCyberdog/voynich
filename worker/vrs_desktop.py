"""VRS desktop shell: local Review edition, optional separate compute interpreter."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import vrs_dialogs as dialogs
from PIL import ImageTk, Image
from vrs_desktop_api import Desktop
from vrs_build_portable import RELEASE_VERSION as VERSION
from vrs_ui_format import human,review_fraction,brand_icon

PALETTES={
 'dark': dict(bg='#101722',panel='#172231',card='#202e40',line='#3a4b60',fg='#edf3fa',muted='#a9b9cc',accent='#5de2ca',ink='#102822',success='#86d6a4',warning='#f4c278',danger='#ff999d'),
 'light':dict(bg='#edf2f7',panel='#ffffff',card='#e2eaf2',line='#aebdce',fg='#172b3c',muted='#465d73',accent='#096a61',ink='#ffffff',success='#17643d',warning='#875000',danger='#a62938')}
DE={'Home':'Start','Review':'Glyphen-Review','Sources':'Quellen','Settings':'Einstellungen','Refresh':'Aktualisieren','Project':'Projekt','Open workspace':'Workspace öffnen','Local only':'Nur lokal','Ready':'Bereit','No runs yet':'Noch keine Runs','Select run':'Run wählen','Previous':'Zurück','Next':'Weiter','Context':'Kontext','Glyph':'Glyphe','Fit':'Einpassen','References':'Referenzen','Decisions':'Entscheidungen','Save draft':'Entwurf speichern','Submit':'Übernehmen','Reviewer':'Reviewer:in','No catalog':'Kein visueller Katalog','No candidate':'Kein Kandidat','No queue':'Keine offene Warteschlange','Pending':'Offen','Resolved':'Bearbeitet','Deferred':'Zurückgestellt','Inventory':'Inventar','Label':'Zeichen','Disposition':'Zuordnung','Import source':'Quelle importieren','Verify manifest':'Manifest prüfen','Register run':'Run registrieren','Choose file':'Datei wählen','Compute Python':'Compute-Python','Catalog file':'Katalogdatei','Theme':'Design','Language':'Sprache','Apply':'Übernehmen','Overview':'Übersicht','Source management':'Quellenverwaltung','Offline drafts':'Offline-Entwürfe','Worker connected':'Worker konfiguriert','No auto-acceptance claim':'Keine validierte Erkennungsfreigabe','Busy':'Lädt …','Draft saved':'Entwurf gespeichert','Decision saved':'Entscheidung übernommen','Workspace path':'Workspace-Pfad','Reference scheme':'Referenzschema','Sample':'Beispiel','No visual sample':'Kein visuelles Beispiel','Unreviewed proposals':'Unvalidierte Vorschläge','Revision':'Revision','Browse':'Auswählen','No prediction hints':'Keine Modellvorschläge im Review','Manual selection':'Manuelle Auswahl','No automatic publication':'Keine automatische Veröffentlichung','Source role':'Quellentyp','Pinned file':'Gebundene Datei','glyph':'Glyphe','false_positive':'False Positive','compound':'Compound','deferred':'Zurückstellen','mapped':'Zugeordnet','absent':'Nicht im Inventar','unknown':'Unbekannt','unreviewed':'Nicht geprüft','Create manifest':'Manifest erstellen','Build reference catalog':'Referenzkatalog erstellen','Pinned existing local files; optional second transcription':'Vorhandene lokale Dateien; zweite Transkription optional','Reviewed plan JSON':'Geprüfter Plan (JSON)','Preview only (not reviewed)':'Nur Vorschau (nicht geprüft)','No automatic catalog approval':'Keine automatische Freigabe des Katalogs'}

DE.update({'Total runs':'Runs gesamt','Review blocked':'Review blockiert','Review required':'Review erforderlich','Completed runs':'Abgeschlossen','Research runs':'Forschungsläufe','Select a run to inspect':'Run auswählen, um ihn zu prüfen','Status':'Status','Stage':'Phase','Use selected label':'Zeichen übernehmen','Raw JSON':'Original-JSON','No results':'Keine Ergebnisse','Review progress':'Review-Fortschritt','Select reference label':'Referenzzeichen wählen','Technical details':'Technische Details','Reference samples':'Referenzbeispiele','Visual catalog':'Visueller Katalog','Search label':'Zeichen suchen','Assignment scheme':'Zuordnungssystem','Previous sample':'Vorheriges Beispiel','Next sample':'Nächstes Beispiel','Select for review':'Für Review auswählen','No compatible reference':'Keine kompatible Referenz','Page':'Seite','Keyboard help':'Tastaturhilfe','Close':'Schließen','No pending changes':'Keine offenen Änderungen'})

DE.update({'Full page':'Ganze Seite','Page context verified':'Seitenkoordinaten verifiziert','Line/word alignment unknown':'Zeilen-/Wortzuordnung unbekannt'})

class App:
    def __init__(self, window, root):
        self.w=window; self.api=Desktop(root); self.cfg=self.api.settings(); self.pool=ThreadPoolExecutor(max_workers=1); self.future=None; self.closing=False
        self.run=None; self.data=None; self.items=[]; self.offset=0; self.index=0; self.image=None; self.box=None; self.photo=None; self.refphoto=None; self.factor=1.; self.glyph_only=False; self.catalog={}; self.view='Home'; self.maps={}
        self.window_icon=ImageTk.PhotoImage(brand_icon(64),master=self.w);self.w.iconphoto(True,self.window_icon)
        self.w.title('Voynich Research Studio · '+VERSION); self.w.geometry(self.cfg['geometry']); self.w.minsize(1024,650); self.w.protocol('WM_DELETE_WINDOW',self.close)
        self.w.bind('<Control-r>',lambda e:self.refresh()); self.w.bind('<Control-Return>',lambda e:self.submit()); self.w.bind('<Alt-Left>',lambda e:self.move(-1)); self.w.bind('<Alt-Right>',lambda e:self.move(1)); self.w.bind('<Control-plus>',lambda e:self.zoom(1.25)); self.w.bind('<Control-minus>',lambda e:self.zoom(.8));self.w.bind('<F1>',lambda e:self.keyboard_help());self.w.bind('<FocusIn>',self.reveal_review_focus,add='+')
        self.build(); self.show('Home'); self.refresh()

    def t(self,text): return DE.get(text,text) if self.cfg['language']=='de' else text

    def build(self):
        for child in self.w.winfo_children(): child.destroy()
        self.p=PALETTES[self.cfg['theme']]; p=self.p; self.w.configure(bg=p['bg']); s=ttk.Style(self.w); s.theme_use('clam')
        from tkinter import font as tkfont
        family='Segoe UI' if 'Segoe UI' in tkfont.families(self.w) else tkfont.nametofont('TkDefaultFont').actual('family')
        self.family=family; scale=float(self.w.tk.call('tk','scaling')); rowheight=max(30,round(25*scale))
        s.configure('.',font=(family,10),background=p['bg'],foreground=p['fg'],fieldbackground=p['card'],bordercolor=p['line'],troughcolor=p['panel'],lightcolor=p['line'],darkcolor=p['line'])
        for style,background in [('TFrame',p['bg']),('Panel.TFrame',p['panel']),('Card.TFrame',p['card'])]:s.configure(style,background=background)
        s.configure('TLabel',background=p['bg'],foreground=p['fg']);s.configure('Panel.TLabel',background=p['panel']);s.configure('Muted.TLabel',foreground=p['muted'])
        s.configure('Title.TLabel',font=(family,21,'bold'));s.configure('Section.TLabel',font=(family,12,'bold'));s.configure('Metric.TLabel',background=p['card'],foreground=p['fg'],font=(family,22,'bold'));s.configure('MetricCaption.TLabel',background=p['card'],foreground=p['muted'],font=(family,10))
        s.configure('Card.TLabel',background=p['card'],padding=10);s.configure('TButton',background=p['card'],padding=(10,6));s.map('TButton',background=[('active',p['line'])],foreground=[('disabled',p['muted'])])
        s.configure('Nav.TButton',background=p['panel'],anchor='w',padding=(12,7),borderwidth=0);s.map('Nav.TButton',background=[('active',p['card']),('focus',p['line'])])
        s.configure('Accent.TButton',background=p['accent'],foreground=p['ink']);s.map('Accent.TButton',background=[('disabled',p['card']),('active',p['accent'])],foreground=[('disabled',p['muted'])])
        s.configure('NavActive.TButton',background=p['accent'],foreground=p['ink'],anchor='w',padding=(12,7),borderwidth=0);s.map('NavActive.TButton',background=[('active',p['accent']),('focus',p['accent'])])
        s.configure('Treeview',background=p['panel'],fieldbackground=p['panel'],foreground=p['fg'],rowheight=rowheight,borderwidth=0);s.map('Treeview',background=[('selected',p['line'])],foreground=[('selected',p['fg'])]);s.configure('Treeview.Heading',background=p['card'],foreground=p['fg'],font=(family,10,'bold'),padding=(6,7))
        s.configure('TCombobox',padding=4);s.map('TCombobox',fieldbackground=[('readonly',p['card'])],foreground=[('readonly',p['fg'])]);s.configure('Horizontal.TProgressbar',background=p['accent'],troughcolor=p['line'],bordercolor=p['line'])
        self.w.option_add('*TCombobox*Listbox.background',p['card']);self.w.option_add('*TCombobox*Listbox.foreground',p['fg'])
        top=ttk.Frame(self.w,padding=(20,12)); top.pack(fill='x'); ttk.Label(top,text='VRS',font=(family,24,'bold'),foreground=p['accent']).pack(side='left'); ttk.Label(top,text='  VOYNICH RESEARCH STUDIO',font=(family,12,'bold')).pack(side='left'); ttk.Button(top,text='F1',command=self.keyboard_help,width=4).pack(side='right',padx=(12,0));ttk.Label(top,text=VERSION+'  ·  '+self.t('Local only'),style='Muted.TLabel').pack(side='right')
        ttk.Separator(self.w).pack(fill='x'); self.status=tk.StringVar(value=self.t('Ready')); ttk.Label(self.w,textvariable=self.status,style='Card.TLabel',anchor='w').pack(fill='x',side='bottom'); area=ttk.Frame(self.w); area.pack(fill='both',expand=True); nav=ttk.Frame(area,style='Panel.TFrame',padding=12); nav.pack(side='left',fill='y'); ttk.Label(nav,text=self.t('Project').upper(),style='Panel.TLabel').pack(anchor='w',pady=(4,8)); ttk.Label(nav,text=self.api.root.name[:22],style='Panel.TLabel',wraplength=145).pack(anchor='w',pady=(0,14)); ttk.Button(nav,text=self.t('Open workspace'),command=self.switch).pack(fill='x',pady=(0,20)); self.nav={}
        for name in ('Home','Review','Sources','Settings'):
            b=ttk.Button(nav,text=self.t(name),style='Nav.TButton',command=lambda n=name:self.show(n)); b.pack(fill='x',pady=2); self.nav[name]=b
        ttk.Label(nav,text='PRIVATE WORKSPACE',style='Panel.TLabel',foreground=p['muted']).pack(side='bottom',pady=10)
        self.body=ttk.Frame(area,padding=(22,18)); self.body.pack(side='left',fill='both',expand=True)

    def task(self,fn,done):
        if self.future is not None: return
        self.status.set(self.t('Busy')); self.future=self.pool.submit(fn); self.w.after(30,lambda:self.poll(done))

    def poll(self,done):
        if self.closing: return
        if not self.future.done(): self.w.after(30,lambda:self.poll(done)); return
        future=self.future; self.future=None
        try: result=future.result(); self.status.set(self.t('Ready')); done(result)
        except Exception as exc: self.status.set(str(exc)); messagebox.showerror('VRS',str(exc),parent=self.w)

    def show(self,name):
        if self.future is not None: return
        self.view=name
        for n,b in self.nav.items(): b.configure(style='NavActive.TButton' if n==name else 'Nav.TButton')
        for child in self.body.winfo_children(): child.destroy()
        getattr(self,'page_'+name.lower())()

    def reveal_review_focus(self,event):
        canvas=getattr(self,'review_side',None)
        if self.view!='Review' or canvas is None or not canvas.winfo_exists():return
        widget=event.widget
        if not str(widget).startswith(str(canvas)+'.'):return
        bounds=canvas.bbox('all')
        if not bounds:return
        height=max(1,bounds[3]-bounds[1]);top=widget.winfo_rooty()-canvas.winfo_rooty()+canvas.canvasy(0);bottom=top+widget.winfo_height();visible=canvas.canvasy(0)
        if top<visible:canvas.yview_moveto(max(0,top/height))
        elif bottom>visible+canvas.winfo_height():canvas.yview_moveto(max(0,(bottom-canvas.winfo_height())/height))

    def keyboard_help(self):
        if self.cfg['language']=='de':
            text='Tab / Umschalt+Tab  ·  Fokus wechseln\nStrg+R  ·  Aktualisieren\nAlt+Links / Rechts  ·  Kandidat wechseln\nStrg+Plus / Minus  ·  Zoom\nEnter in Referenzliste  ·  Zeichen übernehmen\nStrg+Enter  ·  Entscheidung übernehmen'
        else:text='Tab / Shift+Tab  ·  Move focus\nCtrl+R  ·  Refresh\nAlt+Left / Right  ·  Change candidate\nCtrl+Plus / Minus  ·  Zoom\nEnter in reference list  ·  Assign label\nCtrl+Enter  ·  Submit decision'
        if hasattr(self,'request_view'):text+='\nCtrl+1–7  ·  '+('Arbeitsbereiche' if self.cfg['language']=='de' else 'Workspaces')
        messagebox.showinfo(self.t('Keyboard help'),text,parent=self.w)

    def title(self,name,subtitle):
        ttk.Label(self.body,text=self.t(name),style='Title.TLabel').pack(anchor='w'); ttk.Label(self.body,text=subtitle,style='Muted.TLabel',wraplength=760).pack(anchor='w',pady=(4,15))

    def metric(self,parent,label):
        card=ttk.Frame(parent,style='Card.TFrame',padding=(12,10));card.pack(side='left',fill='both',expand=True,padx=(0,8))
        ttk.Label(card,text=label,style='MetricCaption.TLabel').pack(anchor='w')
        value=ttk.Label(card,text='—',style='Metric.TLabel');value.pack(anchor='w',pady=(3,0));return value

    def page_home(self):
        self.title('Overview',self.t('No automatic publication')+'  ·  '+self.t('Local only'))
        cards=ttk.Frame(self.body);cards.pack(fill='x',pady=(0,14))
        self.homecount=self.metric(cards,self.t('Total runs'));self.homepending=self.metric(cards,self.t('Review blocked'));self.homecomplete=self.metric(cards,self.t('Completed runs'))
        heading=ttk.Frame(self.body);heading.pack(fill='x',pady=(0,6));ttk.Label(heading,text=self.t('Research runs'),style='Section.TLabel').pack(side='left')
        ttk.Button(heading,text=self.t('Refresh'),command=self.refresh).pack(side='right')
        ttk.Label(heading,text=self.t('Worker connected' if self.cfg['interpreter'] else 'Offline drafts'),style='Muted.TLabel').pack(side='right',padx=10)
        footer=ttk.Frame(self.body);footer.pack(side='bottom',fill='x',pady=(8,0));self.homehint=ttk.Label(footer,text=self.t('No runs yet'),style='Muted.TLabel');self.homehint.pack(side='left');self.home_review=ttk.Button(footer,text=self.t('Review'),command=self.open_selected,style='Accent.TButton',width=0);self.home_review.pack(side='right')
        table=ttk.Frame(self.body);table.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(table,columns=('state','stage'),show='tree headings');self.tree.heading('#0',text='Run ID');self.tree.heading('state',text=self.t('Status'));self.tree.heading('stage',text=self.t('Stage'));self.tree.column('#0',width=210);self.tree.column('state',width=110);self.tree.column('stage',width=190)
        sb=ttk.Scrollbar(table,orient='vertical',command=self.tree.yview);sb.pack(side='right',fill='y');self.tree.configure(yscrollcommand=sb.set);self.tree.pack(fill='both',expand=True)
        for state,color in [('COMPLETED','success'),('BLOCKED','warning'),('FAILED','danger'),('CANCELLED','muted')]:self.tree.tag_configure(state,foreground=self.p[color])
        self.tree.bind('<Double-1>',lambda e:self.open_selected())
        self.refresh()

    def refresh(self):
        if self.view=='Home': self.task(self.api.runs,self.fill_runs)
        elif self.view=='Review' and self.run: self.load_review(self.offset)

    def fill_runs(self,rows):
        selected=self.tree.selection();self.tree.delete(*self.tree.get_children())
        self.homecount.configure(text=str(len(rows)));self.homepending.configure(text=str(sum(r['control']=='BLOCKED' and r['stage']=='exception_review' for r in rows)));self.homecomplete.configure(text=str(sum(r['control']=='COMPLETED' for r in rows)))
        for row in rows:self.tree.insert('','end',iid=row['id'],text=row['id'][:16]+'…',values=(row['control'],row['stage'] or 'DONE'),tags=(row['control'],))
        if selected and self.tree.exists(selected[0]):self.tree.selection_set(selected[0])
        self.homehint.configure(text=self.t('Select a run to inspect') if rows else self.t('No runs yet'))

    def open_selected(self):
        sel=self.tree.selection()
        if sel: self.run=sel[0]; self.offset=0; self.show('Review')

    def page_review(self):
        self.title('Review',self.t('No prediction hints')+'  ·  '+self.t('Unreviewed proposals'))
        bar=ttk.Frame(self.body);bar.pack(fill='x',pady=(0,4))
        self.runvar=tk.StringVar(value=self.run or '');self.runbox=ttk.Combobox(bar,textvariable=self.runvar,state='readonly',width=19);self.runbox.pack(side='left');self.runbox.bind('<<ComboboxSelected>>',lambda e:self.choose_run())
        ttk.Button(bar,text=self.t('Previous'),command=lambda:self.move(-1)).pack(side='right');ttk.Button(bar,text=self.t('Next'),command=lambda:self.move(1)).pack(side='right',padx=5);ttk.Button(bar,text=self.t('Refresh'),command=self.refresh).pack(side='right')
        self.counter=ttk.Label(self.body,text='—',style='Muted.TLabel');self.counter.pack(anchor='w',pady=(0,4))
        self.reviewprogress=ttk.Progressbar(self.body,maximum=1,value=0,mode='determinate');self.reviewprogress.pack(fill='x',pady=(0,8))
        panes=ttk.Panedwindow(self.body,orient='horizontal'); panes.pack(fill='both',expand=True); left=ttk.Frame(panes,padding=8,style='Panel.TFrame'); right_shell=ttk.Frame(panes,padding=8,style='Panel.TFrame'); panes.add(left,weight=3); panes.add(right_shell,weight=2)
        def balance(event):
            width=event.width
            if width<550:return
            minimum=min(width-280,max(340,round(250*float(self.w.tk.call('tk','scaling')))))
            if width-panes.sashpos(0)<minimum:panes.sashpos(0,width-minimum)
        panes.bind('<Configure>',balance)
        # Keep decision actions visible while the reference/mapping panel scrolls.
        fixed=ttk.Frame(right_shell,style='Panel.TFrame');fixed.pack(side='bottom',fill='x')
        scrollhost=ttk.Frame(right_shell,style='Panel.TFrame');scrollhost.pack(fill='both',expand=True)
        self.review_side=tk.Canvas(scrollhost,bg=self.p['panel'],highlightthickness=0,width=300);ys=ttk.Scrollbar(scrollhost,orient='vertical',command=self.review_side.yview);ys.pack(side='right',fill='y');self.review_side.configure(yscrollcommand=ys.set);self.review_side.pack(side='left',fill='both',expand=True)
        right=ttk.Frame(self.review_side,style='Panel.TFrame',padding=(0,0,6,0));right_id=self.review_side.create_window(0,0,anchor='nw',window=right)
        right.bind('<Configure>',lambda e:self.review_side.configure(scrollregion=self.review_side.bbox('all')));self.review_side.bind('<Configure>',lambda e:self.review_side.itemconfigure(right_id,width=e.width))
        self.review_side.bind('<MouseWheel>',lambda e:self.review_side.yview_scroll(-1 if e.delta>0 else 1,'units'));self.review_side.bind('<Button-4>',lambda e:self.review_side.yview_scroll(-1,'units'));self.review_side.bind('<Button-5>',lambda e:self.review_side.yview_scroll(1,'units'))
        self.meta=ttk.Label(left,text=self.t('No candidate'),style='Panel.TLabel',wraplength=380); self.meta.pack(anchor='w',pady=5); controls=ttk.Frame(left,style='Panel.TFrame'); controls.pack(fill='x');
        self.zoom_controls=[]
        for label,fn in (('Context',lambda:self.mode(False)),('Glyph',lambda:self.mode(True)),('Fit',self.fit),('−',lambda:self.zoom(.8)),('+',lambda:self.zoom(1.25))):
            button=ttk.Button(controls,text=self.t(label),command=fn,width=0);button.pack(side='left',padx=(0,4));self.zoom_controls.append(button)
        self.page_button=ttk.Button(left,text=self.t('Full page'),command=self.open_page_context); self.page_button.pack(anchor='w',pady=(4,0))
        self.canvas=tk.Canvas(left,bg=self.p['bg'],highlightthickness=1,highlightbackground=self.p['line'],width=320,height=220); self.canvas.pack(fill='both',expand=True,pady=8); self.canvas.bind('<Configure>',lambda e:self.draw()); self.canvas.bind('<ButtonPress-1>',lambda e:self.canvas.scan_mark(e.x,e.y)); self.canvas.bind('<B1-Motion>',lambda e:self.canvas.scan_dragto(e.x,e.y,gain=1)); self.canvas.bind('<MouseWheel>',lambda e:self.zoom(1.15 if e.delta>0 else 1/1.15)); self.canvas.bind('<Button-4>',lambda e:self.zoom(1.15)); self.canvas.bind('<Button-5>',lambda e:self.zoom(1/1.15)); self.canvas.configure(takefocus=True)
        ttk.Label(right,text=self.t('References'),style='Panel.TLabel',font=('TkDefaultFont',12,'bold')).pack(anchor='w'); self.refmeta=ttk.Label(right,text=self.t('No catalog'),style='Panel.TLabel',wraplength=330); self.refmeta.pack(anchor='w',pady=3); rr=ttk.Frame(right,style='Panel.TFrame'); rr.pack(fill='x'); self.scheme=tk.StringVar(); self.schemebox=ttk.Combobox(rr,textvariable=self.scheme,state='readonly',width=10); self.schemebox.pack(side='left',fill='x',expand=True); self.schemebox.bind('<<ComboboxSelected>>',lambda e:self.change_scheme()); self.search=tk.StringVar(); self.searchbox=ttk.Entry(rr,textvariable=self.search,width=8); self.searchbox.pack(side='right',padx=(4,0)); self.search.trace_add('write',lambda *_:self.filter_refs()); self.visual=tk.StringVar(); vr=ttk.Frame(right,style='Panel.TFrame'); vr.pack(fill='x'); ttk.Label(vr,text=self.t('Reference scheme'),style='Panel.TLabel').pack(side='left'); self.visualbox=ttk.Combobox(vr,textvariable=self.visual,state='readonly',width=10); self.visualbox.pack(side='right',fill='x',expand=True,padx=5); self.visualbox.bind('<<ComboboxSelected>>',lambda e:self.visual_changed()); rf=ttk.Frame(right,style='Panel.TFrame'); rf.pack(fill='x'); labelbox=ttk.Frame(rf,style='Panel.TFrame');labelbox.pack(side='left',fill='both',expand=True);self.labels=tk.Listbox(labelbox,height=5,width=10,bg=self.p['card'],fg=self.p['fg'],selectbackground=self.p['line'],selectforeground=self.p['fg'],exportselection=False,highlightthickness=1,highlightcolor=self.p['accent']);labelsbar=ttk.Scrollbar(labelbox,command=self.labels.yview);labelsbar.pack(side='right',fill='y');self.labels.configure(yscrollcommand=labelsbar.set);self.labels.pack(side='left',fill='both',expand=True); self.labels.bind('<<ListboxSelect>>',lambda e:self.sample()); self.labels.bind('<Return>',lambda e:self.assign_reference()); self.samplelabel=ttk.Label(rf,text=self.t('No visual sample'),style='Panel.TLabel',width=12,wraplength=100,anchor='center'); self.samplelabel.pack(side='right',fill='y',padx=4); self.samplemeta=ttk.Label(right,text='',style='Panel.TLabel',wraplength=330); self.samplemeta.pack(fill='x'); sampletools=ttk.Frame(right,style='Panel.TFrame');sampletools.pack(fill='x',pady=(4,0));ttk.Button(sampletools,text='‹',command=lambda:self.next_sample(-1),width=3).pack(side='left');ttk.Button(sampletools,text='›',command=self.next_sample,width=3).pack(side='left',padx=(4,0));ttk.Button(sampletools,text=self.t('Visual catalog'),command=self.visual_catalog,width=0).pack(side='right');ttk.Button(right,text=self.t('Use selected label'),command=self.assign_reference,style='Accent.TButton').pack(fill='x',pady=(4,0)); ttk.Separator(right).pack(fill='x',pady=6)
        ttk.Label(right,text=self.t('Decisions'),style='Panel.TLabel',font=('TkDefaultFont',12,'bold')).pack(anchor='w'); self.mapping_frame=ttk.Frame(right,style='Panel.TFrame');self.mapping_frame.pack(fill='x',pady=(4,8))
        self.kind=tk.StringVar(value='glyph'); self.kindbox=ttk.Combobox(fixed,textvariable=self.kind,state='readonly',values=('glyph','false_positive','compound','deferred')); self.kindbox.pack(fill='x',pady=4); self.kindbox.bind('<<ComboboxSelected>>',lambda e:self.kind_changed()); actions=ttk.Frame(fixed,style='Panel.TFrame'); actions.pack(fill='x'); self.draft_button=ttk.Button(actions,text=self.t('Save draft'),command=lambda:self.save(False),width=0);self.draft_button.pack(side='left',fill='x',expand=True);self.submit_button=ttk.Button(actions,text=self.t('Submit'),style='Accent.TButton',command=self.submit,width=0);self.submit_button.pack(side='left',fill='x',expand=True,padx=(6,0)); self.image=None; self.box=None; self.data=None; self.items=[]; self.maps={}; self.catalog={}; self.task(lambda:(self.api.runs(),self.api.catalog(self.cfg['catalog'])),self.review_init)

    def review_init(self,result):
        rows,self.catalog=result; self.runids={r['id'][:16]:r['id'] for r in rows}; self.runbox.configure(values=list(self.runids));
        if self.run not in self.runids.values(): self.run=next(iter(self.runids.values()),None)
        if self.run: self.runvar.set(self.run[:16]); self.load_review(0)
        else: self.counter.configure(text=self.t('No runs yet'))

    def choose_run(self):
        if self.future is not None:
            self.runvar.set(self.run[:16] if self.run else ''); return
        self.run=self.runids.get(self.runvar.get()); self.load_review(0)

    def load_review(self,offset):
        if not self.run or self.future is not None: return
        run=self.run; self.task(lambda:self.api.review(run,offset),lambda result:self.review_loaded(result,offset))

    def review_loaded(self,result,offset):
        self.data=result; self.items=result['items']; self.offset=offset; self.index=0; snap=result['snapshot']; self.counter.configure(text=self.t('No queue') if snap is None else f"{snap['pending']} {self.t('Pending')}  ·  {snap['resolved']} {self.t('Resolved')}  ·  {snap['deferred']} {self.t('Deferred')}"); fraction=review_fraction(snap);self.reviewprogress.configure(maximum=max(1,fraction[1]) if fraction else 1,value=fraction[0] if fraction else 0); self.render_candidate()

    def render_candidate(self):
        for w in self.mapping_frame.winfo_children(): w.destroy()
        self.maps={}; self.image=None; self.box=None; self.page_image=None; self.page_box=None; self.page_active=False; self.draw(); self.kind.set('glyph'); inv=self.data['inventory'] if self.data else {}; self.schemebox.configure(values=list(inv)); self.scheme.set(next(iter(inv),'')); self.search.set(''); self.change_scheme()
        for name,labels in inv.items():
            row=ttk.Frame(self.mapping_frame,style='Panel.TFrame'); row.pack(fill='x',pady=3); ttk.Label(row,text=name,style='Panel.TLabel').grid(row=0,column=0,columnspan=2,sticky='w'); state=tk.StringVar(value='unreviewed'); label=tk.StringVar(); a=ttk.Combobox(row,textvariable=state,values=('unreviewed','mapped','absent','unknown'),state='readonly',width=11); a.grid(row=1,column=0,sticky='ew',padx=(0,4)); b=ttk.Combobox(row,textvariable=label,values=labels,state='readonly',width=8); b.grid(row=1,column=1,sticky='ew');row.columnconfigure(0,weight=1);row.columnconfigure(1,weight=1); b.bind('<<ComboboxSelected>>',lambda e,v=state:v.set('mapped')); self.maps[name]=(state,label,a,b)
        if not self.items: self.meta.configure(text=self.t('No candidate')); return
        item=self.items[self.index]; self.meta.configure(text=f"PAGE {item['page']}  ·  {self.offset+self.index+1}  ·  {self.t('Revision')} {item['revision']}\n{item['reason']}  ·  {item['region_id'][:24]}"); self.factor=1.; self.glyph_only=False; self.task(lambda:self.api.crop(item),self.crop_loaded)

    def crop_loaded(self,result): self.image,self.box=result; self.draw()
    def open_page_context(self):
        if self.view!='Review' or self.future is not None or not self.items or self.image is None:return
        if self.page_image is not None:self.page_context_loaded((self.page_image,self.page_box));return
        item=self.items[self.index]; self.task(lambda:self.api.page_context(item),self.page_context_loaded)
    def page_context_loaded(self,result):
        self.page_image,self.page_box=result;self.page_active=True;self.glyph_only=False;self.fit()
        self.status.set(self.t('Page context verified')+' · '+self.t('Line/word alignment unknown'))
    def fit(self): self.factor=1.; self.draw(); self.canvas.xview_moveto(0); self.canvas.yview_moveto(0)
    def mode(self,only): self.page_active=False; self.glyph_only=only; self.fit()
    def zoom(self,amount):
        if self.view=='Review' and self.image is not None: self.factor=max(.25,min(8,self.factor*amount)); self.draw()
    def draw(self):
        if not hasattr(self,'canvas') or not self.canvas.winfo_exists(): return
        self.canvas.delete('all')
        if self.image is None: return
        box=self.page_box if getattr(self,'page_active',False) else self.box; im=self.page_image if getattr(self,'page_active',False) else (self.image.crop(self.box) if self.glyph_only else self.image); w=max(1,self.canvas.winfo_width()); h=max(1,self.canvas.winfo_height()); scale=min((w-20)/im.width,(h-20)/im.height)*self.factor; scale=max(.01,min(scale,4096/max(im.size))); iw,ih=max(1,round(im.width*scale)),max(1,round(im.height*scale)); x,y=max(10,(w-iw)//2),max(10,(h-ih)//2); self.photo=ImageTk.PhotoImage(im.resize((iw,ih),Image.Resampling.NEAREST)); self.canvas.create_image(x,y,anchor='nw',image=self.photo)
        if not self.glyph_only: self.canvas.create_rectangle(x+box[0]*iw/im.width,y+box[1]*ih/im.height,x+box[2]*iw/im.width,y+box[3]*ih/im.height,outline='#00bca5',width=2)
        self.canvas.configure(scrollregion=(0,0,max(w,x+iw+10),max(h,y+ih+10)))
    def move(self,delta):
        if self.view!='Review' or self.future is not None or not self.items: return
        n=self.index+delta
        if 0<=n<len(self.items): self.index=n; self.render_candidate()
        elif delta>0 and self.data['next_offset'] is not None: self.load_review(self.data['next_offset'])
        elif delta<0 and self.offset: self.load_review(max(0,self.offset-24))
    def change_scheme(self):
        name=self.scheme.get(); self.visualbox.configure(values=['']+list(self.catalog)); self.visual.set(name if name in self.catalog else ''); self.visual_changed()
    def visual_changed(self):
        name=self.visual.get(); cat=self.catalog.get(name); self.refmeta.configure(text=(cat['source']+' · '+cat['version']+' · '+cat['coverage']+(' · PREVIEW' if cat['preview'] else '')) if cat else self.t('No catalog')+' · '+name); self.filter_refs()
    def filter_refs(self):
        name=self.scheme.get(); self.labels.delete(0,'end'); inv=self.data['inventory'] if self.data else {}; query=self.search.get().casefold()
        labels=self.catalog.get(self.visual.get(),{}).get('entries',{}) if self.visual.get() else inv.get(name,[])
        for label in labels:
            if query in label.casefold(): self.labels.insert('end',label)
        self.samplelabel.configure(image='',text=self.t('No visual sample')); self.samplemeta.configure(text=''); self.refphoto=None; self.sample_refs=[]
    def sample(self):
        if not self.labels.curselection() or self.future is not None: return
        name=self.scheme.get(); label=self.labels.get(self.labels.curselection()[0]); self.sample_refs=self.catalog.get(self.visual.get(),{}).get('entries',{}).get(label,[]); self.sample_index=0; self.render_sample()
    def assign_reference(self):
        if self.view!='Review' or self.future is not None or not self.items or self.kind.get()!='glyph' or not self.labels.curselection():return
        name=self.scheme.get();label=self.labels.get(self.labels.curselection()[0])
        # Browsing is separate from explicit manual assignment; cross-scheme labels remain fenced.
        if name in self.maps and self.visual.get() in ('',name) and label in self.data['inventory'][name]:
            state,var,_,_=self.maps[name];state.set('mapped');var.set(label)
        else:self.status.set(self.t('Select reference label'))
    def next_sample(self,delta=1):
        if getattr(self,'sample_refs',[]) and self.future is None: self.sample_index=(self.sample_index+delta)%len(self.sample_refs); self.render_sample()
    def render_sample(self):
        if not self.sample_refs: self.samplelabel.configure(image='',text=self.t('No visual sample')); self.samplemeta.configure(text=''); return
        ref,source=self.sample_refs[self.sample_index]; self.task(lambda:self.api.reference_image(ref),lambda im:self.sample_loaded(im,source))
    def sample_loaded(self,im,source): self.refphoto=ImageTk.PhotoImage(im); self.samplelabel.configure(image=self.refphoto,text=''); self.samplemeta.configure(text=source+'  ·  '+str(self.sample_index+1)+' / '+str(len(self.sample_refs)))
    def visual_catalog(self):
        # Preview only; selection never writes a review decision.
        if self.view!='Review' or self.future is not None:return
        scheme=self.visual.get();entries=self.catalog.get(scheme,{}).get('entries',{})
        if not entries:self.status.set(self.t('No catalog'));return
        labels=[label for label in entries if self.search.get().casefold() in label.casefold()]
        if not labels:self.status.set(self.t('No results'));return
        dialog=tk.Toplevel(self.w);dialog.title(self.t('Visual catalog')+' · '+scheme);dialog.transient(self.w);dialog.geometry('740x520');dialog.grab_set()
        bar=ttk.Frame(dialog,padding=10);bar.pack(fill='x');caption=ttk.Label(bar,text='—');caption.pack(side='left')
        grid=ttk.Frame(dialog,padding=10);grid.pack(fill='both',expand=True)
        index=[0];photos=[];page_size=12
        def choose(label):
            # Keep modal closed while the existing reference API loads the selected sample.
            if self.future is not None:return
            dialog.destroy()
            if self.visual.get()!=scheme:return
            values=self.labels.get(0,'end')
            if label in values:
                pos=values.index(label);self.labels.selection_clear(0,'end');self.labels.selection_set(pos);self.labels.see(pos);self.sample()
        def show(rows,start):
            if not dialog.winfo_exists():return
            for child in grid.winfo_children():child.destroy()
            photos.clear()
            for n,(label,image) in enumerate(rows):
                card=ttk.Frame(grid,style='Card.TFrame',padding=5);card.grid(row=n//4,column=n%4,sticky='nsew',padx=4,pady=4)
                if image is not None:
                    image.thumbnail((130,78));photo=ImageTk.PhotoImage(image,master=dialog);photos.append(photo)
                    ttk.Button(card,text=label,image=photo,compound='top',command=lambda v=label:choose(v)).pack(fill='both',expand=True)
                else:ttk.Button(card,text=label+' · '+self.t('No visual sample'),command=lambda v=label:choose(v)).pack(fill='both',expand=True)
            for c in range(4):grid.columnconfigure(c,weight=1)
            for rr in range(3):grid.rowconfigure(rr,weight=1)
            caption.configure(text=f"{start+1}–{min(start+page_size,len(labels))} / {len(labels)} · {scheme}")
        def load(delta=0):
            if self.future is not None:return
            start=max(0,min((len(labels)-1)//page_size*page_size,index[0]+delta*page_size));index[0]=start
            def work():
                return [(label,self.api.reference_image(entries[label][0][0]) if entries[label] else None) for label in labels[start:start+page_size]]
            self.task(work,lambda rows:show(rows,start))
        ttk.Button(bar,text=self.t('Previous'),command=lambda:load(-1)).pack(side='right');ttk.Button(bar,text=self.t('Next'),command=lambda:load(1)).pack(side='right',padx=5)
        ttk.Label(dialog,text=self.t('Manual selection')+' · '+self.t('No prediction hints'),style='Muted.TLabel').pack(pady=5)
        load()
    def kind_changed(self):
        for _,_,a,b in self.maps.values(): a.configure(state='readonly' if self.kind.get()=='glyph' else 'disabled'); b.configure(state='readonly' if self.kind.get()=='glyph' else 'disabled')
    def save(self,send):
        if self.view!='Review' or not self.items or self.future is not None: return
        if send and not self.cfg['interpreter']: messagebox.showinfo('VRS',self.t('Compute Python')+' — '+self.t('Settings'),parent=self.w); return
        if send and self.data['control'] not in ('BLOCKED','PAUSED'): messagebox.showerror('VRS','Run not parked for review',parent=self.w); return
        item=self.items[self.index]; snap=self.data['snapshot']; inv=self.data['inventory']; kind=self.kind.get(); maps={n:dict(state=s.get(),label=v.get() if s.get()=='mapped' else None) for n,(s,v,_,_) in self.maps.items()} if kind=='glyph' else {}; reviewer=self.cfg['reviewer']; interpreter=self.cfg['interpreter']
        def work():
            draft=self.api.stage_decision(item,snap,inv,reviewer,kind,maps)
            return self.api.command(interpreter,'decide',draft) if send else draft
        self.task(work,lambda r:self.saved(send,r))
    def saved(self,send,result):
        if send: self.load_review(0)
        else: self.status.set(self.t('Draft saved')+' · '+result)
    def submit(self): self.save(True)

    def page_sources(self):
        self.title('Source management',self.t('Local only')+' · SHA-256'); form=ttk.Frame(self.body); form.pack(fill='x'); self.role=tk.StringVar(value='manuscript'); ttk.Label(form,text=self.t('Source role')).pack(side='left'); ttk.Combobox(form,textvariable=self.role,values=('manuscript','reference_pdf','transcription','json'),state='readonly',width=17).pack(side='left',padx=8); ttk.Button(form,text=self.t('Import source'),command=self.import_source,style='Accent.TButton').pack(side='left'); ttk.Button(form,text=self.t('Sources'),command=lambda:self.task(self.api.sources,self.result)).pack(side='left',padx=5); ttk.Separator(self.body).pack(fill='x',pady=14); f=ttk.Frame(self.body); f.pack(fill='x'); self.manifest=tk.StringVar(); ttk.Entry(f,textvariable=self.manifest).pack(side='left',fill='x',expand=True); ttk.Button(f,text=self.t('Choose file'),command=lambda:self.choose_relative(self.manifest)).pack(side='left',padx=5); actions=ttk.Frame(self.body);actions.pack(fill='x',pady=(5,0));ttk.Button(actions,text=self.t('Verify manifest'),command=lambda:self.check_manifest(False)).pack(side='left'); ttk.Button(actions,text=self.t('Register run'),command=lambda:self.check_manifest(True)).pack(side='left',padx=5); self.output=tk.Text(self.body,bg=self.p['panel'],fg=self.p['fg'],height=12,wrap='word',relief='flat',padx=12,pady=12); self.output.pack(fill='both',expand=True,pady=12); self.output.configure(state='disabled'); self.source_value=None; tools=ttk.Frame(self.body); tools.pack(fill='x'); ttk.Button(tools,text=self.t('Create manifest'),command=self.manifest_dialog).pack(side='left'); ttk.Button(tools,text=self.t('Build reference catalog'),command=self.catalog_dialog).pack(side='left',padx=6); ttk.Button(tools,text=self.t('Offline drafts'),command=self.draft_dialog).pack(side='left');ttk.Button(tools,text=self.t('Raw JSON'),command=lambda:self.raw_dialog(self.source_value)).pack(side='right')
    def result(self,value):
        self.source_value=value;self.output.configure(state='normal');self.output.delete('1.0','end');self.output.insert('end',human(value));self.output.configure(state='disabled')
    def raw_dialog(self,value):
        if value is None:return
        import json
        dialog=tk.Toplevel(self.w);dialog.title(self.t('Raw JSON'));dialog.transient(self.w);dialog.geometry('760x480')
        text=tk.Text(dialog,wrap='word',bg=self.p['panel'],fg=self.p['fg'],padx=12,pady=10);bar=ttk.Scrollbar(dialog,command=text.yview);bar.pack(side='right',fill='y');text.configure(yscrollcommand=bar.set);text.pack(fill='both',expand=True);text.insert('end',json.dumps(value,indent=2,ensure_ascii=False));text.configure(state='disabled')
    def import_source(self):
        if self.future is not None:return
        p=dialogs.choose(filedialog.askopenfilename,parent=self.w,workspace=self.api.root)
        if p: role=self.role.get(); self.task(lambda:self.api.import_source(p,role),self.result)
    def choose_relative(self,var):
        p=dialogs.choose(filedialog.askopenfilename,parent=self.w,workspace=self.api.root,current=var.get())
        if p:
            try: var.set(Path(p).resolve().relative_to(self.api.root).as_posix())
            except ValueError: messagebox.showerror('VRS','Select a file inside the workspace',parent=self.w)
    def check_manifest(self,register):
        if self.future is not None:return
        rel=self.manifest.get(); interp=self.cfg['interpreter']
        def work():
            info=self.api.manifest_info(rel)
            if register: return self.api.command(interp,'register',rel)
            return info
        self.task(work,self.result)

    def manifest_dialog(self):
        if self.future is not None: return
        dialog=tk.Toplevel(self.w); dialog.title(self.t('Create manifest')); dialog.transient(self.w); dialog.grab_set(); fields={}
        for role in ('manuscript','groups','references','model','recognition_policy','transcription 1','transcription 2'):
            row=ttk.Frame(dialog,padding=6); row.pack(fill='x'); ttk.Label(row,text=role,width=20).pack(side='left'); var=tk.StringVar(); fields[role]=var; ttk.Entry(row,textvariable=var,width=46).pack(side='left'); ttk.Button(row,text=self.t('Browse'),command=lambda v=var:self.choose_relative(v)).pack(side='right')
        ttk.Label(dialog,text=self.t('Pinned existing local files; optional second transcription'),wraplength=650).pack(pady=8)
        def create():
            roles={k:fields[k].get() for k in ('manuscript','groups','references','model','recognition_policy')}; trans=[fields[k].get() for k in ('transcription 1','transcription 2') if fields[k].get()]; dialog.destroy()
            self.task(lambda:self.api.make_manifest(roles,trans),lambda value:(self.manifest.set(value['path']),self.result(value)))
        ttk.Button(dialog,text=self.t('Create manifest'),style='Accent.TButton',command=create).pack(pady=8)
    def catalog_dialog(self):
        if self.future is not None:return
        dialog=tk.Toplevel(self.w); dialog.title(self.t('Build reference catalog')); dialog.transient(self.w); dialog.grab_set(); vars=[]
        for name in ('PDF','Reviewed plan JSON'):
            row=ttk.Frame(dialog,padding=6); row.pack(fill='x'); ttk.Label(row,text=self.t(name),width=20).pack(side='left'); var=tk.StringVar(); vars.append(var); ttk.Entry(row,textvariable=var,width=44).pack(side='left'); ttk.Button(row,text=self.t('Browse'),command=lambda v=var:self.choose_relative(v)).pack(side='right')
        preview=tk.BooleanVar(value=True); ttk.Checkbutton(dialog,text=self.t('Preview only (not reviewed)'),variable=preview).pack(anchor='w',padx=8); ttk.Label(dialog,text=self.t('No automatic catalog approval'),wraplength=550).pack(pady=8)
        def build():
            pdf,plan=(v.get() for v in vars); pre=preview.get(); dialog.destroy(); self.task(lambda:self.api.build_catalog(pdf,plan,pre),self.result)
        ttk.Button(dialog,text=self.t('Build reference catalog'),style='Accent.TButton',command=build).pack(pady=8)
    def draft_dialog(self):
        if self.future is not None:return
        def show(rows):
            dialog=tk.Toplevel(self.w); dialog.title(self.t('Offline drafts')); dialog.transient(self.w); dialog.grab_set(); listbox=tk.Listbox(dialog,width=78,height=10); listbox.pack(padx=12,pady=12)
            for r in rows: listbox.insert('end',r['run_id'][:12]+' · '+r['candidate_id'][:12]+' · '+r['kind']+' · r'+str(r['revision']))
            def send():
                if not listbox.curselection():return
                rel=rows[listbox.curselection()[0]]['path']; dialog.destroy(); self.task(lambda:self.api.submit_draft(self.cfg['interpreter'],rel),self.result)
            ttk.Button(dialog,text=self.t('Submit'),command=send,state='normal' if self.cfg['interpreter'] else 'disabled').pack(pady=(0,12))
        self.task(self.api.drafts,show)

    def page_settings(self):
        self.title('Settings',self.t('Workspace path')+' · '+str(self.api.root)); self.fields={}
        for k,label,values in [('project','Project',None),('reviewer','Reviewer',None),('theme','Theme',('dark','light')),('language','Language',('de','en')),('interpreter','Compute Python',None),('catalog','Catalog file',None)]:
            row=ttk.Frame(self.body); row.pack(fill='x',pady=7); ttk.Label(row,text=self.t(label),width=20).pack(side='left'); var=tk.StringVar(value=self.cfg[k]); self.fields[k]=var
            if values: ttk.Combobox(row,textvariable=var,values=values,state='readonly').pack(side='left')
            else: ttk.Entry(row,textvariable=var).pack(side='left',fill='x',expand=True)
            if k=='catalog': ttk.Button(row,text=self.t('Browse'),command=lambda v=var:self.choose_relative(v)).pack(side='right')
            if k=='interpreter': ttk.Button(row,text=self.t('Browse'),command=lambda v=var:v.set(dialogs.choose(filedialog.askopenfilename,parent=self.w,workspace=self.api.root,current=v.get()) or v.get())).pack(side='right')
        ttk.Button(self.body,text=self.t('Apply'),style='Accent.TButton',command=self.apply).pack(anchor='e',pady=12)
    def apply(self):
        if self.future is not None:return
        value={**self.cfg,**{k:v.get() for k,v in self.fields.items()},'geometry':f'{self.w.winfo_width()}x{self.w.winfo_height()}'}
        def work():
            self.api.catalog(value['catalog']); return self.api.save_settings(value)
        self.task(work,self.settings_done)
    def settings_done(self,value): self.cfg=value; self.build(); self.show('Settings')
    def switch(self):
        if self.future is not None:return
        p=dialogs.choose(filedialog.askdirectory,parent=self.w,workspace=self.api.root,mustexist=True)
        if p:
            try: api=Desktop(p); cfg=api.settings()
            except Exception as exc: messagebox.showerror('VRS',str(exc),parent=self.w); return
            self.api,self.cfg=api,cfg; self.run=None; self.build(); self.show('Home')
    def close(self):
        if self.future is not None: self.status.set(self.t('Busy')); return
        self.closing=True; self.pool.shutdown(wait=False,cancel_futures=True)
        try: self.api.save_settings({**self.cfg,'geometry':f'{self.w.winfo_width()}x{self.w.winfo_height()}'})
        except Exception: pass
        self.w.destroy()


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('root',type=Path); a=p.parse_args(); w=tk.Tk(); App(w,a.root); w.mainloop()

if __name__=='__main__': main()

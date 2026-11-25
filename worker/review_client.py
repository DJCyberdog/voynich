"""v0.8 local glyph review client. No network, training or automatic publication."""
import argparse
import copy
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import active_review as ar
import review_groups
import worker as w

VERSION = '0.8.0'
PAGE_SIZE = 18
BG, PANEL, BORDER, FG, MUTED, ACCENT = '#101820', '#192630', '#344650', '#e8eef2', '#a6b8c4', '#55cbb8'


class Session:
    def __init__(self, manifest, predictions, references, output, reviewer):
        self.manifest, self.predictions, self.references = map(Path, (manifest,predictions,references))
        self.output = Path(output)
        self.schemes, rows, self.data = ar.open_session(manifest,predictions,references,output,reviewer)
        self.rows = review_groups.ordered(manifest, rows)
        self.by_id = {r['id']:r for r in self.rows}
        self.digest = w.sha(self.output) if self.output.exists() else None
        self.deferred = set()

    def pending(self):
        return [r for r in self.rows if r['id'] not in self.data['decisions']]

    def next(self):
        rows = self.pending()
        return next((r for r in rows if r['id'] not in self.deferred), None)

    def restart_deferred(self):
        self.deferred.clear()

    def defer(self, rid):
        w.require(rid in self.by_id and rid not in self.data['decisions'], 'Nur offene Kandidaten zurückstellen')
        self.deferred.add(rid)

    def save(self, rid, kind, mapping, note='', proposed_boxes=None):
        w.require(rid in self.by_id,'Unbekannter Kandidat')
        d = dict(kind=kind,mapping=copy.deepcopy(mapping) if kind=='glyph' else ar.empty_mapping(self.schemes),note=note)
        ar.validate_decision(d,self.schemes)
        if proposed_boxes:
            w.require(kind=='compound','Rahmenkorrekturen nur als Segmentierungsfall speichern')
            row=self.by_id[rid]
            with Image.open(w.within(self.manifest.parent,row['record']['file'])) as im: width,height=im.size
            w.require(len(proposed_boxes)<=32 and all(isinstance(b,list) and len(b)==4 and all(type(x) is int for x in b) and 0<=b[0]<b[2]<=width and 0<=b[1]<b[3]<=height for b in proposed_boxes), 'Ungültige Korrekturrahmen')
            w.require(len(set(map(tuple,proposed_boxes)))==len(proposed_boxes),'Doppelte Korrekturrahmen')
            d['proposed_boxes']=copy.deepcopy(proposed_boxes)
        current=w.sha(self.output) if self.output.exists() else None
        w.require(current==self.digest,'Review-Datei extern geändert. Sitzung neu öffnen.')
        updated=copy.deepcopy(self.data)
        if rid in updated['decisions']:
            updated.setdefault('revisions',[]).append(dict(candidate_id=rid,previous=updated['decisions'][rid]))
        updated['decisions'][rid]=d
        w.write(self.output,updated)
        self.data=updated; self.digest=w.sha(self.output); self.deferred.discard(rid)

    def counts(self):
        done=len(self.data['decisions']); return len(self.rows),done,len(self.pending()),len(self.deferred)


def search_entries(scheme, query):
    q=query.casefold().strip()
    return [(label,samples) for label,samples in scheme['entries'].items() if q in label.casefold()]


def preferred(schemes):
    keys=list(schemes)
    eva=next((k for k in keys if k=='eva-original'),next((k for k in keys if 'eva' in k.lower()),keys[0]))
    sta=next((k for k in keys if k.lower()=='sta1'),next((k for k in keys if 'sta' in k.lower() and k!=eva),next((k for k in keys if k!=eva),eva)))
    return eva,sta


def configure(root):
    root.configure(bg=BG); style=ttk.Style(root); style.theme_use('clam')
    style.configure('.',background=BG,foreground=FG,font=('Segoe UI',10),fieldbackground=PANEL)
    style.configure('TFrame',background=BG); style.configure('Panel.TFrame',background=PANEL)
    style.configure('TLabel',background=BG,foreground=FG); style.configure('Muted.TLabel',foreground=MUTED)
    style.configure('Title.TLabel',font=('Segoe UI',19,'bold')); style.configure('Stat.TLabel',font=('Segoe UI',16,'bold'),foreground=ACCENT)
    style.configure('TButton',background=PANEL,foreground=FG,bordercolor=BORDER,padding=(7,5)); style.map('TButton',background=[('active',BORDER)])
    style.configure('Accent.TButton',background=ACCENT,foreground=BG); style.map('Accent.TButton',background=[('active','#85dece')])
    style.configure('TCombobox',fieldbackground=PANEL,foreground=FG,background=PANEL,arrowcolor=FG); style.map('TCombobox',fieldbackground=[('readonly',PANEL)],foreground=[('readonly',FG)])
    style.configure('TEntry',fieldbackground=PANEL,foreground=FG,insertcolor=FG)
    style.configure('Horizontal.TProgressbar',background=ACCENT,troughcolor=PANEL)
    root.option_add('*TCombobox*Listbox.background',PANEL); root.option_add('*TCombobox*Listbox.foreground',FG)


class ReferencePane:
    def __init__(self, parent, client, key):
        self.client=client; self.page=0; self.photos=[]; self.buttons={}
        self.frame=ttk.Frame(parent,padding=6); self.frame.columnconfigure(0,weight=1)
        self.key=tk.StringVar(value=key); self.query=tk.StringVar(); self.selected=tk.StringVar()
        names=list(client.session.schemes)
        self.combo=ttk.Combobox(self.frame,textvariable=self.key,values=names,state='readonly'); self.combo.grid(row=0,column=0,sticky='ew')
        self.combo.bind('<<ComboboxSelected>>',lambda _:self.reset())
        self.info=ttk.Label(self.frame,style='Muted.TLabel',wraplength=560); self.info.grid(row=1,column=0,sticky='ew',pady=4)
        self.search=ttk.Entry(self.frame,textvariable=self.query); self.search.grid(row=2,column=0,sticky='ew'); self.query.trace_add('write',lambda *_:self.reset())
        self.grid=ttk.Frame(self.frame); self.grid.grid(row=3,column=0,sticky='nsew',pady=4)
        for c in range(6): self.grid.columnconfigure(c,weight=1)
        nav=ttk.Frame(self.frame); nav.grid(row=4,column=0,sticky='ew')
        ttk.Button(nav,text='‹',command=lambda:self.move(-1)).pack(side='left'); self.counter=ttk.Label(nav); self.counter.pack(side='left',expand=True); ttk.Button(nav,text='›',command=lambda:self.move(1)).pack(side='right')
        ttk.Label(self.frame,textvariable=self.selected,wraplength=420).grid(row=5,column=0,sticky='ew',pady=4)
        bar=ttk.Frame(self.frame); bar.grid(row=6,column=0,sticky='ew')
        ttk.Button(bar,text='Nicht im Inventar',command=lambda:client.select(self.key.get(),'not_in_inventory')).pack(side='left')
        ttk.Button(bar,text='Unbestimmbar',command=lambda:client.select(self.key.get(),'uncertain')).pack(side='right')
        ttk.Button(self.frame,text='Alle Bildvarianten / Quellen',command=self.details).grid(row=7,column=0,sticky='ew',pady=3)
        self.refresh()

    def reset(self): self.page=0; self.refresh()
    def move(self,n): self.page=max(0,min(self.page+n,self.pages-1)); self.refresh()
    def refresh(self):
        s=self.client.session.schemes[self.key.get()]; entries=search_entries(s,self.query.get())
        self.pages=max(1,(len(entries)+PAGE_SIZE-1)//PAGE_SIZE); self.page=min(self.page,self.pages-1)
        self.info.configure(text=f'{s["name"]} · {s["version"]} | {len(entries)} Treffer\n{s["coverage"]}')
        for child in self.grid.winfo_children(): child.destroy()
        self.photos=[]; self.buttons={}
        for i,(label,samples) in enumerate(entries[self.page*PAGE_SIZE:(self.page+1)*PAGE_SIZE]):
            with Image.open(samples[0][0]) as im:
                im=im.convert('RGB'); im.thumbnail((60,32)); photo=ImageTk.PhotoImage(im)
            self.photos.append(photo)
            b=ttk.Button(self.grid,text=label,image=photo,compound='top',width=6,command=lambda l=label:self.client.select(self.key.get(),'mapped',l)); b.grid(row=i//6,column=i%6,sticky='nsew',padx=1,pady=1); self.buttons[label]=b
        self.counter.configure(text=f'Seite {self.page+1}/{self.pages} · Suche nach Code')
        self.sync()

    def sync(self):
        m=self.client.mapping.get(self.key.get(),{'state':'unreviewed','label':None})
        self.selected.set('Auswahl: '+(m['label'] if m['state']=='mapped' else {'unreviewed':'offen','not_in_inventory':'nicht im geladenen Inventar','uncertain':'unbestimmbar'}[m['state']]))
        for k,b in self.buttons.items(): b.configure(style='Accent.TButton' if m['label']==k else 'TButton')

    def details(self):
        s=self.client.session.schemes[self.key.get()]; m=self.client.mapping[self.key.get()]
        if m['state']!='mapped': return
        top=tk.Toplevel(self.frame); top.title(f'{s["name"]} – {m["label"]}'); top.configure(bg=BG); top.geometry('740x560')
        ttk.Label(top,text=s['source'],wraplength=690).pack(padx=8,pady=6)
        cv=tk.Canvas(top,bg=BG,highlightthickness=0); cv.pack(side='left',fill='both',expand=True); sb=ttk.Scrollbar(top,command=cv.yview); sb.pack(side='right',fill='y'); cv.configure(yscrollcommand=sb.set)
        f=ttk.Frame(cv); cv.create_window((0,0),window=f,anchor='nw'); f.bind('<Configure>',lambda _:cv.configure(scrollregion=cv.bbox('all'))); top.photos=[]
        for path,source in s['entries'][m['label']]:
            with Image.open(path) as im:
                im=im.convert('RGB'); im.thumbnail((300,150)); ph=ImageTk.PhotoImage(im)
            top.photos.append(ph); ttk.Label(f,image=ph).pack(pady=4); ttk.Label(f,text=source,wraplength=660).pack()


class Client:
    def __init__(self,root,session):
        self.root=root; self.session=session; self.mapping=ar.empty_mapping(session.schemes); self.row=None; self.proposed=[]; self.drag=None; self.geometry=None; self.photos=[]
        configure(root); root.title('Voynich · Glyph Review 0.8'); root.geometry('1320x940'); root.minsize(1160,920)
        top=ttk.Frame(root,padding=(14,9)); top.pack(fill='x')
        ttk.Label(top,text='VOYNICH / GLYPH REVIEW',style='Title.TLabel').pack(side='left'); self.stats=ttk.Label(top,style='Stat.TLabel'); self.stats.pack(side='right')
        self.progress=ttk.Progressbar(root,mode='determinate'); self.progress.pack(fill='x',padx=14)
        head=ttk.Frame(root,padding=(14,5)); head.pack(fill='x'); self.header=ttk.Label(head); self.header.pack(side='left'); ttk.Button(head,text='Geprüften Kandidaten bearbeiten',command=self.last).pack(side='right')
        stage=ttk.Frame(root,padding=(14,0)); stage.pack(fill='x'); self.context=tk.Canvas(stage,width=790,height=128,bg=PANEL,highlightthickness=0); self.context.pack(side='left',fill='x',expand=True)
        self.zoom=tk.Label(stage,bg=PANEL); self.zoom.pack(side='right',padx=(8,0)); self.context.bind('<ButtonPress-1>',self.press); self.context.bind('<ButtonRelease-1>',self.release)
        controls=ttk.Frame(root,padding=(14,3)); controls.pack(fill='x'); ttk.Label(controls,text='Rahmen zeichnen = Korrekturvorschlag, keine automatische Zuordnung.',style='Muted.TLabel').pack(side='left'); ttk.Button(controls,text='Rahmen zurücksetzen',command=self.clear_boxes).pack(side='right')
        main=ttk.Frame(root,padding=(8,0)); main.pack(fill='both',expand=True); main.columnconfigure((0,1),weight=1,uniform='ref')
        self.panes=[]
        for i,k in enumerate(preferred(session.schemes)):
            p=ReferencePane(main,self,k); p.frame.grid(row=0,column=i,sticky='nsew'); self.panes.append(p)
        self.summary=ttk.Label(root,wraplength=1180,style='Muted.TLabel'); self.summary.pack(fill='x',padx=14,side='bottom',before=main)
        bottom=ttk.Frame(root,padding=(14,6)); bottom.pack(fill='x',side='bottom',before=self.summary); self.note=tk.Text(bottom,height=1,bg=PANEL,fg=FG,insertbackground=FG,wrap='word',relief='flat'); self.note.pack(fill='x'); self.status=ttk.Label(bottom,style='Muted.TLabel'); self.status.pack(fill='x',pady=3)
        bar=ttk.Frame(bottom); bar.pack(fill='x'); self.actions={}
        for label,action,style in [('Speichern · Ctrl+Enter',lambda:self.save('glyph'),'Accent.TButton'),('Rest unbestimmbar',self.rest,'TButton'),('In keinem Inventar',self.absent,'TButton'),('False Positive · F2',lambda:self.save('false_positive'),'TButton'),('Segmentierung · F3',lambda:self.save('compound'),'TButton'),('Später · F4',self.defer,'TButton'),('Unbestimmbar · F5',lambda:self.save('uncertain'),'TButton')]:
            b=ttk.Button(bar,text=label,command=action,style=style); i=len(self.actions); b.grid(row=i//4,column=i%4,padx=2,pady=1,sticky='ew'); bar.columnconfigure(i%4,weight=1); self.actions[label]=b
        for key,fn in [('<Control-Return>',lambda:self.save('glyph')),('<F2>',lambda:self.save('false_positive')),('<F3>',lambda:self.save('compound')),('<F4>',self.defer),('<F5>',lambda:self.save('uncertain')),('<Control-f>',lambda:self.panes[0].search.focus_set())]: root.bind(key,lambda e,f=fn:(f(),'break')[1])
        self.show(session.next())

    def sync(self):
        for p in self.panes: p.sync()
        self.summary.configure(text=' | '.join(f'{k}: {v["label"] or {"unreviewed":"offen","not_in_inventory":"nicht enthalten","uncertain":"?"}.get(v["state"],"")}' for k,v in self.mapping.items()))

    def select(self,key,state,label=None):
        if self.row is None:return
        self.mapping[key]=dict(state=state,label=label); self.sync()
    def rest(self):
        if self.row is None:return
        for k,v in self.mapping.items():
            if v['state']=='unreviewed': self.mapping[k]=dict(state='uncertain',label=None)
        self.sync()
    def absent(self):
        if self.row is None:return
        self.mapping=ar.empty_mapping(self.session.schemes,'not_in_inventory'); self.sync(); self.status.configure(text='Alle geladenen Inventare als nicht enthalten markiert. Zum Speichern bestätigen.')
    def show(self,row):
        self.row=row; self.mapping=ar.empty_mapping(self.session.schemes); self.proposed=[]; self.note.delete('1.0','end'); self.drag=None
        total,done,pending,deferred=self.session.counts(); self.stats.configure(text=f'{pending} offen  ·  {done}/{total} geprüft'); self.progress.configure(maximum=max(1,total),value=done)
        if row is None:
            self.header.configure(text='Keine offenen Kandidaten' if not pending else f'{pending} zurückgestellt – F4 startet nächste Runde'); self.context.delete('all'); self.zoom.configure(image=''); self.geometry=None
        else:
            d=self.session.data['decisions'].get(row['id']); self.header.configure(text=f'PDF-Seite {row["record"]["page"]}  /  {row["region_id"]}  /  Gruppe {row["visual_group"]} ({row["group_size"]})'+('  ·  Korrektur einer gespeicherten Entscheidung' if d else ''))
            if d: self.mapping=copy.deepcopy(d['mapping']); self.note.insert('1.0',d['note']); self.proposed=copy.deepcopy(d.get('proposed_boxes',[]))
            self.draw()
        self.sync()
    def draw(self):
        if self.row is None:return
        row=self.row; self.context.delete('all')
        with Image.open(w.within(self.session.manifest.parent,row['record']['file'])) as im:
            im=im.convert('RGB'); crop=im.crop(row['box']); width,height=im.size; scale=min(790/width,128/height,10); ox=0; oy=(128-height*scale)/2
            ph=ImageTk.PhotoImage(im.resize((max(1,round(width*scale)),max(1,round(height*scale))))); self.context.image=ph; self.context.create_image(ox,oy,image=ph,anchor='nw')
            self.geometry=(width,height,scale,ox,oy)
            for box,color in [(row['box'],'#e9a64c')]+[(b,ACCENT) for b in self.proposed]:
                x0,y0,x1,y1=box; self.context.create_rectangle(ox+x0*scale,oy+y0*scale,ox+x1*scale,oy+y1*scale,outline=color,width=2)
            s=min(280/crop.width,128/crop.height,12); ph2=ImageTk.PhotoImage(crop.resize((max(1,round(crop.width*s)),max(1,round(crop.height*s))))); self.zoom.image=ph2; self.zoom.configure(image=ph2)
    def press(self,e): self.drag=(e.x,e.y) if self.geometry else None
    def release(self,e):
        if self.drag is None or self.geometry is None:return
        width,height,scale,ox,oy=self.geometry
        def point(x,y):return max(0,min(width,round((x-ox)/scale))),max(0,min(height,round((y-oy)/scale)))
        a,b=point(*self.drag),point(e.x,e.y); self.drag=None; box=[min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])]
        if box[0]<box[2] and box[1]<box[3] and box not in self.proposed and len(self.proposed)<32: self.proposed.append(box); self.draw(); self.status.configure(text='Korrekturrahmen vorgeschlagen. Mit Segmentierung (F3) speichern.')
    def clear_boxes(self): self.proposed=[]; self.draw()
    def save(self,kind):
        if self.row is None:return
        try:
            if self.proposed and kind!='compound': raise ValueError('Korrekturrahmen mit F3 speichern oder zurücksetzen.')
            self.session.save(self.row['id'],kind,self.mapping,self.note.get('1.0','end-1c'),self.proposed)
        except (ValueError,OSError) as e: self.status.configure(text=str(e)); return
        self.status.configure(text='Gespeichert · lokal'); self.show(self.session.next())
    def defer(self):
        if self.row is None: self.session.restart_deferred()
        elif self.row['id'] not in self.session.data['decisions']: self.session.defer(self.row['id'])
        self.status.configure(text='Zurückgestellt, keine Entscheidung gespeichert'); self.show(self.session.next())
    def last(self):
        if not self.session.data['decisions']:return
        rows=[r for r in self.session.rows if r['id'] in self.session.data['decisions']]
        top=tk.Toplevel(self.root); top.title('Geprüften Kandidaten auswählen'); top.geometry('740x380'); top.configure(bg=BG)
        frame=ttk.Frame(top); frame.pack(fill='both',expand=True,padx=8,pady=8)
        listing=tk.Listbox(frame,bg=PANEL,fg=FG,selectbackground=BORDER,exportselection=False); listing.pack(side='left',fill='both',expand=True)
        sb=ttk.Scrollbar(frame,command=listing.yview); sb.pack(side='right',fill='y'); listing.configure(yscrollcommand=sb.set)
        for r in rows: listing.insert('end',f'Seite {r["record"]["page"]} · {r["region_id"]} · {r["box"]} · {self.session.data["decisions"][r["id"]]["kind"]}')
        def choose(event=None):
            if listing.curselection(): self.show(rows[listing.curselection()[0]]); top.destroy()
        listing.bind('<Double-Button-1>',choose); ttk.Button(top,text='Bearbeiten',command=choose).pack(pady=4)


def launch(manifest=None,predictions=None,references=None,output=None,reviewer=None):
    root=tk.Tk(); root.withdraw()
    try:
        if not all((manifest,predictions,references,output,reviewer)):
            root.deiconify(); configure(root); root.title('Voynich · Review öffnen'); root.geometry('720x340')
            initial=dict(manifest=manifest,predictions=predictions,references=references,output=output,reviewer=reviewer)
            fields={}; labels={'manifest':'Crop-Manifest','predictions':'Glyphen-Predictions','references':'Referenzkatalog','output':'Review-Datei (lokal)','reviewer':'Reviewer-ID'}
            for i,(k,label) in enumerate(labels.items()):
                ttk.Label(root,text=label).grid(row=i,column=0,padx=10,pady=7,sticky='w'); var=tk.StringVar(value=initial[k] or ''); fields[k]=var; ttk.Entry(root,textvariable=var,width=55).grid(row=i,column=1,sticky='ew')
                if k!='reviewer':
                    def choose(key=k):
                        f=(filedialog.asksaveasfilename if key=='output' else filedialog.askopenfilename)(parent=root,filetypes=[('JSON','*.json')]); fields[key].set(f) if f else None
                    ttk.Button(root,text='…',command=choose).grid(row=i,column=2,padx=8)
            def start():
                try: s=Session(**{k:v.get() for k,v in fields.items()})
                except Exception as e: messagebox.showerror('Review nicht geöffnet',str(e),parent=root); return
                for child in root.winfo_children(): child.destroy()
                Client(root,s)
            ttk.Button(root,text='Review öffnen',style='Accent.TButton',command=start).grid(row=5,column=1,pady=12); root.columnconfigure(1,weight=1)
        else: Client(root,Session(manifest,predictions,references,output,reviewer)); root.deiconify()
        root.mainloop()
    finally:
        try: root.destroy()
        except tk.TclError: pass


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('manifest','predictions','references','output','reviewer'): p.add_argument('--'+key)
    launch(**vars(p.parse_args()))


if __name__=='__main__':main()

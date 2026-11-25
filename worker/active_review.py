"""Local multi-convention uncertainty review; never trains or publishes automatically."""
import argparse
import hashlib
import json
from pathlib import Path
import worker as w

VERSION = '0.5.1'
STATES = ('unreviewed', 'mapped', 'not_in_inventory', 'uncertain')
KINDS = ('glyph', 'compound', 'false_positive', 'uncertain')


def catalog(path):
    from PIL import Image
    root = Path(path).parent; obj = w.read(path); schemes = obj['schemes']
    w.require(obj['schema'] == 1 and isinstance(schemes,list) and 1 <= len(schemes) <= 12, 'Invalid reference catalog')
    result = {}
    for s in schemes:
        key = s['id']
        w.require(isinstance(key,str) and key and key not in result and all(isinstance(s[k],str) and s[k].strip() for k in ('name','version','source')), 'Invalid scheme provenance')
        entries = {}
        for e in s['entries']:
            label = e['label']; samples = e['samples']
            w.require(isinstance(label,str) and label and label not in entries and 1 <= len(samples) <= 8, 'Invalid reference entry')
            images = []
            for sample in samples:
                f = w.within(root,sample['file'])
                w.require(not Path(sample['file']).is_absolute() and w.sha(f)==sample['sha256'] and isinstance(sample['source'],str) and sample['source'].strip(), 'Reference image provenance mismatch')
                with Image.open(f) as im:
                    im.verify()
                images.append((f,sample['source']))
            entries[label] = images
        w.require(1 <= len(entries) <= 1024,'Empty or oversized inventory')
        result[key] = dict(name=s['name'],version=s['version'],source=s['source'],coverage=s.get('coverage','coverage not established'),entries=entries)
    return result


def queue(manifest, predictions):
    from PIL import Image
    m=w.dataset(manifest); pred=w.read(predictions)
    w.require(pred['manifest_sha256']==w.sha(manifest),'Prediction manifest mismatch')
    records={r['id']:r for r in m['regions']}; seen=set(); rows=[]
    for r in pred['rows']:
        rid=r['region_id']; b=r['box']; w.require(rid in records,'Unknown region')
        with Image.open(w.within(Path(manifest).parent,records[rid]['file'])) as im: width,height=im.size
        w.require(isinstance(b,list) and len(b)==4 and all(type(x) is int for x in b) and 0<=b[0]<b[2]<=width and 0<=b[1]<b[3]<=height,'Invalid candidate box')
        key=hashlib.sha256(json.dumps([rid,b],separators=(',',':')).encode()).hexdigest()
        w.require(key not in seen,'Duplicate candidate'); seen.add(key)
        if r['predicted']=='unknown': rows.append(dict(id=key,region_id=rid,box=b,record=records[rid]))
    return rows


def validate_decision(decision, schemes):
    w.require(decision['kind'] in KINDS and isinstance(decision['note'],str) and len(decision['note'])<=2000,'Invalid review decision')
    mapping=decision['mapping']; w.require(set(mapping)==set(schemes),'Review every loaded convention explicitly')
    for key,v in mapping.items():
        w.require(v['state'] in STATES,'Invalid mapping state')
        if v['state']=='mapped': w.require(v['label'] in schemes[key]['entries'],'Unknown reference label')
        else: w.require(v['label'] is None,'Non-mapping cannot have a label')
    if decision['kind']!='glyph': w.require(all(v['state']=='unreviewed' for v in mapping.values()),'Non-glyph decision must not assert mappings')
    else: w.require(all(v['state']!='unreviewed' for v in mapping.values()),'Mark each convention mapped, absent or uncertain')
    return decision


def empty_mapping(schemes, state='unreviewed'):
    return {k:dict(state=state,label=None) for k in schemes}


def open_session(manifest,predictions,references,output,reviewer):
    schemes=catalog(references); rows=queue(manifest,predictions)
    w.require(isinstance(reviewer,str) and reviewer.strip(),'Reviewer required')
    binding=dict(version=VERSION,manifest_sha256=w.sha(manifest),predictions_sha256=w.sha(predictions),catalog_sha256=w.sha(references),reviewer=reviewer)
    out=Path(output); data=w.read(out) if out.exists() else dict(binding=binding,decisions={})
    w.require(data['binding']==binding,'Review provenance mismatch')
    w.require(set(data['decisions'])<={r['id'] for r in rows},'Unknown saved candidate')
    for d in data['decisions'].values(): validate_decision(d,schemes)
    return schemes,rows,data


def review(manifest,predictions,references,output,reviewer):
    import tkinter as tk
    from tkinter import ttk
    from PIL import Image,ImageTk,ImageDraw
    schemes,rows,data=open_session(manifest,predictions,references,output,reviewer)
    root=tk.Tk(); root.title('Voynich | Multi-convention review'); root.geometry('1200x800')
    header=ttk.Label(root); header.pack(pady=4)
    context=ttk.Label(root); context.pack(); zoom=ttk.Label(root); zoom.pack()
    outer=ttk.Frame(root); outer.pack(fill='both',expand=True)
    strip=tk.Canvas(outer,height=300); strip.pack(side='top',fill='both',expand=True)
    h=ttk.Scrollbar(outer,orient='horizontal',command=strip.xview); h.pack(fill='x'); strip.configure(xscrollcommand=h.set)
    columns=ttk.Frame(strip); strip.create_window((0,0),window=columns,anchor='nw'); columns.bind('<Configure>',lambda e:strip.configure(scrollregion=strip.bbox('all')))
    mapping={}; displays={}; thumbs=[]
    def select(key,state,label=None):
        mapping[key]=dict(state=state,label=label); displays[key].set(label if state=='mapped' else state)
    for i,(key,s) in enumerate(schemes.items()):
        panel=ttk.LabelFrame(columns,text=f'{s["name"]} · {s["version"]}',padding=5); panel.grid(row=0,column=i,sticky='n',padx=4)
        ttk.Label(panel,text=s['source']+' | '+s['coverage'],wraplength=330).pack()
        displays[key]=tk.StringVar(); ttk.Label(panel,textvariable=displays[key]).pack()
        ttk.Button(panel,text='Nicht im geladenen Inventar',command=lambda k=key:select(k,'not_in_inventory')).pack(fill='x')
        ttk.Button(panel,text='Nicht bestimmbar',command=lambda k=key:select(k,'uncertain')).pack(fill='x')
        area=ttk.Frame(panel); area.pack(); cv=tk.Canvas(area,width=330,height=260); cv.pack(side='left')
        sb=ttk.Scrollbar(area,orient='vertical',command=cv.yview); sb.pack(side='right',fill='y'); cv.configure(yscrollcommand=sb.set)
        grid=ttk.Frame(cv); cv.create_window((0,0),window=grid,anchor='nw'); grid.bind('<Configure>',lambda e,c=cv:c.configure(scrollregion=c.bbox('all')))
        for j,(label,samples) in enumerate(s['entries'].items()):
            cell=ttk.Frame(grid,padding=3); cell.grid(row=j//3,column=j%3,sticky='n')
            for f,source in samples:
                with Image.open(f) as im:
                    im=im.convert('RGB'); im.thumbnail((95,56)); photo=ImageTk.PhotoImage(im)
                thumbs.append(photo); ttk.Button(cell,image=photo,command=lambda k=key,l=label:select(k,'mapped',l)).pack(); ttk.Label(cell,text=source,wraplength=95).pack()
            ttk.Button(cell,text=label,command=lambda k=key,l=label:select(k,'mapped',l)).pack(fill='x')
    note=tk.Text(root,height=2); note.pack(fill='x',padx=8)
    status=ttk.Label(root); status.pack(); bar=ttk.Frame(root); bar.pack(pady=5)
    from review_groups import ordered
    position=[0]; pending=[r for r in ordered(manifest,rows) if r['id'] not in data['decisions']]
    def show():
        note.delete('1.0','end'); mapping.clear(); mapping.update(empty_mapping(schemes))
        for k in schemes: displays[k].set('unreviewed')
        if position[0]>=len(pending):
            header.configure(text=f'Fertig: {len(data["decisions"])}/{len(rows)}'); context.configure(image=''); zoom.configure(image=''); return
        r=pending[position[0]]; record=r['record']
        with Image.open(w.within(Path(manifest).parent,record['file'])) as im:
            im=im.convert('RGB'); crop=im.crop(r['box']); ImageDraw.Draw(im).rectangle(r['box'],outline='red',width=2)
            im.thumbnail((1000,100)); scale=min(280/crop.width,100/crop.height); crop=crop.resize((max(1,round(crop.width*scale)),max(1,round(crop.height*scale))))
            context.image=ImageTk.PhotoImage(im); zoom.image=ImageTk.PhotoImage(crop)
        context.configure(image=context.image); zoom.configure(image=zoom.image)
        header.configure(text=f'{len(data["decisions"])}/{len(rows)} erledigt | Seite {record["page"]} · {r["region_id"]} · {r["box"]} | Gruppe {r["visual_group"]} ({r["group_size"]})')
    def save(kind):
        if position[0]>=len(pending): return
        d=dict(kind=kind,mapping=dict(mapping) if kind=='glyph' else empty_mapping(schemes),note=note.get('1.0','end-1c'))
        try: validate_decision(d,schemes)
        except ValueError as exc: status.configure(text=str(exc)); return
        data['decisions'][pending[position[0]]['id']]=d; w.write(output,data); position[0]+=1; status.configure(text='Gespeichert'); show()
    def absent_all():
        for key in schemes: select(key,'not_in_inventory')
    for label,action in [('In keinem geladenen Inventar',absent_all),('Zuordnungen speichern',lambda:save('glyph')),('False Positive',lambda:save('false_positive')),('Ligatur / Segmentierungsfehler',lambda:save('compound')),('Unbestimmbar',lambda:save('uncertain'))]:
        ttk.Button(bar,text=label,command=action).pack(side='left',padx=3)
    show(); root.mainloop()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('manifest','predictions','references','output','reviewer'): p.add_argument(k)
    review(**vars(p.parse_args()))


if __name__=='__main__': main()

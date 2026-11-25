"""Local Tk editor for glyph review boxes; no predicted labels are shown."""
import argparse
from pathlib import Path
import glyphs as g
import worker as w


def review(manifest, alphabet, output, reviewer):
    import tkinter as tk
    from tkinter import ttk
    from PIL import Image, ImageTk
    m=w.dataset(manifest); labels=g.inventory(alphabet)['labels']+[g.UNKNOWN]
    output=Path(output); items=m['regions']; sizes={}
    for r in items:
        with Image.open(w.within(Path(manifest).parent,r['file'])) as im: sizes[r['id']]=im.size
    if not output.exists(): g.propose(manifest,output,reviewer)
    data=g.checked_review(output,manifest,sizes,labels[:-1])
    w.require(data['reviewer']==reviewer,'Reviewer output belongs to someone else')
    root=tk.Tk(); root.title('Voynich | Glyph review'); info=ttk.Label(root); info.pack(pady=6)
    canvas=tk.Canvas(root,width=900,height=400,background='white'); canvas.pack()
    panel=ttk.Frame(root); panel.pack(fill='x',padx=8,pady=4)
    listing=tk.Listbox(panel,height=6,exportselection=False); listing.pack(side='left',fill='both',expand=True)
    controls=ttk.Frame(panel); controls.pack(side='right')
    label=tk.StringVar(value=g.UNKNOWN); selector=ttk.Combobox(controls,textvariable=label,values=labels,state='readonly'); selector.pack(fill='x')
    status=ttk.Label(root); status.pack(pady=4)
    index=next((i for i,r in enumerate(items) if data['regions'][r['id']]['status']=='unreviewed'),0)
    state={'index':index,'selected':None,'scale':1.,'origin':(0,0),'start':None,'photo':None}
    def current(): return data['regions'][items[state['index']]['id']]
    def save(): w.write(output,data)
    def redraw():
        r=items[state['index']]; row=current(); width,height=sizes[r['id']]
        with Image.open(w.within(Path(manifest).parent,r['file'])) as im:
            scale=min(900/width,400/height,6.); im=im.convert('RGB').resize((max(1,round(width*scale)),max(1,round(height*scale))))
        ox=(900-im.width)//2; oy=(400-im.height)//2; state.update(scale=scale,origin=(ox,oy),photo=ImageTk.PhotoImage(im))
        canvas.delete('all'); canvas.create_image(ox,oy,anchor='nw',image=state['photo'])
        listing.delete(0,'end')
        for i,glyph in enumerate(row['glyphs']):
            x0,y0,x1,y1=glyph['box']; coords=(ox+x0*scale,oy+y0*scale,ox+x1*scale,oy+y1*scale)
            canvas.create_rectangle(*coords,outline='#e05020' if i==state['selected'] else '#007a9a',width=2)
            listing.insert('end',f'{i+1}: {glyph["label"]} {glyph["box"]}')
        sel=state['selected']
        if sel is not None and sel<len(row['glyphs']): listing.selection_set(sel); label.set(row['glyphs'][sel]['label'])
        else: state['selected']=None; label.set(g.UNKNOWN)
        info.configure(text=f'{state["index"]+1}/{len(items)}  |  {r["id"]}  |  {row["status"]}')
    def edit(): current()['status']='unreviewed'; save(); redraw()
    def select(event=None):
        if listing.curselection(): state['selected']=listing.curselection()[0]; redraw()
    def move(delta):
        state.update(index=max(0,min(len(items)-1,state['index']+delta)),selected=None,start=None); redraw()
    def remove():
        if state['selected'] is not None:
            del current()['glyphs'][state['selected']]; state['selected']=None; edit()
    def set_label():
        if state['selected'] is not None:
            current()['glyphs'][state['selected']]['label']=label.get(); edit()
    def mark(value):
        row=current()
        if value=='single_line':
            glyphs=sorted(row['glyphs'],key=lambda x:x['box'][0])
            if not glyphs or any(a['box'][2]>b['box'][0] for a,b in zip(glyphs,glyphs[1:])):
                status.configure(text='Empty or overlapping boxes: correct or mark uncertain'); return
            row['glyphs']=glyphs
        row['status']=value; state['selected']=None; save(); redraw(); status.configure(text='Saved')
    def press(event): state['start']=(event.x,event.y)
    def release(event):
        start=state['start']; state['start']=None
        if start is None: return
        width,height=sizes[items[state['index']]['id']]; ox,oy=state['origin']; scale=state['scale']
        def point(x,y): return max(0,min(width,round((x-ox)/scale))),max(0,min(height,round((y-oy)/scale)))
        x,y=point(*start); xx,yy=point(event.x,event.y)
        box=[min(x,xx),min(y,yy),max(x,xx),max(y,yy)]
        if box[0]==box[2] or box[1]==box[3]: return
        row=current(); selected=state['selected']
        if any(i!=selected and a['box']==box for i,a in enumerate(row['glyphs'])): status.configure(text='Duplicate box'); return
        if selected is None: row['glyphs'].append(dict(box=box,label=g.UNKNOWN)); state['selected']=len(row['glyphs'])-1
        else: row['glyphs'][selected]=dict(box=box,label=g.UNKNOWN)
        edit()
    listing.bind('<ButtonRelease-1>',select); listing.bind('<KeyRelease-Up>',select); listing.bind('<KeyRelease-Down>',select)
    canvas.bind('<ButtonPress-1>',press); canvas.bind('<ButtonRelease-1>',release)
    for title,command in [('Apply label',set_label),('Delete box',remove),('New box',lambda:(state.update(selected=None),redraw()))]: ttk.Button(controls,text=title,command=command).pack(fill='x')
    nav=ttk.Frame(root); nav.pack(pady=6)
    for title,command in [('Previous',lambda:move(-1)),('Next',lambda:move(1)),('Accept line',lambda:mark('single_line')),('Reject',lambda:mark('reject')),('Uncertain',lambda:mark('uncertain'))]: ttk.Button(nav,text=title,command=command).pack(side='left')
    status.configure(text='Drag to draw/replace a selected box; New box adds another. Edited boxes reset to unknown.')
    redraw(); root.mainloop()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('manifest','alphabet','output','reviewer'): p.add_argument(k)
    review(**vars(p.parse_args()))


if __name__=='__main__': main()

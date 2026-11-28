"""Isolated, synthetic RC2-04 framework comparator. Not a VRS runtime or scientific test."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import math
import platform
import statistics
import time
from pathlib import Path

START = time.perf_counter()
from PIL import Image, ImageDraw
import psutil

SIZE = (1800, 2400)
BOX = (710, 1050, 749, 1110)
REGION = (290, 780, 1520, 1580)
ZONES = [(320, y, 1490, y+65) for y in range(810, 1500, 100)]
LABELS = [f"Fixture {i:04d}" for i in range(2000)]
SIZES = [(1024,650),(1440,900),(1920,1080)]
COLORS = {'dark':('#101722','#202e40','#edf3fa'), 'light':('#edf2f7','#ffffff','#172b3c')}


def fixture():
    im=Image.new('RGB',SIZE,'#d6c49b');d=ImageDraw.Draw(im)
    for y in range(100,2300,100):
        for x in range(100,1700,72):
            d.arc((x,y,x+31,y+55),20,320,fill='#66553a',width=3)
            d.line((x+20,y+9,x+20,y+60),fill='#66553a',width=3)
    return im


def summary(samples):
    ordered=sorted(samples)
    return dict(n=len(ordered),p50_ms=round(statistics.median(ordered),3),
                p95_ms=round(ordered[math.ceil(.95*len(ordered))-1],3),max_ms=round(ordered[-1],3))


class TkWindow:
    def __init__(self,im):
        import tkinter as tk
        from tkinter import ttk
        from PIL import ImageTk
        self.tk=tk;self.ttk=ttk;self.ImageTk=ImageTk;self.im=im
        self.w=tk.Tk();self.w.title('VRS framework experiment | Tk | synthetic')
        self.theme_name='dark';self.factor=1.;self.zones=True;self.index=0
        toolbar=ttk.Frame(self.w);toolbar.pack(fill='x')
        for label,fn in [('Fit',self.fit),('Zoom +',lambda:self.zoom(1.25)),('Zoom -',lambda:self.zoom(.8)),('Locate',self.locate),('Zones',self.toggle),('Theme',self.theme),('Next',self.next)]:
            ttk.Button(toolbar,text=label,command=fn).pack(side='left')
        self.pane=ttk.Panedwindow(self.w,orient='horizontal');self.pane.pack(fill='both',expand=True)
        left=ttk.Frame(self.pane);right=ttk.Frame(self.pane);self.pane.add(left,weight=3);self.pane.add(right,weight=1)
        self.canvas=tk.Canvas(left,highlightthickness=0);self.canvas.pack(fill='both',expand=True)
        self.list=tk.Listbox(right,exportselection=False);self.list.pack(fill='both',expand=True)
        for label in LABELS:self.list.insert('end',label)
        self.list.selection_set(0)
        self.canvas.bind('<Configure>',lambda e:self.draw())
        self.canvas.bind('<ButtonPress-1>',lambda e:self.canvas.scan_mark(e.x,e.y))
        self.canvas.bind('<B1-Motion>',lambda e:self.canvas.scan_dragto(e.x,e.y,gain=1))
        self.canvas.bind('<MouseWheel>',lambda e:self.zoom(1.25 if e.delta>0 else .8))
        self.canvas.bind('<Button-4>',lambda e:self.zoom(1.25));self.canvas.bind('<Button-5>',lambda e:self.zoom(.8))
        self.w.geometry('1024x650');self.palette();self.flush();self.fit()
    def flush(self):self.w.update_idletasks();self.w.update()
    def palette(self):
        bg,panel,fg=COLORS[self.theme_name];style=self.ttk.Style(self.w);style.theme_use('clam')
        style.configure('.',background=bg,foreground=fg);self.canvas.configure(bg=bg);self.list.configure(bg=panel,fg=fg)
    def theme(self):
        self.theme_name='light' if self.theme_name=='dark' else 'dark';self.palette()
    def draw(self):
        w,h=max(1,self.canvas.winfo_width()),max(1,self.canvas.winfo_height())
        scale=max(.01,min(w/SIZE[0],h/SIZE[1])*self.factor)
        scale=min(scale,4096/max(SIZE));iw,ih=max(1,round(SIZE[0]*scale)),max(1,round(SIZE[1]*scale))
        self.geom=(max(0,(w-iw)//2),max(0,(h-ih)//2),iw,ih);x,y,_,_=self.geom
        self.canvas.delete('all');self.photo=self.ImageTk.PhotoImage(self.im.resize((iw,ih),Image.Resampling.NEAREST))
        self.canvas.create_image(x,y,image=self.photo,anchor='nw')
        for b,color,dash in [(REGION,'#477de8',(6,3)),(BOX,'#00bca5',None)]+([(b,'#ff9f20',(3,3)) for b in ZONES] if self.zones else []):
            self.canvas.create_rectangle(x+b[0]*iw/SIZE[0],y+b[1]*ih/SIZE[1],x+b[2]*iw/SIZE[0],y+b[3]*ih/SIZE[1],outline=color,dash=dash,width=2)
        self.extent=(max(w,x+iw),max(h,y+ih));self.canvas.configure(scrollregion=(0,0,*self.extent))
    def fit(self):
        self.factor=1.;self.draw();self.canvas.xview_moveto(0);self.canvas.yview_moveto(0)
    def zoom(self,f):
        self.factor=max(.5,min(4,self.factor*f));self.draw()
    def locate(self):
        self.factor=3.;self.draw()
        x,y,iw,ih=self.geom;w,h=self.canvas.winfo_width(),self.canvas.winfo_height()
        cx=x+(BOX[0]+BOX[2])*iw/(2*SIZE[0]);cy=y+(BOX[1]+BOX[3])*ih/(2*SIZE[1])
        self.canvas.xview_moveto(max(0,cx-w/2)/self.extent[0]);self.canvas.yview_moveto(max(0,cy-h/2)/self.extent[1])
    def toggle(self):self.zones=not self.zones;self.draw()
    def next(self):
        self.index=(self.index+1)%len(LABELS);self.list.selection_clear(0,'end');self.list.selection_set(self.index);self.list.see(self.index)
    def resize(self,w,h):self.w.geometry(f'{w}x{h}');self.flush();self.fit()
    def dimensions(self):return [self.w.winfo_width(),self.w.winfo_height(),self.canvas.winfo_width(),self.canvas.winfo_height()]
    def check(self):
        self.flush();x,y,iw,ih=self.geom
        coords=[x+BOX[0]*iw/SIZE[0],y+BOX[1]*ih/SIZE[1],x+BOX[2]*iw/SIZE[0],y+BOX[3]*ih/SIZE[1]]
        # Actual candidate rectangle is the third canvas item: image, region, candidate.
        actual=self.canvas.coords(self.canvas.find_all()[2])
        assert all(abs(a-b)<1e-6 for a,b in zip(coords,actual))
        assert self.list.curselection()==(self.index,)
    def capture(self,path):
        from PIL import ImageGrab
        self.flush();x,y=self.w.winfo_rootx(),self.w.winfo_rooty()
        ImageGrab.grab(bbox=(x,y,x+self.w.winfo_width(),y+self.w.winfo_height())).save(path)
    def close(self):self.w.destroy()
    def loop(self):self.w.mainloop()


class QtWindow:
    def __init__(self,im):
        from PySide6 import QtCore as C,QtGui as G,QtWidgets as W
        self.C=C;self.G=G;self.W=W;self.app=W.QApplication([])
        self.w=W.QMainWindow();self.w.setWindowTitle('VRS framework experiment | Qt | synthetic')
        self.theme_name='dark';self.factor=1.;self.zones=True;self.index=0
        toolbar=self.w.addToolBar('Context')
        for label,fn in [('Fit',self.fit),('Zoom +',lambda:self.zoom(1.25)),('Zoom -',lambda:self.zoom(.8)),('Locate',self.locate),('Zones',self.toggle),('Theme',self.theme),('Next',self.next)]:
            action=toolbar.addAction(label);action.triggered.connect(lambda checked=False,fn=fn:fn())
        scene=W.QGraphicsScene();self.scene=scene
        pix=G.QImage(im.tobytes(),SIZE[0],SIZE[1],SIZE[0]*3,G.QImage.Format.Format_RGB888).copy()
        self.image_item=scene.addPixmap(G.QPixmap.fromImage(pix))
        scene.setSceneRect(0,0,*SIZE)
        def rect(b,color,dashed=False):
            pen=G.QPen(G.QColor(color));pen.setWidth(2);pen.setCosmetic(True)
            if dashed:pen.setStyle(C.Qt.PenStyle.DashLine)
            return scene.addRect(b[0],b[1],b[2]-b[0],b[3]-b[1],pen)
        self.region=rect(REGION,'#477de8',True);self.candidate=rect(BOX,'#00bca5')
        self.zone_items=[rect(b,'#ff9f20',True) for b in ZONES]
        owner=self
        class View(W.QGraphicsView):
            def wheelEvent(self,event):
                owner.zoom(1.25 if event.angleDelta().y()>0 else .8);event.accept()
        self.view=View(scene);self.view.setDragMode(W.QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setTransformationAnchor(W.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.list=W.QListView();self.model=C.QStringListModel(LABELS,self.list);self.list.setModel(self.model)
        self.list.setUniformItemSizes(True);self.list.setCurrentIndex(self.model.index(0,0))
        splitter=W.QSplitter();splitter.addWidget(self.view);splitter.addWidget(self.list);splitter.setStretchFactor(0,3);splitter.setStretchFactor(1,1)
        self.w.setCentralWidget(splitter);self.w.resize(1024,650);self.palette();self.w.show();self.flush();self.fit()
    def flush(self):self.app.processEvents();self.view.viewport().repaint();self.app.processEvents()
    def palette(self):
        bg,panel,fg=COLORS[self.theme_name]
        self.w.setStyleSheet(f'QMainWindow,QToolBar {{ background:{bg}; color:{fg}; }} QListView,QGraphicsView {{ background:{panel}; color:{fg}; }} QToolButton {{ color:{fg}; }}')
    def theme(self):self.theme_name='light' if self.theme_name=='dark' else 'dark';self.palette()
    def fit(self):
        self.factor=1.;self.view.fitInView(self.scene.sceneRect(),self.C.Qt.AspectRatioMode.KeepAspectRatio)
    def zoom(self,f):
        new=max(.5,min(4,self.factor*f));self.view.scale(new/self.factor,new/self.factor);self.factor=new
    def locate(self):
        self.fit();self.zoom(3.);self.view.centerOn((BOX[0]+BOX[2])/2,(BOX[1]+BOX[3])/2)
    def toggle(self):
        self.zones=not self.zones
        for item in self.zone_items:item.setVisible(self.zones)
    def next(self):
        self.index=(self.index+1)%len(LABELS);i=self.model.index(self.index,0);self.list.setCurrentIndex(i);self.list.scrollTo(i)
    def resize(self,w,h):self.w.resize(w,h);self.flush();self.fit()
    def dimensions(self):return [self.w.width(),self.w.height(),self.view.viewport().width(),self.view.viewport().height()]
    def check(self):
        self.flush();r=self.candidate.rect()
        assert (r.x(),r.y(),r.right(),r.bottom())==BOX
        p=self.view.mapFromScene(self.C.QPointF(BOX[0],BOX[1]));q=self.view.mapToScene(p)
        scale=self.view.transform().m11()
        assert abs(q.x()-BOX[0])*scale<=1 and abs(q.y()-BOX[1])*scale<=1
        assert self.list.currentIndex().row()==self.index
        assert all(i.isVisible()==self.zones for i in self.zone_items)
    def capture(self,path):
        self.flush();assert self.w.grab().save(str(path),'PNG')
    def close(self):self.w.close();self.app.quit()
    def loop(self):self.app.exec()


def installed_size():
    result={}
    for name in ('PySide6-Essentials','shiboken6'):
        try:
            dist=metadata.distribution(name)
            result[name]=dict(version=dist.version,bytes=sum(p.stat().st_size for f in (dist.files or []) if (p:=dist.locate_file(f)).is_file()))
        except metadata.PackageNotFoundError:pass
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('framework',choices=('tk','qt'));p.add_argument('--output',type=Path);p.add_argument('--interactive',action='store_true');args=p.parse_args()
    im=fixture();window=(TkWindow if args.framework=='tk' else QtWindow)(im)
    initial_ms=(time.perf_counter()-START)*1000;proc=psutil.Process()
    initial_rss=proc.memory_info().rss
    if args.interactive:window.loop();return
    if args.output is None:p.error('--output is required for measurements')
    args.output.mkdir(parents=True,exist_ok=True)
    report=dict(framework=args.framework,platform=platform.platform(),python=platform.python_version(),fixture_sha256=hashlib.sha256(im.tobytes()).hexdigest(),image_size=SIZE,labels=len(LABELS),initial_ms=round(initial_ms,3),initial_rss_bytes=initial_rss,measurements={},geometry='PASS',installed_qt=installed_size() if args.framework=='qt' else {})
    observed=[initial_rss]
    try:
        for w,h in SIZES:
            window.resize(w,h);window.flush();window.check();results={'actual_window_and_canvas_px':window.dimensions()}
            def zoom_pair():
                window.zoom(1.25);window.flush();window.zoom(.8)
            operations={'theme':window.theme,'zoom_pair':zoom_pair,'next_reference':window.next,'zone_toggle':window.toggle,'locate':window.locate}
            for name,fn in operations.items():
                window.fit();window.flush()
                for _ in range(3):fn();window.flush()
                samples=[]
                for _ in range(30):
                    start=time.perf_counter();fn();window.flush();samples.append((time.perf_counter()-start)*1000)
                    observed.append(proc.memory_info().rss)
                window.check();results[name]=summary(samples)
            report['measurements'][f'{w}x{h}']=results
            window.fit();window.flush()
            # Capture only synthetic pixels, no VRS root or private data is read.
            if (w,h)==SIZES[0]:
                try:window.capture(args.output/f'{args.framework}-synthetic.png');report['capture']='PASS'
                except (OSError,AssertionError) as exc:report['capture']='UNAVAILABLE: '+type(exc).__name__
        report['sampled_peak_rss_bytes']=max(observed)
        report['limitations']='Synchronous callback plus event processing; not input-to-compositor latency. Matched synthetic widgets, not production VRS. Requested viewport sizes may be constrained by hosted desktop. No DPI/worker-load/native-owner claim.'
        (args.output/f'{args.framework}.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report),flush=True)
    finally:window.close()


if __name__=='__main__':main()

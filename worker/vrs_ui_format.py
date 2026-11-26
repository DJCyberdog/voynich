"""Presentation-only helpers; never modify evidence, infer scores or invoke compute."""
import json
import math
import os
import subprocess
from pathlib import Path

def human(value):
    """Readable structured details; original JSON remains available separately."""
    lines=[]
    def walk(v,depth=0,key=None):
        pad='  '*depth; label=key.replace('_',' ') if key else None
        if isinstance(v,dict):
            if label:lines.append(pad+label.upper());depth+=1
            if not v:lines.append('  '*depth+'—')
            for k,x in v.items():walk(x,depth,str(k))
        elif isinstance(v,list):
            if label:lines.append(pad+label.upper());depth+=1
            if not v:lines.append('  '*depth+'—')
            for i,x in enumerate(v,1):walk(x,depth,str(i))
        else:lines.append(pad+((label+':  ') if label else '')+('—' if v is None else str(v)))
    walk(value)
    return '\n'.join(lines)

def parse_gpu(text):
    rows=[]
    for line in text.splitlines():
        parts=[p.strip() for p in line.split(',')]
        if len(parts)!=4:raise ValueError('Unexpected telemetry fields')
        index,util,used,total=map(float,parts)
        if not all(math.isfinite(x) for x in (index,util,used,total)) or not index.is_integer() or index<0 or not 0<=util<=100 or not 0<=used<=total or total<=0:raise ValueError('Invalid GPU telemetry')
        rows.append(dict(index=int(index),util=util,used_mib=used,total_mib=total))
    if not rows or len(rows)>32 or len({r['index'] for r in rows})!=len(rows):raise ValueError('Invalid GPU inventory')
    return rows

def gpu_telemetry():
    """Optional NVIDIA device-wide measurements, no ML import and no fallback guess."""
    if os.name=='nt':
        paths=[Path(r'C:\Windows\System32\nvidia-smi.exe'),Path(r'C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe')]
    else:paths=[Path('/usr/bin/nvidia-smi'),Path('/usr/local/bin/nvidia-smi')]
    exe=next((p for p in paths if p.is_file() and not p.is_symlink()),None)
    if exe is None:return None
    try:
        out=subprocess.run([str(exe),'--query-gpu=index,utilization.gpu,memory.used,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,encoding='utf-8',errors='strict',check=True,timeout=2,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0) if os.name=='nt' else 0)
        return parse_gpu(out.stdout)
    except (OSError,ValueError,subprocess.SubprocessError):return None

def review_fraction(snapshot):
    if snapshot is None:return None
    counts=[snapshot[k] for k in ('pending','resolved','deferred')]
    if any(type(x) is not int or x<0 for x in counts):raise ValueError('Invalid review denominator')
    return counts[1],sum(counts)

def brand_icon(size=64):
    # Local deterministic V monogram; no downloaded font, asset or native dependency.
    from PIL import Image,ImageDraw
    if type(size) is not int or not 16<=size<=256:raise ValueError('Invalid icon size')
    im=Image.new('RGBA',(256,256),(0,0,0,0));d=ImageDraw.Draw(im)
    d.rounded_rectangle((4,4,252,252),radius=52,fill='#172231',outline='#3a4b60',width=5)
    d.polygon([(46,59),(85,59),(128,173),(171,59),(210,59),(146,210),(110,210)],fill='#5de2ca')
    d.line((190,175,212,175),fill='#86d6a4',width=7)
    return im.resize((size,size),Image.Resampling.LANCZOS)

def log_line(row):
    extra=' · '.join(f"{k}: {v}" for k,v in row.items() if k not in ('utc','level','module','code','schema'))
    return f"{row['utc']}  |  {row['level']}  |  {row['module']}  |  {row['code']}"+('  ·  '+extra if extra else '')

"""RC2-02d external archives: static intake and provisional positive-mask pilot."""
import ast
import collections
import hashlib
import io
import json
import re
import sys
import tarfile
import zipfile
from pathlib import Path

import fitz
import numpy as np
import pandas as pd
from PIL import Image, ImageFilter

PINS = (
    '1e79c1ebcce4aa18a8fa5ad83743e9204eb1b08ea52627264bc08bf036485ba4',
    'd0b9bf0b7b12f2a62848a83b0c0127555a6d0f0e4b20728249f2d51c1908b02e',
    'd095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c',
)

def require(ok, message):
    if not ok:
        raise ValueError(message)

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def table(sql, name):
    m = re.search(r'^COPY '+re.escape(name)+r' \((.*?)\) FROM stdin;\n(.*?)\n\\\.', sql, re.M|re.S)
    require(m is not None, 'missing table '+name)
    return pd.DataFrame([line.split('\t') for line in m[2].splitlines()], columns=m[1].split(', '))

def votes(im):
    def adaptive(a, method):
        p = 15
        x = np.pad(a.astype(np.float64), p, mode='edge')
        def mean(y):
            s = np.pad(y.cumsum(0).cumsum(1), ((1,0),(1,0)))
            return (s[31:,31:]-s[:-31,31:]-s[31:,:-31]+s[:-31,:-31])/961
        m = mean(x)
        sd = np.sqrt(np.maximum(0, mean(x*x)-m*m))
        if method == 'sauvola':
            t = m*(1+.25*(sd/128-1))
        else:
            r = sd.max()
            if r <= 1e-9:
                return np.zeros(a.shape, bool)
            t = m+.25*(sd/r-1)*(m-float(a.min()))
        return a<t
    def norm(a):
        bg = np.asarray(Image.fromarray(a).filter(ImageFilter.GaussianBlur(16)), dtype=float)
        return np.clip(np.rint(255*a.astype(float)/np.maximum(bg,1)),0,255).astype(np.uint8)
    g = np.asarray(im.convert('L')); n = norm(g)
    return np.sum([adaptive(g,'sauvola'),adaptive(g,'wolf'),adaptive(n,'sauvola'),adaptive(n,'wolf'),adaptive(norm(np.asarray(im.getchannel('R'))),'sauvola'),adaptive(norm(np.asarray(im.getchannel('B'))),'sauvola')],axis=0,dtype=np.uint16)

def main():
    archetype, glyphs, pdf, review = map(Path, sys.argv[1:])
    require(tuple(map(sha,(archetype,glyphs,pdf)))==PINS,'source hash mismatch')
    r = json.loads(review.read_text()); manifest=r['manifest']
    require(hashlib.sha256(json.dumps({k:v for k,v in manifest.items() if k!='dataset_sha256'},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()==r['dataset_sha256']==manifest['dataset_sha256']=='e95f1d10df4b50a9ac1a8ccd6b3ec99cbdcb08453cc6311a6533a62056a75311','review hash')
    require(len(manifest['items'])==len(r['answers'])==200 and {i['id'] for i in manifest['items']}==set(r['answers']),'review IDs')
    with tarfile.open(archetype) as t:
        sql=t.extractfile('digipal_project/archetype.sql').read().decode()
    an,im,gr,idi,al=(table(sql,'digipal_'+n) for n in ('annotation','image','graph','idiograph','allograph'))
    rows=an.merge(im[['id','locus','width','height']],left_on='image_id',right_on='id').merge(gr[['id','idiograph_id','hand_id']],left_on='graph_id',right_on='id').merge(idi[['id','allograph_id']],left_on='idiograph_id',right_on='id',suffixes=('','_idi')).merge(al[['id','name']],left_on='allograph_id',right_on='id',suffixes=('','_al'))
    require(len(rows)==len(an)==len(gr)==1684,'annotation join')
    for item in rows.itertuples():
        g=ast.literal_eval(item.geo_json)['geometry']; a=np.asarray(g['coordinates'][0],float)
        require(g['type']=='Polygon' and np.isfinite(a).all() and (a>=0).all() and (a[:,0]<=int(item.width)).all() and (a[:,1]<=int(item.height)).all(),'annotation geometry')
    result={'archetype':{'images':len(im),'annotations':len(an),'annotated_images':rows.locus.nunique(),'hands':rows.hand_id.nunique(),'allographs':rows.name.value_counts().to_dict()}}
    with zipfile.ZipFile(glyphs) as z, fitz.open(pdf) as doc:
        require(z.testzip() is None,'ZIP CRC')
        def read(n): return pd.read_csv(io.BytesIO(z.read('glyph-map/'+n+'.tsv')),sep='\t',keep_default_na=False)
        pages,words,letters=(read(n) for n in ('pages','words','letters'))
        require(not words.word_id.duplicated().any() and not letters.duplicated(['word_id','letter']).any(),'duplicate IDs')
        bypage=pages.set_index('image'); human=words[words.trust.isin(['owner-traced','owner-answered'])]
        lrows=letters[letters.word_id.isin(human.word_id)]
        refs=collections.defaultdict(list)
        for p in doc:
            lines=p.get_text().splitlines()
            if len(lines)>2: refs[lines[2]].append(p.number+1)
        dev=set()
        for item in manifest['items']:
            dev.update(re.findall(r'(?<!\d)(\d+)[rv]',doc[item['page']-1].get_text().splitlines()[2]))
        counts=collections.defaultdict(collections.Counter); score=collections.Counter(); images=set()
        for page,group in human.groupby('page'):
            with np.load(io.BytesIO(z.read('glyph-map/masks/'+page+'.npz')),allow_pickle=False) as m:
                lookup={v:i for i,v in enumerate(m['words'])}
                wi, xx, yy, ll, ii, ims=(m[k] for k in ('word','x','y','letter','image','images'))
                for item in group.itertuples():
                    sel=wi==lookup[item.word_id]; x,y,L,I=(a[sel] for a in (xx,yy,ll,ii)); p=bypage.loc[item.image]
                    require(len(x)>0 and (ims[I]==item.image).all() and (x>=0).all() and (y>=0).all() and (x<p.width).all() and (y<p.height).all() and (L>=-1).all() and (L<item.letters).all(),'mask geometry')
                    require(int((L>=0).sum())==item.ink_pixels and int((L<0).sum())==item.stray_pixels,'word pixel counts')
                    for letter in lrows[lrows.word_id==item.word_id].itertuples():
                        q=L==letter.letter-1; lx,ly=x[q],y[q]
                        require(len(lx)==letter.pixels and len(lx)>0 and (lx.min(),ly.min(),lx.max()+1,ly.max()+1)==(letter.x0,letter.y0,letter.x1,letter.y1),'letter geometry')
                    counts[item.trust].update(words=1,letters=item.letters,assigned=item.ink_pixels,stray=item.stray_pixels)
                    pn=refs.get(p.yale_label,[])
                    if item.trust!='owner-traced' or len(pn)!=1 or not re.fullmatch(r'\d+[rv]',p.yale_label) or p.yale_label[:-1] in dev: continue
                    b=[b for b in doc[pn[0]-1].get_text('dict')['blocks'] if b['type']==1]
                    require(len(b)==1,'image layout')
                    image=Image.open(io.BytesIO(b[0]['image'])).convert('RGB')
                    sx,sy=image.width/p.width,image.height/p.height
                    require(abs(sx/sy-1)<.001,'aspect mismatch')
                    X=np.floor((x[L>=0]+.5)*sx).astype(int); Y=np.floor((y[L>=0]+.5)*sy).astype(int)
                    require((X>=0).all() and (Y>=0).all() and (X<image.width).all() and (Y<image.height).all(),'mapped pixels')
                    l,t=max(0,int(X.min())-64),max(0,int(Y.min())-64)
                    R,B=min(image.width,int(X.max())+65),min(image.height,int(Y.max())+65)
                    v=votes(image.crop((l,t,R,B))); X-=l; Y-=t
                    score.update(words=1,pixels=len(X),native_cells=len(set(zip(X,Y))))
                    for name,mask in [('union',v>0),('majority',v>3),('intersection',v==6)]:
                        score[name]+=int(mask[Y,X].sum())
                        score[name+'_nonempty']+=int(mask[Y,X].any())
                        for dx,dy in [(4,0),(-4,0),(0,4),(0,-4)]:
                            good=(X+dx>=0)&(X+dx<v.shape[1])&(Y+dy>=0)&(Y+dy<v.shape[0])
                            score[f'{name}_{dx}_{dy}']+=int(mask[Y[good]+dy,X[good]+dx].sum())
                            if name=='union': score[f'denom_{dx}_{dy}']+=int(good.sum())
                    images.add(pn[0])
        require(sum(c['words'] for c in counts.values())==460 and sum(c['letters'] for c in counts.values())==2560,'human counts')
        result['allen']={'words':len(words),'letters':len(letters),'image_records':len(pages),'mask_files':sum(n.endswith('.npz') for n in z.namelist()),'human':dict(counts)}
        result['pilot']={'status':'UNREGISTERED_POSITIVE_ONLY', 'images':len(images),'counts':dict(score)}
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()

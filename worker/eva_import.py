"""Private source-pinned EVA2 (July 2004) reference and historical comparison import."""
import argparse
import json
import shutil
from pathlib import Path
import worker as w
import reference_import as ri

EVA_SHA = '2f9a9c7e81dedfbd934e49eeac47de07e7e0855eda46f063a0624958d3e524fc'
STA_SHA = '85a595aa61936fa103a0f2c11d980e9970e11f98d1f35038f9fc268cc433ada2'
NAMES = {'eva-original':'EVA2 (original reference)', 'bennett':'Bennett (comparison)', 'fsg':'FSG (comparison)', 'currier':'Currier (comparison)', 'frogguy':'Frogguy (comparison)', 'eva-aux':'EVA2 auxiliary symbols'}


def discover(pdf, output):
    import fitz
    w.require(w.sha(pdf)==EVA_SHA, 'Unrecognized EVA edition/hash')
    entries=[]; omitted=[]; seen=set()
    with fitz.open(pdf) as doc:
        w.require(len(doc)==7, 'Unexpected page count')
        def table(page, idx=0):
            return doc[page-1].find_tables().tables[idx]
        def add(page,t,row,col,scheme,label,category):
            cell=t.rows[row].cells[col]
            w.require(cell is not None and label, 'Missing reference cell')
            rect=fitz.Rect(cell)
            spans=[s for b in doc[page-1].get_text('dict',clip=rect)['blocks'] for l in b.get('lines',[]) for s in l['spans']]
            w.require(any('EVA2' in s['font'] for s in spans), 'Reference cell is not EVA2 font')
            key=(scheme,label,page,tuple(cell))
            if key not in seen:
                seen.add(key); entries.append(dict(scheme=scheme,label=label,page=page,box=list(cell),visual_column=category))
        t=table(1); rows=t.extract(); w.require(rows[0][0]=='BASIC EVA CHARACTERS','Unexpected basic table')
        for j,r in enumerate(rows[2:],2):
            add(1,t,j,1,'eva-original',r[0],'Basic EVA')
            if r[2]: add(1,t,j,2,'eva-original',r[2],'Capitalised connectivity form')
        t=table(2); rows=t.extract(); w.require(rows[0][0]=='EXTENDED EVA CHARACTERS','Unexpected extended table')
        for j,r in enumerate(rows[2:],2):
            for k in (0,4,8):
                if r[k]: add(2,t,j,k+2,'eva-original',f'&{int(r[k])};','Extended EVA (2004 source notation)')
        for i,category in enumerate(('Doodles','Dee-like numerals')):
            t=table(3,i)
            for j,r in enumerate(t.extract()[1:],1): add(3,t,j,len(r)-1,'eva-aux',f'{category}: {r[0]}',category)
        t=table(4); rows=t.extract(); w.require(rows[0]==['Character','Example','EVA','Capitalised EVA','Script'],'Unexpected connectivity table')
        for j,r in enumerate(rows[1:],1): add(4,t,j,4,'eva-original',r[2].replace(' ¹',''),'Connectivity example (sequence, not atomic glyph)')
        for page in (6,7):
            t=table(page); rows=t.extract()
            for j,r in enumerate(rows):
                if page==6 and j==0: continue
                if not r[5] or r[5] in ('line end','para end','*'):
                    omitted.append([page,j+1,r,'blank or transcription marker']); continue
                for k,scheme in enumerate(('bennett','fsg','currier','frogguy','eva-original')):
                    label=ri.norm(r[k]);
                    if not label: continue
                    if '¹' in label or '*' in label:
                        omitted.append([page,j+1,scheme,label,'source footnote: not original']); continue
                    rect=fitz.Rect(t.rows[j].cells[k]); spans=[s for b in doc[page-1].get_text('dict',clip=rect)['blocks'] for l in b.get('lines',[]) for s in l['spans']]
                    category='Historical comparison; non-original combination' if any('Italic' in s['font'] for s in spans) else 'Historical comparison; source row'
                    add(page,t,j,5,scheme,label,category)
    w.require(not Path(output).exists(),'Plan already exists')
    plan=dict(schema=1,source=ri.SOURCES['eva'],source_sha256=EVA_SHA,version='EVA Alphabet Font Version 2 Reference (July 2004)',rights=ri.RIGHTS,reviewed=False,entries=entries,omitted=omitted,recognized_pages=[1,2,3,4,6,7])
    w.write(output,plan); return plan


def combine(catalogs,out):
    """Merge private catalogs without collapsing historical or current conventions."""
    from active_review import catalog
    out=Path(out); w.require(not out.exists(),'Output already exists')
    schemes=[]; seen=set(); inputs=[]
    for path in catalogs:
        path=Path(path); catalog(path); obj=w.read(path); inputs.append(w.sha(path))
        for scheme in obj['schemes']:
            key=scheme['id']; w.require(key not in seen,'Duplicate scheme'); seen.add(key)
            for entry in scheme['entries']:
                for sample in entry['samples']:
                    source=w.within(path.parent,sample['file']); dest=f'{key}/{sample["sha256"]}.png'
                    sample['file']=dest
                    target=out/dest; target.parent.mkdir(parents=True,exist_ok=True)
                    if not target.exists(): shutil.copyfile(source,target)
                    w.require(w.sha(target)==sample['sha256'],'Copied reference hash mismatch')
            scheme['name']=NAMES.get(key,scheme['name']); schemes.append(scheme)
    w.require(1<=len(schemes)<=12,'Too many conventions')
    primary=[s for s in schemes if s['id']!='eva-aux']; auxiliary=[s for s in schemes if s['id']=='eva-aux']
    w.require(primary,'No primary reference conventions')
    w.write(out/'references.json',dict(schema=1,schemes=primary,preview=True,input_catalog_sha256=inputs))
    catalog(out/'references.json')
    if auxiliary:
        w.write(out/'auxiliary.json',dict(schema=1,schemes=auxiliary,preview=True,input_catalog_sha256=inputs))
        catalog(out/'auxiliary.json')
    return {s['id']:len(s['entries']) for s in schemes}


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='action',required=True)
    d=sub.add_parser('discover'); d.add_argument('pdf'); d.add_argument('output')
    c=sub.add_parser('combine'); c.add_argument('out'); c.add_argument('catalogs',nargs='+')
    a=p.parse_args()
    if a.action=='discover': print(len(discover(a.pdf,a.output)['entries']))
    else: print(json.dumps(combine(a.catalogs,a.out),indent=2))


if __name__=='__main__': main()

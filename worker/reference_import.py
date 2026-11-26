"""Build a private, review-gated glyph catalog from local reference PDFs."""
import argparse
import re
from pathlib import Path
import worker as w

SOURCES = {
    'eva': 'https://www.voynich.nu/hist/gabriel/eva2_reference.pdf',
    'sta': 'https://www.voynich.nu/data/sta/STA1_def.pdf',
}
RIGHTS = 'Local reference preview only; redistribution rights not cleared'


def norm(value):
    return ' '.join((value or '').split())


def discover(pdf, expected_sha, kind, output):
    """Propose cell locations; never declare an exhaustive or approved inventory."""
    import fitz
    w.require(kind in SOURCES and w.sha(pdf)==expected_sha, 'Source hash or kind mismatch')
    entries=[]; omitted=[]; recognized=[]
    with fitz.open(pdf) as doc:
        for page in doc:
            if kind=='eva' and page.number>1: continue
            for table in page.find_tables().tables:
                values=table.extract()
                for i,row in enumerate(values):
                    cells=[norm(x) for x in row]
                    if kind=='sta' and (cells[:7]==['STA','Combi','R','Eva','v101','Eva','v101'] or
                                        (page.number==19 and i==0 and len(cells)==11 and cells[0]=='Ts')):
                        recognized.append(page.number+1)
                        first=i if cells[0]=='Ts' else i+1
                        pictures=[fitz.Rect(x['bbox']) for x in page.get_image_info()]
                        for j,line in enumerate(values[first:],first):
                            v=[norm(x) for x in line]
                            if len(v)<7: continue
                            code,combi,red,ev,vc=v[:5]
                            if not re.fullmatch(r'[A-X][A-Za-z0-9]',code) or combi:
                                omitted.append([page.number+1,j+1,code,combi,'non-standalone or special']); continue
                            visual=False
                            for col in (5,6):
                                rect=table.rows[j].cells[col]
                                if rect is None: continue
                                cell=fitz.Rect(rect)
                                if not any(cell.contains((pic.tl+pic.br)/2) for pic in pictures): continue
                                visual=True
                                for scheme,label in [('sta1',code),('sta1r',code if red=='*' else ''),('eva-from-sta',ev if col==5 else ''),('v101-from-sta',vc if col==6 else '')]:
                                    if label and label not in ('?','???','(below)','(above)'):
                                        entries.append(dict(scheme=scheme,label=label,page=page.number+1,box=list(rect),sta_code=code,visual_column='EVA' if col==5 else 'v101'))
                            if not visual: omitted.append([page.number+1,j+1,code,combi,'no standalone visual cell'])
                        break
                    if kind=='eva' and page.number==0 and len(cells)>=3 and cells[1]=='EVA' and cells[2]=='Capitalised EVA':
                        recognized.append(1)
                        for j,line in enumerate(values[i+1:],i+1):
                            code=norm(line[0]); rect=table.rows[j].cells[1]
                            if re.fullmatch(r"[a-z']",code) and rect is not None:
                                entries.append(dict(scheme='basic-eva',label=code,page=1,box=list(rect)))
                        break
                    if kind=='eva' and page.number==1:
                        groups=[k for k in range(len(cells)-2) if cells[k]=='& code;' and cells[k+1:k+3]==['Arial','EVA']]
                        if not groups: continue
                        recognized.append(2)
                        for j,line in enumerate(values[i+1:],i+1):
                            for k in groups:
                                code=norm(line[k]); rect=table.rows[j].cells[k+2]
                                if code.isdecimal() and 128<=int(code)<=255 and rect is not None:
                                    entries.append(dict(scheme='extended-eva',label=f'@{code};',page=2,box=list(rect)))
                        break
    w.require(entries,'No recognized reference cells; inspect original PDF and create explicit plan')
    plan=dict(schema=1,source=SOURCES[kind],source_sha256=expected_sha,version='STA v1.03 (2025-09-13)' if kind=='sta' and expected_sha=='85a595aa61936fa103a0f2c11d980e9970e11f98d1f35038f9fc268cc433ada2' else 'verify edition locally',rights=RIGHTS,
              reviewed=False,entries=entries,recognized_pages=sorted(set(recognized)),omitted=omitted)
    w.require(not Path(output).exists(),'Plan already exists'); w.write(output,plan)
    return {'proposed_cells':len(entries),'recognized_pages':plan['recognized_pages'],'omitted_rows':len(omitted),'reviewed':False}


def build(pdf, plan_path, out, preview=False):
    """Render approved cell clips, not OCR-generated glyphs; source bytes stay local."""
    import fitz
    from PIL import Image
    plan=w.read(plan_path); out=Path(out)
    w.require(plan['schema']==1 and (preview or plan['reviewed'] is True),'Explicit visual plan review required')
    w.require(w.sha(pdf)==plan['source_sha256'],'Reference PDF hash mismatch')
    w.require(all(isinstance(plan[k],str) and plan[k].strip() for k in ('source','version','rights')) and plan['version']!='verify edition locally','Source edition and rights required')
    if not preview: w.require(isinstance(plan.get('reviewer'),str) and plan['reviewer'].strip(),'Reviewer required')
    if not preview: w.require(plan.get('private_use_confirmed') is True,'Private reference use must be confirmed')
    w.require(not out.exists() and 1<=len(plan['entries'])<=12000,'Invalid output or cell count')
    schemes={}; seen=set()
    with fitz.open(pdf) as doc:
        for entry in plan['entries']:
            scheme,label,page,box=(entry[k] for k in ('scheme','label','page','box'))
            w.require(re.fullmatch(r'[A-Za-z0-9_-]+',scheme) and isinstance(label,str) and label.strip() and len(label)<=100,'Invalid scheme or label')
            w.require(type(page) is int and 1<=page<=len(doc) and isinstance(box,list) and len(box)==4,'Invalid reference page or cell')
            rect=fitz.Rect(box); w.require(not rect.is_empty and not rect.is_infinite and doc[page-1].rect.contains(rect) and rect.width>2 and rect.height>2,'Invalid reference clip')
            key=(scheme,label,page,tuple(box)); w.require(key not in seen,'Duplicate reference cell'); seen.add(key)
            entries=schemes.setdefault(scheme,{}); samples=entries.setdefault(label,[])
            w.require(len(samples)<8,'Too many examples for label; curate explicitly')
            samples.append((page,rect,entry.get('sta_code'),entry.get('visual_column')))
        w.require(len(schemes)<=12 and all(len(s)<=1024 for s in schemes.values()),'Inventory limit exceeded')
        out.mkdir(parents=True); (out/'refs').mkdir(); catalog=[]; number=0
        for scheme,entries in schemes.items():
            items=[]
            for label,samples in entries.items():
                refs=[]
                for page,rect,sta_code,visual_column in samples:
                    clip=fitz.Rect(rect.x0+1,rect.y0+1,rect.x1-1,rect.y1-1)
                    pix=doc[page-1].get_pixmap(dpi=250,clip=clip,colorspace=fitz.csRGB,alpha=False)
                    im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
                    w.require(im.convert('L').getextrema()[0]<180,'Blank reference clip; inspect source cell')
                    number+=1; name=f'refs/{number:05d}.png'; im.save(out/name)
                    refs.append(dict(file=name,sha256=w.sha(out/name),source=f'p. {page} | {sta_code or label} | {visual_column or scheme}',page=page,box=list(rect)))
                items.append(dict(label=label,samples=refs))
            catalog.append(dict(id=scheme,name=scheme,version=plan['version'],source=plan['source'],coverage='unreviewed candidate subset; not exhaustive' if preview else 'reviewed subset; not exhaustive',source_sha256=plan['source_sha256'],rights=plan['rights'],entries=items))
    w.write(out/'references.json',dict(schema=1,schemes=catalog,plan_sha256=w.sha(plan_path),preview=preview))
    return {'schemes':{s['id']:len(s['entries']) for s in catalog},'images':number}


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='action',required=True)
    d=sub.add_parser('discover')
    for k in ('pdf','expected_sha','kind','output'): d.add_argument(k)
    b=sub.add_parser('build')
    for k in ('pdf','plan_path','out'): b.add_argument(k)
    b.add_argument('--preview',action='store_true')
    args=vars(p.parse_args()); action=args.pop('action'); print({'discover':discover,'build':build}[action](**args))


if __name__=='__main__': main()

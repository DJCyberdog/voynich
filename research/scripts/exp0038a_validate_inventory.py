import hashlib,json,sys,random,collections
from pathlib import Path
import fitz
p=Path(sys.argv[1]);inv=json.loads(Path(sys.argv[2]).read_text());out=Path(sys.argv[3]);assert hashlib.file_digest(p.open('rb'),'sha256').hexdigest()==inv['source']['sha256'];d=fitz.open(p);assert len(d)==214
for page,r in inv['pages'].items():
    pg=d[int(page)-1]; pix=pg.get_pixmap(dpi=100,colorspace=fitz.csRGB,alpha=False)
    assert (pix.width,pix.height)==(827,1170) and hashlib.sha256(pix.samples).hexdigest()==r['rgb_sha256']
    assert r['folio'][1:] in pg.get_text().splitlines()
ids=set();classes=collections.defaultdict(set);counts=collections.Counter();attachment=collections.Counter();candidate_roots=set();inside_roots=set()
for x in inv['objects']:
    assert x['id'] not in ids;ids.add(x['id']);r=inv['pages'][str(x['page'])]['root'];classes[x['shape']].add(r);counts[x['shape']]+=1;attachment[x['attachment']]+=1
    for b in (x['box'],x['writing_box']):
        if b:assert 0<=b[0]<b[2]<=827 and 0<=b[1]<b[3]<=1170
    if x['writing_box']:candidate_roots.add(r)
    if x['attachment']=='inside_object':
        inside_roots.add(r);a,b=x['box'],x['writing_box'];assert a[0]<=b[0]<b[2]<=a[2] and a[1]<=b[1]<b[3]<=a[3]
roots={inv['pages'][str(x['page'])]['root'] for x in inv['objects']};gates={'objects':len(ids)>=8,'roots':len(roots)>=2,'repeated_shape':any(len(v)>=2 for v in classes.values()),'candidate_writing_roots':len(candidate_roots)>=2,'coordinates_and_ids':True}
res=dict(experiment='EXP-0038a',inventory_decision='PASS' if all(gates.values()) else 'NOT_MET',semantic_readiness='BLOCKED',gates=gates,objects=len(ids),roots=sorted(roots),shape_counts=dict(counts),shape_roots={k:sorted(v) for k,v in classes.items()},attachment_counts=dict(attachment),candidate_writing_roots=sorted(candidate_roots),inside_object_writing_roots=sorted(inside_roots),independent_review_count=0,locus_alignment_count=0,render_version=fitz.VersionBind)
out.write_text(json.dumps(res,sort_keys=True,indent=2)+'\n')
# Opaque IDs and randomized order, private mapping not in review sheet.
items=inv['objects'].copy();random.Random(380038).shuffle(items);review=[];key={}
for i,x in enumerate(items,1):
    rid=f'R{i:02d}';key[rid]=x['id'];review.append(dict(review_id=rid,pdf_page=x['page'],object_box=x['box'],object_valid=None,shape_class=None,features=None,writing_box=None,attachment=None,alternative=None,certainty=None))
out.with_name('review_template.json').write_text(json.dumps({'instructions':'Independent reviewer, without transcription or preliminary inventory: use owner PDF at 100 dpi RGB, top-left pixel coordinates, 827x1170. Verify proposed region or reject/uncertain. Describe visible geometry; choose pedestal / broad_body / other / uncertain. Independently locate nearby writing region if any; distinguish inside-object, ambiguous-nearby, none-clear. Do not read or translate writing. Supply alternatives and confidence. Opaque IDs are not claims of full blinding: page and box reveal location.','reviews':review},indent=2)+'\n')
out.with_name('private_review_key.json').write_text(json.dumps(key,indent=2)+'\n')

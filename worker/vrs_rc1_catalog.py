"""RC1 source-native, private catalog preview; no reviewed inventory or model generated."""
import copy
import json
import shutil
import tempfile
from pathlib import Path

import vrs_contract as c
from vrs_portable import local,need,digest
from vrs_rc_snapshot import existing_directory,destination,private_directory
from vrs_desktop_api import atomic_json
import vrs_rc1_intake as intake
import reference_import

def merge_catalogs(parts,out):
    """Deduplicate identical PNG bytes without merging notation IDs or source cells."""
    out=Path(out);out.mkdir();(out/'refs').mkdir();schemes=[];seen=set();unique={}
    for home,plan_path in parts:
        home=Path(home);plan_path=Path(plan_path);obj=c.load(home/'references.json')
        need(obj['preview'] is True and obj['plan_sha256']==digest(plan_path),'Preview plan mismatch')
        for scheme in obj['schemes']:
            sid=scheme['id'];need(sid in intake.VISUAL_SCHEMES and sid not in seen,'Unexpected catalog scheme');seen.add(sid)
            scheme['plan_sha256']=obj['plan_sha256']
            for entry in scheme['entries']:
                for sample in entry['samples']:
                    src=local(home,sample['file']);need(src.is_file() and digest(src)==sample['sha256'],'Preview sample mismatch')
                    key=sample['sha256'];name='refs/'+key+'.png';target=local(out,name)
                    if key not in unique:
                        shutil.copyfile(src,target);need(digest(target)==key,'Preview copy mismatch');unique[key]=target
                    sample['file']=name
            schemes.append(scheme)
    need(schemes,'Empty preview')
    path=out/'references.json';atomic_json(path,dict(schema=1,schemes=schemes,preview=True))
    return path,unique

def build_preview(root,out,plan,approved,scope):
    root=existing_directory(root);out=destination(out,root);c.digest_ok(approved)
    need(scope==plan['scope']=='REAL_RESEARCH' and c.digest(plan)==approved,'Explicit real-source preview approval required')
    need(plan['catalog'] is None,'Existing catalog; create a distinct curated plan instead')
    report,_=intake.inspect(root,plan);need(not report['blocked'],'Intake blocked')
    # Limit automatic table discovery to exact previously identified documents.
    selected=[]
    for kind,scheme in [('eva','Eva-'),('sta','STA1')]:
        known=next(x for x in intake.KNOWN_SOURCES if x[2]=='reference_pdf' and x[3]==scheme)
        rows=[x for x in plan['sources'] if x['role']=='reference_pdf' and x['scheme']==scheme and x['sha256']==known[4]]
        need(len(rows)==1,'Known reference PDF required for automatic cell proposal')
        selected.append((kind,rows[0],known[7]))
    private_directory(out)
    try:
        for row in plan['sources']:intake.copy_input(root,out,row)
        generated=copy.deepcopy(plan);seen={x['sha256'] for x in plan['sources']}
        def add(path,role,rid,origin,edition,scheme=None):
            h=digest(path);need(h not in seen,'Generated asset duplicates admitted source bytes');seen.add(h)
            generated['sources'].append(dict(id=rid,path=path.relative_to(out).as_posix(),role=role,sha256=h,bytes=path.stat().st_size,origin=origin,edition=edition,scheme=scheme,rights='LOCAL_USE_ATTESTED',rights_basis='Derived local preview under explicitly approved source plan '+approved))
        parent=local(out,'data/rc1/catalog-preview');parent.mkdir()
        parts=[]
        with tempfile.TemporaryDirectory(dir=out,prefix='.preview-') as d:
            temp=Path(d)
            for kind,row,edition in selected:
                src=local(out,row['path']);draft=parent/(kind+'-plan.json')
                reference_import.discover(src,row['sha256'],kind,draft)
                value=c.load(draft);value['version']=edition;value['reviewed']=False;atomic_json(draft,value)
                add(draft,'catalog_plan','preview-'+kind+'-plan',row['origin'],edition)
                home=temp/kind;reference_import.build(src,draft,home,preview=True);parts.append((home,draft))
            path,unique=merge_catalogs(parts,parent/'catalog')
        for h,p in sorted(unique.items()):add(p,'reference_sample','preview-'+h,'PDF cells; see source-bound catalog entries','Unreviewed preview')
        add(path,'visual_catalog','preview-catalog','Exact EVA/STA PDF preview plans','Unreviewed, source-native schemes')
        generated['catalog']='preview-catalog'
        report,_=intake.inspect(out,generated);need(not report['blocked'],'Generated preview validation failed')
        atomic_json(local(out,'rc1-preview-plan.json'),generated)
        return dict(status='PREVIEW_CREATED',scope=scope,plan_sha256=c.digest(generated),unique_images=len(unique),catalog_path=path.relative_to(out).as_posix(),missing=report['missing'],execution_authorized=False,scientific_status='UNADJUDICATED')
    except BaseException:
        shutil.rmtree(out);raise

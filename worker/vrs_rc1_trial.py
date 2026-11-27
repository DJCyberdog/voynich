"""Owner-only RC1 technical trial. Unreviewed PDF reference prototypes, never calibration."""
import argparse
import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

import vrs_contract as c
import vrs_rc1_intake as intake
from vrs_portable import local,need,digest
from vrs_rc_snapshot import existing_directory,destination,private_directory
from vrs_desktop_api import Desktop,atomic_json
from vrs_rc1_catalog import build_preview
from vrs_build_portable import source_payload


def stage(source,originals,out):
    source=existing_directory(source);originals=existing_directory(originals);out=destination(out,originals);destination(out,source)
    source_payload(source);private_directory(out)
    try:
        target=out/'data/rc1';target.mkdir(parents=True)
        for rid,name,role,scheme,h,size,origin,edition in (*intake.KNOWN_SOURCES,*intake.OPTIONAL_SOURCES):
            p=local(originals,name)
            if not p.exists() and name=='ZL3b-n(1).txt':p=local(originals,'ZL3b-n.txt')
            if not p.exists() and name=='voynich.pdf':p=local(originals,'voynich(1).pdf')
            if not p.exists():
                need(role not in ('manuscript','reference_pdf','transcription'),'Required original missing: '+name);continue
            need(p.is_file() and not p.is_symlink() and p.stat().st_size==size and digest(p)==h,'Original mismatch: '+name)
            shutil.copyfile(p,local(target,name));need(digest(local(target,name))==h,'Copy mismatch')
        plan=intake.starter(source,out);atomic_json(out/'sources-plan.json',plan)
        return dict(status='STAGED_NOT_APPROVED',plan_sha256=c.digest(plan),sources=len(plan['sources']))
    except BaseException:shutil.rmtree(out);raise


def attest(root,plan,approved,basis):
    need(plan['scope']=='REAL_RESEARCH' and c.digest(plan)==approved,'Source plan digest mismatch')
    need(type(basis) is str and 0<len(basis.strip())<=512,'Specific local-use basis required')
    need(plan['catalog'] is None and plan['run_manifest'] is None,'Original source plan required')
    report,_=intake.inspect(root,plan)
    need(not any(x['reason']!='LOCAL_USE_NOT_ATTESTED' for x in report['blocked']),'Source validation failed')
    need(all(r['rights']!='DENIED' for r in plan['sources']),'Denied source requires separate review')
    for r in plan['sources']:r['rights']='LOCAL_USE_ATTESTED';r['rights_basis']=basis.strip()
    p=local(root,'sources-approved.json');need(not p.exists(),'Approval file exists');atomic_json(p,plan)
    return dict(status='LOCAL_USE_ATTESTED',plan_sha256=c.digest(plan),path=p.name,execution_authorized=False)


def compact(path,value):
    raw=json.dumps(value,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode('ascii')
    need(len(raw)<=c.MAX_JSON,'Trial JSON quota')
    with path.open('xb') as f:f.write(raw)


def first_folio(pdf):
    import fitz
    with fitz.open(pdf) as doc:
        need(len(doc)==214,'Expected exact 214-page Yale PDF')
        text=[x.strip() for x in doc[3].get_text().splitlines()]
        need('1r' in text and 'Page 4 of 214' in text,'First folio caption mismatch')
    return {'4':'f1'}


def prepare(root,out,plan,approved,backend='cpu'):
    """Build a separate reviewable plan, not a registered run or accepted model."""
    import glyphs as g
    import numpy as np
    from PIL import Image
    root=existing_directory(root);out=destination(out,root)
    need(backend in ('cpu','cuda'),'Explicit trial backend required')
    need(plan['scope']=='REAL_RESEARCH' and c.digest(plan)==approved,'Source approval mismatch')
    known={r[0]:r[4] for r in (*intake.KNOWN_SOURCES,*intake.OPTIONAL_SOURCES)}
    pinned={r['id']:r['sha256'] for r in plan['sources']}
    need(all(pinned.get(k)==known[k] for k in ('manuscript-beinecke-408','zl3b-eva','zl3b-sta1','eva-font-reference','sta-definition-reference')),'Exact trial sources required')
    result=build_preview(root,out,plan,approved,'REAL_RESEARCH',runtime_subset=True)
    try:
        p=c.load(out/'rc1-preview-plan.json');seen={r['sha256'] for r in p['sources']};home=local(out,'data/rc1/trial');home.mkdir()
        by={r['id']:r for r in p['sources']}
        def ref(row):return dict(path=row['path'],sha256=row['sha256'])
        def add(name,role,value,scheme=None):
            path=local(home,name+'.json');compact(path,value);h=digest(path);need(h not in seen,'Duplicate derived bytes');seen.add(h)
            row=dict(id='trial-'+name,path=path.relative_to(out).as_posix(),role=role,scheme=scheme,sha256=h,bytes=path.stat().st_size,origin='Local RC1 technical trial; exact pinned PDF references',edition='Unreviewed subset; no manuscript calibration',rights='LOCAL_USE_ATTESTED',rights_basis='Derived under source plan '+approved)
            p['sources'].append(row);return ref(row)
        catalog=Desktop(out).catalog(result['catalog_path']);inventories=[];models=[];coverage={}
        for name,sid in [('eva','Eva-'),('sta','STA1')]:
            entries=catalog[sid]['entries'];labels=sorted(entries);need(2<=len(labels)<=256,'Trial subset bounds')
            inv=add(name+'-inventory','inventory',dict(schema=1,convention=sid,labels=labels),sid);inventories.append(dict(alphabet=inv))
            proto=[];cells=[]
            for label in labels:
                vectors=[];samples=[]
                for sample,_ in entries[label]:
                    with Image.open(c.artifact(out,sample)) as im:vectors.append(g.feature(im))
                    samples.append(sample)
                vector=np.mean(vectors,axis=0)
                proto.append([int(x) if x==0 or x==1 else round(float(x),3) for x in vector]);cells.append(dict(label=label,samples=samples))
            model=add(name+'-model','model',dict(version=g.VERSION,labels=labels,prototypes=proto,inventory_sha256=inv['sha256'],code_sha256=digest(Path(g.__file__)),thresholds=[.12,.005]),sid)
            report=add(name+'-report','model_report',dict(schema=1,model_sha256=model['sha256'],source_catalog=ref(by[p['catalog']]),inventory=inv,reference_cells=cells,method='Mean PDF-cell features rounded to 3 decimals',calibration='NONE',scientific_status='UNADJUDICATED'),sid)
            models.append(dict(convention=sid,model=model,report=report));coverage[sid]=len(labels)
        manuscript=ref(by['manuscript-beinecke-408']);groups=add('groups','groups',first_folio(c.artifact(out,manuscript)))
        references=add('references','references',dict(schema=1,inventories=inventories));bundle=add('models','model_bundle',dict(schema=1,models=models));policy=add('policy','recognition_policy',dict(schema=1,approval=None,mapping=None))
        m=dict(schema=1,module=c.MODULE,protocol=c.PROTOCOL,backend=backend,seed=7,run_nonce=uuid.uuid4().hex,inputs=dict(manuscript=manuscript,groups=groups,references=references,model=bundle,recognition_policy=policy),transcriptions=[ref(by['zl3b-eva']),ref(by['zl3b-sta1'])])
        manifest=add('run','run_manifest',m);p['run_manifest']='trial-run'
        report,_=intake.inspect(out,p);need(report['status']=='INVENTORY_PASS','Trial dependency validation failed: '+str(report['blocked']))
        compact(out/'rc1-trial-plan.json',p)
        return dict(status='TRIAL_PLAN_READY_NOT_REGISTERED',plan_sha256=c.digest(p),run_id=c.digest(m),manifest=manifest['path'],physical_pages=[4],folio='f1r',labels=coverage,unique_images=result['unique_images'],backend=backend,execution_authorized=False,scientific_status='UNADJUDICATED')
    except BaseException:shutil.rmtree(out);raise


def bootstrap(root,profile):
    """Resolve local Windows owner-test assets; no installed-plan approval or binary redistribution."""
    from vrs_native_acceptance import assemble_runtime,fetch_wheels
    from vrs_prepare_plan import prepare as lock
    from vrs_portable import extract
    root=existing_directory(root);source_payload(root)
    need(os.name=='nt' and sys.version_info[:2]==(3,13) and sys.maxsize>2**32,'Trusted full Windows x64 CPython 3.13 required')
    need(profile in ('cpu','cuda') and not (root/'bootstrap').exists() and not (root/'config'/('install-'+profile+'.json')).exists(),'Fresh trial root required')
    plan_path=local(root,'config/install-'+profile+'.json');boot=local(root,'bootstrap')
    try:
        with tempfile.TemporaryDirectory(dir=root,prefix='.rc1-assets-') as d:
            home=Path(d);rt=home/'python-runtime.zip';wheels=home/'wheels';wheels.mkdir()
            assemble_runtime(sys.base_prefix,rt);fetch_wheels(profile,wheels,root);result=lock(root,profile,rt,wheels)
            boot.mkdir();extract(rt,boot)
        return result
    except BaseException:
        # Remove only the freshly created plan/bootstrap, retaining verified cache.
        plan_path.unlink(missing_ok=True)
        if boot.exists():shutil.rmtree(boot)
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('stage');q.add_argument('originals',type=Path);q.add_argument('out',type=Path);q.add_argument('--source',type=Path,default=Path(__file__).resolve().parent)
    q=s.add_parser('attest');q.add_argument('root',type=Path);q.add_argument('plan',type=Path);q.add_argument('--approve',required=True);q.add_argument('--basis',required=True)
    q=s.add_parser('prepare');q.add_argument('root',type=Path);q.add_argument('plan',type=Path);q.add_argument('out',type=Path);q.add_argument('--approve',required=True);q.add_argument('--backend',choices=('cpu','cuda'),default='cpu')
    q=s.add_parser('bootstrap');q.add_argument('root',type=Path);q.add_argument('--profile',choices=('cpu','cuda'),required=True)
    a=p.parse_args()
    if a.command=='stage':v=stage(a.source,a.originals,a.out)
    elif a.command=='attest':v=attest(a.root,c.load(a.plan),a.approve,a.basis)
    elif a.command=='prepare':v=prepare(a.root,a.out,c.load(a.plan),a.approve,a.backend)
    else:v=bootstrap(a.root,a.profile)
    print(json.dumps(v,indent=2,sort_keys=True))


if __name__=='__main__':main()

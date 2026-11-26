"""RC1 private, explicitly approved source intake. No registration, compute, network or publication."""
import argparse
import hashlib
import json
import os
import re
import shutil
import stat
from pathlib import Path

import vrs_contract as c
from vrs_portable import local,need,digest
from vrs_build_portable import source_payload
from vrs_desktop_api import Desktop,atomic_json
from vrs_rc_snapshot import existing_directory,destination,private_directory

SCOPES=('REAL_RESEARCH','SYNTHETIC_TEST')
SCHEMES=('Eva-','STA1')
JSON_ROLES={'groups','references','model_bundle','recognition_policy','inventory','model','model_report','mapping','run_manifest','visual_catalog','catalog_plan','historical_result'}
ROLES=JSON_ROLES|{'manuscript','transcription','transcription_archive','reference_pdf','reference_sample','historical_report'}
CORE={'manuscript','transcription','reference_pdf'}
ARCHIVE_SCHEMES=('EvaT',)
VISUAL_SCHEMES={'basic-eva':'Eva-','extended-eva':'Eva-','sta1':'STA1','sta1r':'STA1','eva-from-sta':'STA1','v101-from-sta':'STA1'}
KNOWN_SOURCES=(
 ('manuscript-beinecke-408','voynich.pdf','manuscript',None,'d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c',127121031,'Owner copy; matches repository LFS declaration','exact PDF object'),
 ('zl3b-sta1','ZL3b.txt','transcription','STA1','8438ba1c45f47fe1d06b5262cbcdf60ce69158a0edbd4dd802612896f3217e2a',472861,'Zandbergen–Landini; owner copy','ZL3b, IVTFF STA1 2.0 M 5'),
 ('eva-font-reference','eva2_reference.pdf','reference_pdf','Eva-','2f9a9c7e81dedfbd934e49eeac47de07e7e0855eda46f063a0624958d3e524fc',170416,'G. Landini; owner copy','EVA Alphabet Font Version 2 Reference'),
 ('sta-definition-reference','STA1_def.pdf','reference_pdf','STA1','85a595aa61936fa103a0f2c11d980e9970e11f98d1f35038f9fc268cc433ada2',1159908,'R. Zandbergen; owner copy','STA definition 1.03, 2025-09-13; includes reduced-STA markers'),
)
MAX_BYTES=16*1024**3
MAX_ENTRIES=5000
ID=re.compile(r'[a-z0-9][a-z0-9._-]{0,95}')
RECEIPT='config/rc1-admission.json'
PLAN='config/rc1-plan.json'

def regular(root,rel):
    p=local(root,rel);s=p.lstat()
    need(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and not getattr(s,'st_file_attributes',0)&1024,'Nonregular or aliased input')
    return p,s

def validate_plan(plan):
    c.fields(plan,('schema','scope','application_sha256','sources','run_manifest','catalog'))
    need(type(plan['schema']) is int and plan['schema']==1 and plan['scope'] in SCOPES,'Unsupported intake contract')
    c.digest_ok(plan['application_sha256'])
    rows=plan['sources'];need(type(rows) is list and 0<len(rows)<=MAX_ENTRIES,'Source inventory quota')
    ids=set();paths={};hashes=set();total=0;roles={}
    for row in rows:
        c.fields(row,('id','path','role','sha256','bytes','origin','edition','scheme','rights','rights_basis'))
        rid=row['id'];path=row['path'];role=row['role'];scheme=row['scheme']
        need(type(rid) is str and ID.fullmatch(rid) and rid not in ids,'Duplicate or invalid source identity');ids.add(rid)
        need(type(path) is str and path.startswith('data/rc1/') and len(path)<=512 and path.casefold() not in paths,'Invalid or colliding intake path')
        need(not any(re.search(r'(?i)(owner[-_]?key|blind[-_]?key|holdout|credential|secret|\.dpapi$|\.git$)',p) for p in path.split('/')),'Restricted material refused')
        need(role in ROLES,'Unsupported role');c.digest_ok(row['sha256']);c.number(row['bytes'],1024**3);need(row['bytes']>0,'Empty source')
        need(row['sha256'] not in hashes,'Duplicate source bytes');hashes.add(row['sha256'])
        total+=row['bytes'];need(total<=MAX_BYTES,'Intake byte quota')
        for key in ('origin','edition','rights_basis'):need(type(row[key]) is str and 0<len(row[key].strip())<=512,'Missing provenance or rights basis')
        need(row['rights'] in ('LOCAL_USE_ATTESTED','UNKNOWN','DENIED'),'Invalid local-use declaration')
        need(scheme in ARCHIVE_SCHEMES if role=='transcription_archive' else scheme in SCHEMES if role in ('transcription','reference_pdf','inventory') else scheme is None or scheme in SCHEMES,'Invalid scheme binding')
        if role=='historical_report':need(path.lower().endswith(('.md','.txt')),'Historical report format')
        if role in JSON_ROLES:need(path.lower().endswith('.json'),'JSON role requires JSON path')
        if role in ('manuscript','reference_pdf'):need(path.lower().endswith('.pdf'),'PDF role requires PDF path')
        if role in ('transcription','transcription_archive'):need(path.lower().endswith(('.txt','.ivtff')),'Transcription path')
        paths[path.casefold()]=row;roles.setdefault(role,[]).append(row)
    need(len(roles.get('manuscript',[]))<=1,'Ambiguous manuscript')
    for role,key in [('run_manifest','run_manifest'),('visual_catalog','catalog')]:
        chosen=plan[key];items=roles.get(role,[])
        need(len(items)<=1 and ((chosen is None and not items) or (len(items)==1 and chosen==items[0]['id'])),'Ambiguous selected input')
    return {r['path']:r for r in rows},roles

def missing_roles(roles):
    missing=[]
    if not roles.get('manuscript'):missing.append('manuscript')
    for role in ('transcription','reference_pdf'):
        for scheme in SCHEMES:
            if not any(r['scheme']==scheme for r in roles.get(role,[])):missing.append(role+':'+scheme)
    if not roles.get('visual_catalog'):missing.append('visual_catalog')
    if not roles.get('run_manifest'):missing.append('run_manifest')
    return missing

def pin_row(root,row):
    p,s=regular(root,row['path']);need(s.st_size==row['bytes'] and digest(p)==row['sha256'],'Source bytes do not match plan')
    end=p.stat();need((s.st_ino,s.st_mtime_ns,s.st_size)==(end.st_ino,end.st_mtime_ns,end.st_size),'Input changed during hashing')
    return p

def linked(value,paths):
    if isinstance(value,dict):
        if set(value)=={'path','sha256'}:
            rel=value['path'];need(type(rel) is str and rel in paths and paths[rel]['sha256']==value['sha256'],'Unadmitted dependency')
        else:
            for v in value.values():linked(v,paths)
    elif isinstance(value,list):
        for v in value:linked(v,paths)

def inspect(root,plan):
    """Read-only, compute dependencies imported only when needed for validation."""
    root=existing_directory(root);paths,roles=validate_plan(plan);blocked=[];details={}
    for row in plan['sources']:
        if row['rights']!='LOCAL_USE_ATTESTED':blocked.append(dict(id=row['id'],reason='LOCAL_USE_NOT_ATTESTED'))
        try:
            p=pin_row(root,row);role=row['role'];info={}
            if role in ('manuscript','reference_pdf'):
                import fitz
                with fitz.open(p,filetype='pdf') as d:need(d.is_pdf and not d.needs_pass and 0<len(d)<=10000,'Invalid PDF');info={'pages':len(d)}
            elif role=='transcription_archive':
                # Preserve unsupported source notation literally; never feed it into alignment.
                need(row['bytes']<=64*1024**2,'Archive transcription quota')
                with p.open(encoding='utf-8-sig') as f:header=f.readline(1024).strip()
                need(re.fullmatch(r'#=IVTFF '+re.escape(row['scheme'])+r' 2\.0 M\s*[0-9]+',header),'Archive header mismatch')
                info=dict(header=header,runtime_eligible=False)
            elif role=='transcription':
                need(row['bytes']<=64*1024**2,'Transcription quota')
                import alignment
                scheme,_,info=alignment.load_source(p,row['sha256']);need(scheme==row['scheme'],'Transcription scheme mismatch')
            elif role in JSON_ROLES:
                value=c.load(p);need(type(value) is dict,'Expected JSON object')
                if role!='historical_result':linked(value,paths)
                if role=='inventory':need(value.get('convention')==row['scheme'],'Inventory scheme mismatch')
                if role=='recognition_policy':need(value.get('approval') is None,'RC1 intake may not authorize recognition')
                if role=='catalog_plan':need(value.get('reviewed') is False and any(x['sha256']==value.get('source_sha256') for x in roles.get('reference_pdf',[])),'Catalog plan lacks admitted PDF binding')
            elif role=='reference_sample':
                from PIL import Image
                with Image.open(p) as im:need(im.width*im.height<=4_000_000,'Reference image quota');im.verify()
            details[row['id']]=info
        except (ValueError,OSError,RuntimeError,KeyError,TypeError,ImportError) as exc:
            blocked.append(dict(id=row['id'],reason='SOURCE_VALIDATION_FAILED',error_type=type(exc).__name__))
    missing=missing_roles(roles)
    if not blocked:
        try:
            api=Desktop(root)
            if plan['catalog'] is not None:
                row=roles['visual_catalog'][0];cat=api.catalog(row['path'])
                need(cat and all(v['preview'] is True for v in cat.values()),'Only explicitly preview catalogs admitted at RC1 entry')
                raw=c.load(local(root,row['path']));scheme_rows={s['id']:s for s in raw['schemes']}
                for name,info in cat.items():
                    need(name in SCHEMES or name in VISUAL_SCHEMES,'Unsupported catalog scheme')
                    # Source-native previews can be browsed but never auto-map to runtime inventory IDs.
                    if name in VISUAL_SCHEMES or plan['scope']=='REAL_RESEARCH':
                        raw_scheme=scheme_rows[name];source_scheme=VISUAL_SCHEMES.get(name,name)
                        need(any(x['scheme']==source_scheme and x['sha256']==raw_scheme.get('source_sha256') for x in roles.get('reference_pdf',[])),'Catalog PDF provenance missing')
                        plans=[x for x in roles.get('catalog_plan',[]) if x['sha256']==raw_scheme.get('plan_sha256')]
                        need(len(plans)==1,'Catalog plan provenance missing')
                        source_plan=c.load(local(root,plans[0]['path']));need(source_plan['source_sha256']==raw_scheme['source_sha256'],'Catalog plan/PDF mismatch')
                        cells={(e['scheme'],e['label'],e['page'],tuple(e['box'])) for e in source_plan['entries']}
                        need(all((name,e['label'],s['page'],tuple(s['box'])) in cells for e in raw_scheme['entries'] for s in e['samples']),'Catalog sample not in source plan')
                    for samples in info['entries'].values():
                        for ref,_ in samples:need(ref['path'] in paths and paths[ref['path']]['role']=='reference_sample' and paths[ref['path']]['sha256']==ref['sha256'],'Unadmitted catalog sample')
                for scheme in SCHEMES:
                    if scheme not in cat:missing.append('visual_catalog:'+scheme)
            if plan['run_manifest'] is not None:
                row=roles['run_manifest'][0];v=c.load(local(root,row['path']));c.manifest(root,v)
                expected={'manuscript':'manuscript','groups':'groups','references':'references','model':'model_bundle','recognition_policy':'recognition_policy'}
                for key,role in expected.items():need(paths[v['inputs'][key]['path']]['role']==role,'Run input role mismatch')
                t=[paths[x['path']] for x in v['transcriptions']]
                need(all(x['role']=='transcription' for x in t) and set(x['scheme'] for x in t)==set(SCHEMES),'Run must bind both transcription conventions')
                policy=c.load(local(root,v['inputs']['recognition_policy']['path']));need(policy['approval'] is None,'Automatic acceptance prohibited')
                refs=c.load(local(root,v['inputs']['references']['path']))
                need(all(paths[x['alphabet']['path']]['role']=='inventory' for x in refs['inventories']),'Unadmitted inventory role')
                need({paths[x['alphabet']['path']]['scheme'] for x in refs['inventories']}==set(SCHEMES),'Both inventories required')
                models=c.load(local(root,v['inputs']['model']['path']))
                need(all(paths[x['model']['path']]['role']=='model' and paths[x['report']['path']]['role']=='model_report' for x in models['models']),'Model dependency role mismatch')
                if policy['mapping'] is not None:need(paths[policy['mapping']['path']]['role']=='mapping','Mapping role mismatch')
                api.manifest_info(row['path'])
                groups=c.load(local(root,v['inputs']['groups']['path']))
                pages=details[paths[v['inputs']['manuscript']['path']]['id']]['pages']
                need(type(groups) is dict and 1<=len(groups)<=213 and all(type(k) is str and k.isdecimal() and str(int(k))==k and 0<int(k)<=pages and type(g) is str and g.strip() for k,g in groups.items()),'Invalid physical page scope')
        except (ValueError,OSError,RuntimeError,KeyError,TypeError,ImportError) as exc:
            blocked.append(dict(id='dependencies',reason='DEPENDENCY_VALIDATION_FAILED',error_type=type(exc).__name__))
    return dict(schema=1,scope=plan['scope'],plan_sha256=c.digest(plan),status='BLOCKED' if blocked else 'INVENTORY_INCOMPLETE' if missing else 'INVENTORY_PASS',
                sources=len(paths),verified_sources=len(details),bytes=sum(r['bytes'] for r in paths.values()),blocked=blocked,missing=missing,
                run_contract_checked=plan['run_manifest'] is not None and not blocked,execution_authorized=False,scientific_status='UNADJUDICATED'),details

def copy_input(root,target,row):
    src=pin_row(root,row);dst=local(target,row['path']);dst.parent.mkdir(parents=True,exist_ok=True)
    with src.open('rb') as i,dst.open('xb') as o:
        h=hashlib.sha256();count=0
        for block in iter(lambda:i.read(1024**2),b''):
            count+=len(block);need(count<=row['bytes'],'Input grew during copy');h.update(block);o.write(block)
        o.flush();os.fsync(o.fileno())
    need(count==row['bytes'] and h.hexdigest()==row['sha256'],'Copy integrity mismatch');pin_row(root,row);pin_row(target,row)

def registry(root,plan,details):
    for row in plan['sources']:
        role=row['role']
        if role not in CORE:continue
        path=f"data/imports/index/{role}-{row['sha256']}.json"
        value=dict(role=role,path=row['path'],sha256=row['sha256'],details=details[row['id']])
        p=local(root,path);need(not p.exists(),'Registry collision');atomic_json(p,value)

def provision(source,intake,out,plan,approved,scope):
    source=existing_directory(source);intake=existing_directory(intake)
    need(plan['scope']==scope and scope in SCOPES,'Explicit matching intake scope required')
    c.digest_ok(approved);need(c.digest(plan)==approved,'Approval digest mismatch')
    out=destination(out,intake);destination(out,source)
    need(digest(local(source,'portable_sources.json'))==plan['application_sha256'],'Application source manifest mismatch')
    files=source_payload(source);report,details=inspect(intake,plan)
    need(not report['blocked'],'Blocked intake; inspect report')
    need(shutil.disk_usage(out.parent).free>=report['bytes']+sum(map(len,files.values())),'Insufficient free space')
    private_directory(out)
    try:
        for name,data in files.items():
            p=local(out,name);p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        need(digest(local(out,'portable_sources.json'))==plan['application_sha256'],'Copied source manifest mismatch');source_payload(out)
        for row in plan['sources']:copy_input(intake,out,row)
        after,actual=inspect(out,plan);need(after==report and actual==details,'Intake replay mismatch')
        registry(out,plan,details)
        api=Desktop(out);cfg=api.settings();cfg['project']='Voynich RC1' if scope=='REAL_RESEARCH' else 'SYNTHETIC RC1 fixture'
        if plan['catalog'] is not None:cfg['catalog']=next(r['path'] for r in plan['sources'] if r['id']==plan['catalog'])
        api.save_settings(cfg)
        atomic_json(local(out,PLAN),plan)
        receipt=dict(schema=1,scope=scope,plan_sha256=approved,application_sha256=plan['application_sha256'],status='PROVISIONED_INCOMPLETE' if report['missing'] else 'PROVISIONED',missing=report['missing'],sources=report['sources'],execution_authorized=False,scientific_status='UNADJUDICATED')
        atomic_json(local(out,RECEIPT),receipt)
        verify(out,approved,scope)
    except BaseException:
        shutil.rmtree(out);raise
    return receipt

def verify(root,approved,scope):
    root=existing_directory(root);c.digest_ok(approved)
    source_payload(root)
    plan=c.load(regular(root,PLAN)[0]);receipt=c.load(regular(root,RECEIPT)[0])
    need(plan['scope']==scope and c.digest(plan)==approved,'Admission identity mismatch')
    report,details=inspect(root,plan);need(not report['blocked'],'Admitted source or dependency changed')
    expected=dict(schema=1,scope=scope,plan_sha256=approved,application_sha256=plan['application_sha256'],status='PROVISIONED_INCOMPLETE' if report['missing'] else 'PROVISIONED',missing=report['missing'],sources=report['sources'],execution_authorized=False,scientific_status='UNADJUDICATED')
    need(receipt==expected,'Admission receipt mismatch')
    for row in plan['sources']:
        if row['role'] in CORE:
            path=f"data/imports/index/{row['role']}-{row['sha256']}.json"
            need(c.load(regular(root,path)[0])==dict(role=row['role'],path=row['path'],sha256=row['sha256'],details=details[row['id']]),'Source registry mismatch')
    return dict(status='VERIFIED',scope=scope,plan_sha256=approved,sources=report['sources'],missing=report['missing'],application_changed=digest(local(root,'portable_sources.json'))!=plan['application_sha256'],execution_authorized=False,scientific_status='UNADJUDICATED')

def starter(source,intake):
    source=existing_directory(source);intake=existing_directory(intake);source_payload(source)
    rows=[]
    def entry(rid,name,role,scheme,h,size,origin,edition):
        return dict(id=rid,path='data/rc1/'+name,role=role,scheme=scheme,sha256=h,bytes=size,origin=origin,edition=edition,rights='UNKNOWN',rights_basis='Owner local-use attestation required; no redistribution claim')
    for args in KNOWN_SOURCES:rows.append(entry(*args))
    path=local(intake,'data/rc1/IT2a-n.txt')
    if path.exists():
        p,s=regular(intake,'data/rc1/IT2a-n.txt');need(0<s.st_size<=64*1024**2,'Archive transcription quota')
        rows.append(entry('takahashi-it2a-original','IT2a-n.txt','transcription_archive','EvaT',digest(p),s.st_size,'Local copy; candidate origin https://voynich.nu/data/IT2a-n.txt','IT 2a; source edition to be verified'))
    result=dict(schema=1,scope='REAL_RESEARCH',application_sha256=digest(local(source,'portable_sources.json')),sources=rows,run_manifest=None,catalog=None)
    validate_plan(result);return result

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    q=sub.add_parser('starter');q.add_argument('intake',type=Path);q.add_argument('--source',type=Path,default=Path(__file__).resolve().parent)
    q=sub.add_parser('inspect');q.add_argument('intake',type=Path);q.add_argument('plan',type=Path)
    q=sub.add_parser('preview-catalog');q.add_argument('intake',type=Path);q.add_argument('plan',type=Path);q.add_argument('destination',type=Path);q.add_argument('--approve',required=True);q.add_argument('--scope',required=True,choices=SCOPES)
    q=sub.add_parser('provision');q.add_argument('intake',type=Path);q.add_argument('plan',type=Path);q.add_argument('destination',type=Path);q.add_argument('--source',type=Path,default=Path(__file__).resolve().parent);q.add_argument('--approve',required=True);q.add_argument('--scope',required=True,choices=SCOPES)
    q=sub.add_parser('verify');q.add_argument('root',type=Path);q.add_argument('--approve',required=True);q.add_argument('--scope',required=True,choices=SCOPES)
    a=p.parse_args()
    try:
        if a.action=='starter':print(json.dumps(starter(a.source,a.intake),indent=2,sort_keys=True));return 0
        if a.action=='inspect':value=inspect(a.intake,c.load(a.plan))[0]
        elif a.action=='preview-catalog':
            from vrs_rc1_catalog import build_preview
            value=build_preview(a.intake,a.destination,c.load(a.plan),a.approve,a.scope)
        elif a.action=='provision':value=provision(a.source,a.intake,a.destination,c.load(a.plan),a.approve,a.scope)
        else:value=verify(a.root,a.approve,a.scope)
    except (ValueError,OSError,RuntimeError,KeyError,TypeError,ImportError) as exc:
        print(json.dumps(dict(status='BLOCKED',error_type=type(exc).__name__,execution_authorized=False)));return 1
    print(json.dumps(value,indent=2,sort_keys=True));return int(value['status']=='BLOCKED')

if __name__=='__main__':raise SystemExit(main())

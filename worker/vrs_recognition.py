"""Prototype scoring: CPU selective policy; explicit CUDA candidate with CPU parity only."""
import math
from pathlib import Path
import vrs_contract as c
from vrs_core import require, sha
from vrs_exceptions import load_page, box_key


def inputs(root, manifest):
    import glyphs as g
    def read(ref): return load_page(c.artifact(root,ref))
    i=manifest['inputs']; refs=read(i['references']); bundle=read(i['model']); policy=read(i['recognition_policy'])
    c.fields(refs,('schema','inventories')); c.fields(bundle,('schema','models')); c.fields(policy,('schema','approval','mapping'))
    require(all(type(x['schema']) is int and x['schema']==1 for x in (refs,bundle,policy)),'Unsupported recognition schema')
    inventories={}; models={}
    require(type(refs['inventories']) is list and 1<=len(refs['inventories'])<=12,'Invalid inventories')
    for entry in refs['inventories']:
        c.fields(entry,('alphabet',)); path=c.artifact(root,entry['alphabet']); inv=g.inventory(path); name=inv['convention']
        require(name not in inventories and len(name)<=64,'Duplicate/invalid convention'); inventories[name]=(inv['labels'],entry['alphabet']['sha256'])
    require(type(bundle['models']) is list and 1<=len(bundle['models'])<=len(inventories),'Invalid model bundle')
    for entry in bundle['models']:
        c.fields(entry,('convention','model','report')); name=entry['convention']; require(name in inventories and name not in models,'Invalid model convention')
        m=read(entry['model']); report=read(entry['report']); labels,digest=inventories[name]
        require(m['version']==g.VERSION and m['labels']==labels and m['inventory_sha256']==digest and m['code_sha256']==sha(g.__file__) and m['thresholds']==[.12,.005] and report['model_sha256']==entry['model']['sha256'],'Model provenance mismatch')
        p=m['prototypes']; require(type(p) is list and len(p)==len(labels) and all(type(row) is list and len(row)==1024 and all(type(x) in (int,float) and math.isfinite(x) and 0<=x<=1 for x in row) for row in p),'Invalid prototypes')
        models[name]=p
    approval=None
    if policy['approval'] is not None:
        require(manifest['backend']!='cuda','CPU calibration cannot authorize CUDA candidate acceptance')
        approval=read(policy['approval']); c.fields(approval,('schema','model_sha256','references_sha256','classifier_sha256','backend','calibration','geometry','limits'))
        require(approval['schema']==1 and approval['model_sha256']==i['model']['sha256'] and approval['references_sha256']==i['references']['sha256'] and approval['classifier_sha256']==sha(g.__file__) and approval['backend']=='cpu','Approval binding mismatch')
        # Local owner-maintained trust file, never supplied by a manifest/remote request.
        trust=root/'config/vrs096-approved.json'
        require(not trust.is_symlink() and not trust.parent.is_symlink() and trust.resolve().is_relative_to(root),'Unsafe approval list')
        allowed=c.load(trust); c.fields(allowed,('schema','approvals')); require(allowed['schema']==1 and type(allowed['approvals']) is list and policy['approval']['sha256'] in allowed['approvals'],'Policy not locally approved')
        cal=read(approval['calibration']); c.fields(cal,('schema','model_sha256','references_sha256','classifier_sha256','backend','train_groups','holdout_groups','reviewers','rows'))
        require(cal['schema']==1 and all(cal[k]==approval[k] for k in ('model_sha256','references_sha256','classifier_sha256','backend')),'Calibration provenance mismatch')
        for k in ('train_groups','holdout_groups','reviewers'):
            require(type(cal[k]) is list and cal[k] and all(type(x) is str and x.strip() for x in cal[k]) and len(set(cal[k]))==len(cal[k]),'Invalid calibration provenance')
        require(not set(cal['train_groups'])&set(cal['holdout_groups']) and len(cal['reviewers'])>=2,'Independent calibration prerequisites absent')
        require(set(approval['limits'])==set(inventories)==set(models),'All conventions require calibrated models')
        seen=set(); totals={name:[0,0] for name in models}
        for name,limit in approval['limits'].items():
            c.fields(limit,('distance','margin','minimum_accepted','maximum_errors'))
            require(type(limit['distance']) in (int,float) and 0<=limit['distance']<=.12 and type(limit['margin']) in (int,float) and .005<=limit['margin']<=1,'Invalid frozen thresholds')
            c.number(limit['minimum_accepted']); c.number(limit['maximum_errors']); require(limit['minimum_accepted']>0 and limit['maximum_errors']<limit['minimum_accepted'],'Invalid calibration gate')
        for row in cal['rows']:
            c.fields(row,('id','convention','group','truth','prediction','distance','margin'))
            name=row['convention']; require(name in models and row['group'] in cal['holdout_groups'] and type(row['id']) is str and row['id'] and (name,row['id']) not in seen,'Invalid calibration row'); seen.add((name,row['id']))
            labels=inventories[name][0]; require(row['truth'] in labels+['unknown'] and row['prediction'] in labels,'Invalid calibration labels')
            score(row['distance'],row['margin']); limit=approval['limits'][name]
            if row['distance']<=limit['distance'] and row['margin']>=limit['margin']:
                totals[name][0]+=1; totals[name][1]+=row['truth']!=row['prediction']
        for name,(n,errors) in totals.items():
            limit=approval['limits'][name]; require(n>=limit['minimum_accepted'] and errors<=limit['maximum_errors'],'Calibration gate not met')
        geometry=read(approval['geometry']); c.fields(geometry,('schema','manuscript_sha256','occurrences'))
        require(geometry['schema']==1 and geometry['manuscript_sha256']==i['manuscript']['sha256'],'Geometry certification mismatch')
        eligible=set()
        for entry in geometry['occurrences']:
            c.fields(entry,('page','region_id','crop_sha256','box')); c.number(entry['page']); c.digest_ok(entry['crop_sha256']); require(entry['page']>0 and type(entry['region_id']) is str,'Invalid geometry certificate')
            key=(entry['page'],entry['region_id'],entry['crop_sha256'],box_key(entry['box'])); require(key not in eligible,'Duplicate geometry certificate'); eligible.add(key)
        approval={'limits':approval['limits'],'eligible':eligible}
    if policy['mapping'] is not None: c.artifact(root,policy['mapping'])
    return inventories,models,approval,policy['mapping']


def score(d,m):
    require(all(type(x) in (int,float) and math.isfinite(x) and 0<=x<=1 for x in (d,m)),'Invalid classifier scores')


def route(predictions, inventories, approval, key):
    require(set(predictions)<=set(inventories),'Unknown prediction convention')
    for name,row in predictions.items():
        c.fields(row,('label','distance','margin')); require(row['label'] in inventories[name][0],'Invalid prediction label'); score(row['distance'],row['margin'])
    if set(predictions)!=set(inventories): return 'ABSTAINED','UNSUPPORTED_INVENTORY'
    if any(r['distance']>.12 for r in predictions.values()): return 'ABSTAINED','OUT_OF_DISTRIBUTION'
    if any(r['margin']<.005 for r in predictions.values()): return 'ABSTAINED','LOW_CONFIDENCE'
    if approval is None: return 'ABSTAINED','UNKNOWN'
    if key not in approval['eligible']: return 'ABSTAINED','AMBIGUOUS_SEGMENTATION'
    if any(r['distance']>approval['limits'][n]['distance'] or r['margin']<approval['limits'][n]['margin'] for n,r in predictions.items()): return 'ABSTAINED','LOW_CONFIDENCE'
    return 'ACCEPTED','NONE'


def classify(boxes, image, inventories, models, backend='cpu'):
    import glyphs as g
    import torch
    from numpy import stack
    require(backend in ('cpu','cuda'),'Explicit supported classifier backend required')
    if not boxes: return []
    with torch.inference_mode():
        features=torch.from_numpy(stack([g.feature(image.crop(b)) for b in boxes]))
        if backend=='cuda': features=features.to('cuda:0')
        device='cuda:0' if backend=='cuda' else 'cpu'
        out=[{} for _ in boxes]
        for name,proto in models.items():
            p=torch.tensor(proto,dtype=torch.float32,device=device)
            for row,(i,d,m) in zip(out,g.classify(features,p)):
                row[name]=dict(label=inventories[name][0][i],distance=d,margin=m)
        return out


# Candidate GPU scoring never inherits the CPU calibration. Require exact label
# and abstention-reason parity plus the existing replay numerical tolerance.
def compare_candidate(cpu,gpu,inventories):
    require(len(cpu)==len(gpu),'CUDA parity denominator mismatch')
    for a,b in zip(cpu,gpu):
        require(set(a)==set(b),'CUDA parity convention mismatch')
        for name in a:
            x,y=a[name],b[name]
            score(x['distance'],x['margin']); score(y['distance'],y['margin'])
            require(x['label']==y['label'] and abs(x['distance']-y['distance'])<=1e-6
                    and abs(x['margin']-y['margin'])<=1e-6,'CUDA numerical/label parity mismatch')
        require(route(a,inventories,None,None)==route(b,inventories,None,None),'CUDA routing parity mismatch')
    return gpu


def candidate(boxes,image,inventories,models):
    # Same frozen feature extractor and classifier; GPU is not a fallback.
    cpu=classify(boxes,image,inventories,models,'cpu')
    gpu=classify(boxes,image,inventories,models,'cuda')
    return compare_candidate(cpu,gpu,inventories)

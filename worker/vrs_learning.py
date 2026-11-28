"""VRS-120/121/122/126: local frozen cohorts and controlled prototype updates.
No automatic activation, new research jobs or scientific approval.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import vrs_contract as c
from vrs_core import require, sha
from vrs_coordinator import inside, ref, write_new, scheduler_lock
from vrs_exceptions import load_page, box_key
import vrs_hardware as h

VERSION = '0.12.0'
SIDES = ('train','calibration','holdout')


def read(root, value):
    return load_page(c.artifact(root,value))


def code_identity():
    root=Path(__file__).resolve().parent
    return c.digest({'version':VERSION,'sources':{n:sha(root/n) for n in ('vrs_learning.py','glyphs.py','regions.py','vrs_surface.py','vrs_segmentation.py','alignment.py','worker.py','vrs_runtime.py','vrs_recognition.py','vrs_decisions.py','vrs_exceptions.py','vrs_operations.py','vrs_hardware.py')}})


def admit(root,backend,ram,disk,vram=0):
    info=h.snapshot(root,backend); work=dict(ram_base=0,ram_item=ram,vram_base=0,vram_item=max(1,vram) if backend=='cuda' else 0,disk=disk,items=1)
    selected=h.plan(info,work,backend); h.admit_next(info,selected,ram,vram if backend=='cuda' else 0,disk)


def device_info(backend):
    import torch
    import worker
    require(backend in ('cpu','cuda'),'Explicit backend required')
    if backend=='cuda':
        probe=h.cuda_probe(torch); 
        if not probe['ok']: raise h.ResourceBlocked(probe['reason'])
    info=worker.device_info(backend); require(info['device']==backend,'Backend mismatch')
    info['torch_threads']=torch.get_num_threads(); return info


def audit_run(root,run):
    """Wrap existing runtime without changing its algorithms or denominators."""
    from vrs_runtime import Runtime
    import vrs_recognition as rec
    app=Runtime(root)
    with app.ledger._tx() as db:
        row=app.ledger._row(db,'runs',run)
        require(row['worker']==app.identity and row['token'] is None,'Run identity/ownership mismatch')
        m,receipts,_=app.ledger._validate(row)
        inv,models,approval,_=rec.inputs(root,m)
        require(receipts['glyph_classification']['state']=='COMPLETED','Classification incomplete')
        app._verify_classification(run,m,receipts,inv,approval,models)
        snap,latest=app.decisions.snapshot(db,run)
        review=receipts['exception_review']
        if review['state']=='COMPLETED':
            data=read(root,review['artifact']); require(data['snapshot']==snap,'Review changed')
        result=dict(schema=1,module='glyph-research',run_id=run,manifest=m,receipts=receipts,review=snap,scientific_status='UNADJUDICATED')
    from vrs_operations import Operations
    aggregate=Operations(root).evidence(run)
    require(aggregate['review']==snap and all(aggregate['stages'][k]['artifact_sha256']==(v['artifact']['sha256'] if v['artifact'] else None) and aggregate['stages'][k]['state']==v['state'] for k,v in receipts.items()),'Run changed during audit')
    result['comparisons']=aggregate['comparisons']; return result


def replay_run(root,run,backend='cpu'):
    """Recompute proposals, boxes, scores and pinned alignment observations in isolation."""
    import tempfile
    import torch
    import worker
    import glyphs as g
    import regions
    import vrs_segmentation as segmentation
    import alignment
    import vrs_recognition as rec
    from PIL import Image
    evidence=audit_run(root,run); m=evidence['manifest']; receipts=evidence['receipts']
    info=device_info(backend)
    inv,models,approval,_=rec.inputs(root,m)
    r=read(root,receipts['script_regions']['artifact']); s=read(root,receipts['glyph_segmentation']['artifact']); p=read(root,receipts['glyph_classification']['artifact'])
    home=inside(root,'workspace/vrs120'); home.mkdir(parents=True,exist_ok=True)
    pages=0; boxes=0; scores=0; differences=0; max_delta=0.; alignment_n=0
    with tempfile.TemporaryDirectory(prefix='replay-',dir=home) as tmp:
        tmp=Path(tmp)
        for rr,ss,pp in zip(r['pages'],s['pages'],p['pages']):
            old=read(root,rr['manifest']); prior=read(root,ss['proposals']); outcome=read(root,pp['outcomes']); dest=tmp/f'p{rr["page"]}'
            width,height=old['page_dimensions'][str(rr['page'])]; largest=max(len(x[0]) for x in inv.values()); admit(root,backend,256*h.MIB+64*width*height+64*largest*1024*8,256*h.MIB+sum(c.artifact(root,dict(path=(c.artifact(root,rr['manifest']).parent.relative_to(root)/x['file']).as_posix(),sha256=x['sha256'])).stat().st_size for x in old['regions']),64*largest*1024*8+64*h.MIB)
            regions.propose(c.artifact(root,m['inputs']['manuscript']),m['inputs']['manuscript']['sha256'],c.artifact(root,m['inputs']['groups']),dest,pages=[rr['page']],isolate_yale='surface_policy' in old)
            fresh=load_page(dest/'manifest.json'); require(fresh==old,'Region replay mismatch'); pages+=1
            if 'dedup' in prior:
                replayed,lineage=segmentation.generate(fresh,lambda region:Image.open(dest/region['file']))
                require(replayed==prior['regions'] and lineage==prior['dedup'],'Segmentation/lineage replay mismatch')
            i=0
            for region,proposal in zip(fresh['regions'],prior['regions']):
                path=dest/region['file']; require(sha(path)==region['sha256'],'Replayed crop mismatch')
                with Image.open(path) as im:
                    b=proposal['boxes'] if 'dedup' in prior else g.boxes(im)
                    require(b==proposal['boxes'],'Segmentation replay mismatch'); boxes+=len(b)
                    for start in range(0,len(b),64):
                        chunk=b[start:start+64]; features=torch.tensor([g.feature(im.crop(x)).tolist() for x in chunk],dtype=torch.float32,device=backend)
                        actual=[{} for _ in chunk]
                        for name,proto in models.items():
                            with torch.inference_mode(): pred=g.classify(features,torch.tensor(proto,dtype=torch.float32,device=backend))
                            for a,(label,d,gap) in zip(actual,pred): a[name]=dict(label=inv[name][0][label],distance=d,margin=gap)
                        for box,a in zip(chunk,actual):
                            stored=outcome['rows'][i]; i+=1; require(stored['box']==box and stored['region_id']==region['id'],'Replay occurrence mismatch')
                            for name,values in a.items():
                                expected=stored['predictions'][name]; scores+=1; differences+=values['label']!=expected['label']; max_delta=max(max_delta,abs(values['distance']-expected['distance']),abs(values['margin']-expected['margin']))
                            differences+=rec.route(a,inv,approval,(rr['page'],region['id'],region['sha256'],box_key(box)))!=(stored['outcome'],stored['reason'])
            require(i==len(outcome['rows']),'Replay denominator mismatch')
        if receipts['transcription_alignment']['state']=='COMPLETED':
            idx=read(root,receipts['transcription_alignment']['artifact'])
            for j,(entry,source) in enumerate(zip(idx['reports'],m['transcriptions'])):
                obs=c.artifact(root,entry['observations']); old=read(root,entry['report']); new=tmp/f'alignment-{j}.json'
                if load_page(obs)['regions']:
                    alignment.compare(c.artifact(root,source),source['sha256'],obs,new); require(load_page(new)==old,'Alignment replay mismatch')
                else: require(old==dict(scientific_status='UNADJUDICATED',metrics=dict(COMPARED=0,UNRESOLVED=0),regions=[]),'Empty alignment mismatch')
                alignment_n+=1
    require(audit_run(root,run)==evidence,'Run changed during replay')
    return dict(backend=info,pages=pages,boxes=boxes,scores=scores,comparisons=alignment_n,decision_mismatches=differences,max_score_difference=max_delta,tolerance=1e-6,status='PASS' if not differences and max_delta<=1e-6 else 'FAIL',scientific_status='UNADJUDICATED')


def corrections(root,run,convention):
    """Only actual manual mapped dispositions; never auto predictions or self labels."""
    from vrs_runtime import Runtime
    import vrs_recognition as rec
    app=Runtime(root); evidence=audit_run(root,run)
    with app.ledger._tx() as db:
        row=app.ledger._row(db,'runs',run); require(row['token'] is None,'Active run')
        m,receipts,_=app.ledger._validate(row)
        snap,latest=app.decisions.snapshot(db,run)
        require(receipts==evidence['receipts'] and snap==evidence['review'],'Run changed')
        inv,_,_,_=rec.inputs(root,m); require(convention in inv,'Unknown convention')
        items=[]
        for r in db.execute('SELECT id,payload FROM vrs095_queue_items WHERE run_id=? ORDER BY id',(run,)):
            d=latest.get(r['id']); item=json.loads(r['payload'])
            if not d or d['kind']!='glyph' or d['mappings'][convention]['state']!='mapped': continue
            items.append(dict(candidate_id=r['id'],page=item['page'],region_id=item['region_id'],crop=item['crop'],box=item['box'],label=d['mappings'][convention]['label'],reviewer=d['reviewer'],revision=d['expected_revision']+1))
        return dict(manuscript=m['inputs']['manuscript'],inventory_sha256=inv[convention][1],decision_sha256=snap['decision_sha256'],items=items)


def freeze(root,plan):
    import glyphs as g
    from PIL import Image
    c.fields(plan,('schema','manuscript','alphabet','leaf_map','regions','annotations','corrections','limits','baseline','baseline_report','baseline_provenance'))
    require(type(plan['schema']) is int and plan['schema']==1,'Bad plan schema')
    c.artifact(root,plan['manuscript']); labels=g.inventory(c.artifact(root,plan['alphabet'])); scheme=labels['convention']; labels=labels['labels']
    leaf=read(root,plan['leaf_map']); c.fields(leaf,('schema','manuscript_sha256','pages','curators'))
    require(leaf['schema']==1 and leaf['manuscript_sha256']==plan['manuscript']['sha256'],'Leaf source mismatch')
    require(type(leaf['curators']) is list and len(set(leaf['curators']))>=2 and all(type(x) is str and x.strip() for x in leaf['curators']),'Two curator declarations required')
    leaves={}; splits={}
    for p,v in leaf['pages'].items():
        c.fields(v,('leaf','split')); require(str(int(p))==p and int(p)>0 and type(v['leaf']) is str and v['leaf'].strip() and v['split'] in SIDES,'Invalid leaf mapping')
        require(splits.setdefault(v['leaf'],v['split'])==v['split'],'Physical-leaf leakage'); leaves[int(p)]=v
    require(set(splits.values())==set(SIDES),'Three independent partitions required')
    import fitz
    with fitz.open(c.artifact(root,plan['manuscript'])) as pdf: require(max(leaves)<=len(pdf),'Page outside source')
    regions={}
    for rr in plan['regions']:
        path=c.artifact(root,rr); m=load_page(path)
        require(m['source_sha256']==plan['manuscript']['sha256'],'Region source mismatch')
        for r in m['regions']:
            key=(r['page'],r['id']); require(key not in regions and r['page'] in leaves and r['group']==leaves[r['page']]['leaf'],'Region leaf mismatch')
            crop=dict(path=(path.parent.relative_to(root)/r['file']).as_posix(),sha256=r['sha256']); c.artifact(root,crop); regions[key]=crop
    ann=read(root,plan['annotations']); c.fields(ann,('schema','reviewers','blind_declared','rows'))
    require(ann['schema']==1 and ann['blind_declared'] is True and type(ann['reviewers']) is list and len(ann['reviewers'])==2 and len(set(ann['reviewers']))==2 and all(type(x) is str and x.strip() for x in ann['reviewers']),'Independent blind reviewer declarations required')
    require(type(ann['rows']) is list and 1<=len(ann['rows'])<=4096,'Cohort exceeds local bounded profile')
    admit(root,'cpu',256*h.MIB+len(ann['rows'])*4096,32*h.MIB)
    rows=[]; seen=set(); fingerprints={}; crop_sides={}; excluded={s:0 for s in SIDES}; used=set()
    for row in ann['rows']:
        c.fields(row,('page','region_id','box','votes')); key=(row['page'],row['region_id']); crop=regions[key]; side=leaves[row['page']]['split']; box=box_key(row['box']); occurrence=(key,box)
        require(occurrence not in seen,'Duplicate occurrence'); seen.add(occurrence); used.add(key)
        require(crop_sides.setdefault(crop['sha256'],side)==side,'Exact crop leakage')
        with Image.open(c.artifact(root,crop)) as im:
            require(box[2]<=im.width and box[3]<=im.height,'Box outside crop'); feature=g.feature(im.crop(box))
        fp=hashlib.sha256(feature.tobytes()).hexdigest(); require(fingerprints.setdefault(fp,side)==side,'Normalized feature leakage')
        votes=row['votes']; require(type(votes) is list and len(votes)==2 and all(v in labels+['unknown','false_positive'] for v in votes),'Invalid votes')
        truth=votes[0] if votes[0]==votes[1] else None
        if truth is None: excluded[side]+=1
        rows.append(dict(page=row['page'],region_id=row['region_id'],crop=crop,box=list(box),leaf=leaves[row['page']]['leaf'],split=side,truth=truth,feature_sha256=fp,correction=False))
    require(used==set(regions),'Every supplied region requires annotation coverage')
    for entry in plan['corrections']:
        c.fields(entry,('run_id','decision_sha256','candidate_ids')); data=corrections(root,entry['run_id'],scheme)
        require(data['manuscript']==plan['manuscript'] and data['inventory_sha256']==plan['alphabet']['sha256'] and data['decision_sha256']==entry['decision_sha256'],'Correction provenance changed')
        ids=entry['candidate_ids']; require(type(ids) is list and ids and len(set(ids))==len(ids),'Invalid correction selection')
        found=set()
        for item in data['items']:
            if item['candidate_id'] not in ids: continue
            found.add(item['candidate_id']); key=(item['page'],item['region_id']); box=tuple(item['box']); matches=[r for r in rows if (r['page'],r['region_id'])==key and tuple(r['box'])==box]
            require(len(matches)==1,'Correction needs independently annotated geometry'); r=matches[0]
            require(r['split']=='train' and r['crop']==item['crop'] and r['truth']==item['label'] and item['reviewer'] not in ann['reviewers'] and not r['correction'],'Correction must agree with independent train-only review'); r['correction']=True
        require(found==set(ids),'Unresolved or nonmapped correction')
    for side in SIDES:
        require({r['truth'] for r in rows if r['split']==side and r['truth'] in labels}==set(labels),'Every partition needs every label')
    require(any(r['correction'] for r in rows),'No authorized correction examples')
    limits=plan['limits']; c.fields(limits,('distance','margin','min_accepted','max_risk','min_coverage'))
    require(type(limits['min_accepted']) is int and limits['min_accepted']>0,'Invalid minimum support')
    require(all(type(limits[k]) in (int,float) and math.isfinite(limits[k]) and 0<=limits[k]<=1 for k in ('distance','margin','max_risk','min_coverage')) and limits['distance']<=.12 and limits['margin']>=.005,'Invalid frozen risk limits')
    baseline=read(root,plan['baseline']); require(baseline['version']==g.VERSION and baseline['labels']==labels and baseline['inventory_sha256']==plan['alphabet']['sha256'] and baseline['code_sha256']==sha(g.__file__) and baseline['thresholds']==[.12,.005],'Baseline identity mismatch')
    require(read(root,plan['baseline_report'])['model_sha256']==plan['baseline']['sha256'],'Baseline report mismatch')
    provenance=read(root,plan['baseline_provenance']); c.fields(provenance,('schema','model_sha256','manuscript_sha256','training_leaves','training_feature_sha256','curator'))
    require(provenance['schema']==1 and provenance['model_sha256']==plan['baseline']['sha256'] and provenance['manuscript_sha256']==plan['manuscript']['sha256'] and type(provenance['curator']) is str and provenance['curator'].strip(),'Baseline provenance mismatch')
    require(type(provenance['training_leaves']) is list and provenance['training_leaves'] and set(provenance['training_leaves'])<=set(k for k,v in splits.items() if v=='train'),'Baseline training leaf leakage or unknown provenance')
    require(type(provenance['training_feature_sha256']) is list and provenance['training_feature_sha256'],'Baseline feature provenance required')
    for fp in provenance['training_feature_sha256']:
        c.digest_ok(fp); require(fingerprints.get(fp)=='train','Baseline feature leakage or unverified training feature')
    return dict(schema=1,plan_sha256=c.digest(plan),code_sha256=code_identity(),convention=scheme,labels=labels,rows=rows,excluded=excluded,limits=limits,scientific_status='UNADJUDICATED')


def tensors(root,rows,device):
    import glyphs as g
    import torch
    from PIL import Image
    features=[]
    for r in rows:
        with Image.open(c.artifact(root,r['crop'])) as im: f=g.feature(im.crop(r['box']))
        require(hashlib.sha256(f.tobytes()).hexdigest()==r['feature_sha256'],'Frozen feature changed'); features.append(f.tolist())
    return torch.tensor(features,dtype=torch.float32,device=device)


def fit(root,train,labels,device):
    import torch
    budget=256*h.MIB+len(train)*1024*40+64*len(labels)*1024*8
    admit(root,device,budget,32*h.MIB,budget)
    return torch.stack([tensors(root,[r for r in train if r['truth']==l],device).mean(0) for l in labels]).cpu().tolist()


def score(root,rows,labels,proto,limits,device):
    import glyphs as g
    import torch
    budget=256*h.MIB+64*len(labels)*1024*8
    admit(root,device,budget,32*h.MIB,budget)
    p=torch.tensor(proto,dtype=torch.float32,device=device)
    require(p.shape==(len(labels),1024) and bool(torch.isfinite(p).all()) and bool(((p>=0)&(p<=1)).all()),'Invalid prototypes')
    out=[]
    with torch.inference_mode():
        for i in range(0,len(rows),64):
            batch=rows[i:i+64]
            for r,(k,d,m) in zip(batch,g.classify(tensors(root,batch,device),p)):
                require(math.isfinite(d) and math.isfinite(m),'Invalid scores')
                out.append(dict(truth=r['truth'],prediction=labels[k],distance=d,margin=m,accepted=d<=limits['distance'] and m>=limits['margin']))
    return out


def metrics(rows):
    valid=[r for r in rows if r['truth'] is not None]; accepted=[r for r in valid if r['accepted']]; errors=sum(r['truth']!=r['prediction'] for r in accepted)
    return dict(total=len(rows),excluded=len(rows)-len(valid),eligible=len(valid),accepted=len(accepted),abstained=len(valid)-len(accepted),errors=errors,correct=len(accepted)-errors,accuracy_including_abstention=(len(accepted)-errors)/len(valid) if valid else None,coverage=len(accepted)/len(valid) if valid else 0,selective_risk=errors/len(accepted) if accepted else None)


def passes(new,old,limits):
    return new['accepted']>=limits['min_accepted'] and new['coverage']>=max(old['coverage'],limits['min_coverage']) and new['selective_risk'] is not None and new['selective_risk']<=limits['max_risk'] and (old['selective_risk'] is None or new['selective_risk']<=old['selective_risk'])


def evaluate(root,plan,device='cpu'):
    """Explicit one-shot evaluation; reserve holdout before any scoring."""
    import torch
    import glyphs as g
    import worker
    info=device_info(device)
    frozen=freeze(root,plan)
    trust=c.load(inside(root,'config/vrs120-training.json')); c.fields(trust,('schema','plans'))
    require(trust['schema']==1 and frozen['plan_sha256'] in trust['plans'],'Explicit local training approval required')
    rows=frozen['rows']; labels=frozen['labels']; limits=frozen['limits']
    # All sources for this manuscript and convention share a conservative one-use gate.
    key=c.digest(dict(manuscript=plan['manuscript']['sha256'],alphabet=plan['alphabet']['sha256']))
    base=inside(root,'workspace/vrs120'); base.mkdir(parents=True,exist_ok=True)
    dest=inside(root,f'workspace/vrs120/{key}'); dest.mkdir(exist_ok=False)
    write_new(dest/'reservation.json',dict(plan_sha256=frozen['plan_sha256'],backend=device,scientific_status='UNADJUDICATED'))
    write_new(dest/'cohort.json',frozen)
    baseline=read(root,plan['baseline']); old=baseline['prototypes']; train=[r for r in rows if r['split']=='train' and r['truth'] in labels]
    # Fixed equal-weight class means; only consensus train observations including approved corrections.
    proto=fit(root,train,labels,device)
    model=dict(baseline,prototypes=proto); write_new(dest/'model.json',model)
    report=dict(schema=1,scientific_status='UNADJUDICATED',backend=info,cohort=ref(root,dest/'cohort.json'),baseline=plan['baseline'],baseline_report=plan['baseline_report'],model=ref(root,dest/'model.json'),model_sha256=sha(dest/'model.json'),code_sha256=code_identity(),partitions={},training_counts={l:sum(r['truth']==l for r in train) for l in labels},correction_count=sum(r['correction'] for r in train),gate='NOT_MET')
    for side in ('calibration','holdout'):
        batch=[r for r in rows if r['split']==side]
        a=score(root,batch,labels,old,limits,device); b=score(root,batch,labels,proto,limits,device)
        item=dict(baseline=metrics(a),candidate=metrics(b),baseline_rows=a,candidate_rows=b)
        report['partitions'][side]=item
        if side=='calibration' and not passes(item['candidate'],item['baseline'],limits): break
    if 'holdout' in report['partitions'] and all(passes(v['candidate'],v['baseline'],limits) for v in report['partitions'].values()): report['gate']='ELIGIBLE_FOR_MANUAL_REVIEW'
    write_new(dest/'report.json',report); return ref(root,dest/'report.json')


def compare(root,plan,report_ref,backend='cpu'):
    """Read-only replay of the frozen candidate; no retraining or new holdout tuning."""
    import worker
    info=device_info(backend)
    report=read(root,report_ref); frozen=freeze(root,plan)
    require(frozen==read(root,report['cohort']) and report['code_sha256']==code_identity(),'Replay binding mismatch')
    model=read(root,report['model']); require(report['model_sha256']==report['model']['sha256'],'Model hash mismatch')
    require(report['baseline']==plan['baseline'] and report['baseline_report']==plan['baseline_report'],'Replay baseline mismatch')
    train=[r for r in frozen['rows'] if r['split']=='train' and r['truth'] in frozen['labels']]; reconstructed=fit(root,train,frozen['labels'],backend)
    delta=max(abs(x-y) for a,b in zip(reconstructed,model['prototypes']) for x,y in zip(a,b))
    base=read(root,report['baseline']); deviations=0; maximum=0.; n=0
    for side,item in report['partitions'].items():
        rows=[r for r in frozen['rows'] if r['split']==side]
        for name,proto in (('baseline',base['prototypes']),('candidate',model['prototypes'])):
            actual=score(root,rows,frozen['labels'],proto,frozen['limits'],backend); expected=item[name+'_rows']; require(len(actual)==len(expected),'Replay denominator mismatch')
            require(metrics(expected)==item[name],'Stored metric mismatch')
            for a,b in zip(actual,expected):
                n+=1; maximum=max(maximum,abs(a['distance']-b['distance']),abs(a['margin']-b['margin']))
                deviations+=any(a[k]!=b[k] for k in ('truth','prediction','accepted'))
    return dict(backend=info,rows=n,decision_mismatches=deviations,max_score_difference=maximum,prototype_max_difference=delta,tolerance=1e-6,status='PASS' if n and not deviations and max(maximum,delta)<=1e-6 else 'FAIL',scientific_status='UNADJUDICATED')


def selection(root,report_ref,action):
    """Local selection history only; does not change any existing manifest or approval."""
    report=read(root,report_ref); require(report['gate']=='ELIGIBLE_FOR_MANUAL_REVIEW','Candidate not eligible')
    path=c.artifact(root,report_ref); require(path.name=='report.json' and path.parent.parent==inside(root,'workspace/vrs120'),'Report not generated in learning workspace')
    frozen=read(root,report['cohort']); reservation=c.load(path.parent/'reservation.json')
    require(reservation['plan_sha256']==frozen['plan_sha256'] and report['code_sha256']==code_identity() and set(report['partitions'])=={'calibration','holdout'},'Report provenance mismatch')
    for item in report['partitions'].values():
        require(all(metrics(item[k+'_rows'])==item[k] for k in ('candidate','baseline')) and passes(item['candidate'],item['baseline'],frozen['limits']),'Report gate mismatch')
    c.artifact(root,report['model']); c.artifact(root,report['baseline']); c.artifact(root,report['cohort']); require(read(root,report['baseline_report'])['model_sha256']==report['baseline']['sha256'],'Baseline report mismatch')
    home=inside(root,'workspace/vrs120'); trust=read(root,ref(root,inside(root,'config/vrs120-approved.json')))
    c.fields(trust,('schema','reports')); require(trust['schema']==1 and report_ref['sha256'] in trust['reports'],'Explicit local approval required')
    require(action in ('select','rollback'),'Invalid action')
    with scheduler_lock(inside(root,'workspace/vrs120/selection.lock')):
        dest=home/'selections'; dest.mkdir(exist_ok=True); entries=sorted(dest.glob('*.json')); n=len(entries)
        if n: prior=read(root,ref(root,entries[-1])); require(prior['report']==report_ref,'Different report history; explicit migration required')
        require((action=='select' and (not n or prior['action']=='rollback')) or (action=='rollback' and n and prior['action']=='select'),'Invalid selection transition')
        result=dict(schema=1,action=action,report=report_ref,model=report['model'] if action=='select' else report['baseline'],previous=ref(root,entries[-1]) if n else None,scientific_status='UNADJUDICATED')
        result['bundle_entry']=dict(convention=frozen['convention'],model=result['model'],report=report_ref if action=='select' else report['baseline_report'])
        write_new(dest/f'{n+1:08d}.json',result); return result


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('root',type=Path); p.add_argument('action',choices=('audit','replay-run','corrections','freeze','evaluate','compare','select','rollback')); p.add_argument('value'); p.add_argument('--report'); p.add_argument('--convention'); p.add_argument('--backend',choices=('cpu','cuda'),default='cpu'); a=p.parse_args(); root=a.root.resolve(strict=True)
    if a.action=='audit': result=audit_run(root,a.value)
    elif a.action=='replay-run': result=replay_run(root,a.value,a.backend)
    elif a.action=='corrections': result=corrections(root,a.value,a.convention)
    elif a.action in ('select','rollback'): result=selection(root,ref(root,inside(root,a.value)),a.action)
    else:
        plan=load_page(inside(root,a.value))
        if a.action=='freeze': result=freeze(root,plan)
        elif a.action=='evaluate': result=evaluate(root,plan,a.backend)
        else: result=compare(root,plan,ref(root,inside(root,a.report)),a.backend)
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__': main()

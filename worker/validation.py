"""v0.7 local, pinned validation of the guided image-to-notation chain."""
import argparse
import collections
import json
import shutil
from pathlib import Path
import alignment as a
import glyphs as g
import pipeline as p
import regions as r
import worker as w

VERSION = '0.7.0'
INPUTS = {'pdf','review_csv','groups','manifest','script_left','script_right',
          'glyph_left','glyph_right','alphabet','split','mapping','transcription'}


def inputs(plan):
    plan=Path(plan); obj=w.read(plan)
    w.require(set(obj)=={'schema','scope','inputs','settings'} and obj['schema']==1 and obj['scope'] in ('synthetic','manuscript'),'Invalid validation plan')
    w.require(set(obj['inputs']) in (INPUTS,INPUTS|{'page_reference'}),'Missing or unexpected input')
    paths={}
    for key,entry in obj['inputs'].items():
        w.require(set(entry)=={'path','sha256'} and isinstance(entry['path'],str) and not Path(entry['path']).is_absolute(),'Invalid input path')
        path=w.within(plan.parent,entry['path']); w.require(path.is_file() and w.sha(path)==entry['sha256'],'Input hash mismatch: '+key); paths[key]=path
    cfg=obj['settings']; w.require(set(cfg)=={'device','epochs','batch','seed'} and cfg['device'] in ('cpu','cuda'),'Explicit validation device required')
    w.require(type(cfg['epochs']) is int and 1<=cfg['epochs']<=50 and type(cfg['batch']) is int and 1<=cfg['batch']<=64 and type(cfg['seed']) is int and 0<=cfg['seed']<2**32,'Invalid frozen training settings')
    return obj,paths


def preflight(plan):
    obj,x=inputs(plan); m=w.dataset(x['manifest']); digest=w.sha(x['manifest']); source_hash=w.sha(x['transcription'])
    w.require(m['source_sha256']==w.sha(x['pdf']) and m['review_sha256']==w.sha(x['review_csv']) and m['groups_sha256']==w.sha(x['groups']),'Guided manifest source mismatch')
    sets,excluded=w.cohorts(x['manifest'],x['script_left'],x['script_right'],x['split'])
    labels,_,_,_=g.cohorts(x['manifest'],x['glyph_left'],x['glyph_right'],x['alphabet'],x['split'])
    scheme,reference,_=a.load_source(x['transcription'],source_hash)
    w.require(g.inventory(x['alphabet'])['convention']==scheme,'Validation requires native convention; no silent conversion')
    for label in labels: a.units(label,scheme)
    test=set(w.read(x['split'])['test']); held=[v for v in m['regions'] if v['group'] in test]
    groupmap=w.read(x['groups']); page_side={}; seen_hashes={}
    for v in m['regions']:
        w.require(groupmap.get(str(v['page']))==v['group'],'Physical group map mismatch')
        side=v['group'] in test
        w.require(page_side.setdefault(v['page'],side)==side,'Same page across split')
        w.require(v['sha256'] not in seen_hashes,'Duplicate crop within validation cohort'); seen_hashes[v['sha256']]=side
    positives={v['id'] for side in sets.values() for v,y in side if y==1}
    left,right=w.read(x['glyph_left']),w.read(x['glyph_right'])
    for v in m['regions']:
        rid=v['id']
        if left['regions'][rid]['status']=='single_line' and left['regions'][rid]==right['regions'][rid]:
            w.require(rid in positives,'Agreed glyph line lacks agreed script label')
    maps=w.read(x['mapping']); entries=maps['regions']
    w.require(maps['manifest_sha256']==digest and maps['source_sha256']==source_hash and maps['scheme']==scheme,'Frozen locus map mismatch')
    w.require(set(entries)=={v['id'] for v in held},'Map must cover every held-out crop only')
    confirmed=set(); eligible=set(); reasons=collections.Counter()
    for v in held:
        rid=v['id']; e=entries[rid]
        w.require(e['page']==v['page'] and e['group']==v['group'],'Physical map page/group mismatch')
        if rid not in positives: reasons['not_agreed_script']+=1; continue
        if e.get('mapping_status')!='confirmed' or e.get('scope')!='complete_locus' or not str(e.get('mapper') or '').strip(): reasons['mapping_unconfirmed']+=1; continue
        key=e.get('locus'); w.require(isinstance(key,str) and key not in confirmed,'Duplicate confirmed held-out locus'); confirmed.add(key)
        if key not in reference or reference[key]['subtype']!=e.get('subtype') or reference[key]['units'] is None: reasons['reference_unresolved']+=1; continue
        eligible.add(rid)
    if 'page_reference' in x:
        ref=w.read(x['page_reference']); pages={str(v['page']) for v in held}
        w.require(ref.get('exhaustive') is True and isinstance(ref.get('reviewer'),str) and ref['reviewer'].strip(),'Exhaustive page reference declaration required')
        w.require(ref['source_sha256']==w.sha(x['pdf']) and ref['groups_sha256']==w.sha(x['groups']) and set(ref['pages'])==pages,'Page reference must cover exact held-out pages')
        w.require(all(isinstance(boxes,list) and all(r.valid_box(b) for b in boxes) and len(set(map(tuple,boxes)))==len(boxes) for boxes in ref['pages'].values()),'Invalid page reference boxes')
    return obj,x,m,held,entries,eligible,dict(reasons),excluded


def holdout_copy(manifest, m, held, out):
    out.mkdir(); (out/'crops').mkdir(); records=[]
    for v in held:
        name='crops/'+v['sha256']+'.png'; shutil.copyfile(w.within(Path(manifest).parent,v['file']),out/name)
        records.append(dict(v,file=name))
    target=out/'manifest.json'; w.write(target,dict(m,regions=records)); w.dataset(target); return target


def track(manifest, pred, model, alphabet, entries, source, out, eligible, allowed=None):
    out.mkdir(); data=w.read(pred)
    if allowed is not None: data['rows']=[v for v in data['rows'] if v['region_id'] in allowed]
    predfile=out/'predictions.json'; w.write(predfile,data)
    scheme=g.inventory(alphabet)['convention']; source_hash=w.sha(source); mapfile=out/'mapping.json'
    w.write(mapfile,dict(manifest_sha256=w.sha(manifest),source_sha256=source_hash,scheme=scheme,alphabet_sha256=w.sha(alphabet),prediction_sha256=w.sha(predfile),regions={k:dict(v) if k in eligible else dict(v,mapping_status='ineligible') for k,v in entries.items()}))
    obs=out/'observations.json'; report=out/'comparison.json'
    a.prepare(manifest,predfile,alphabet,model,mapfile,source,source_hash,obs); a.compare(source,source_hash,obs,report)
    rows=[v for v in w.read(report)['regions'] if v['region_id'] in eligible]; n=len(eligible)
    exact=sum(v.get('exact_notation_agreement',False) for v in rows); compared=sum(v['status']=='COMPARED' for v in rows)
    return dict(eligible=n,compared=compared,exact=exact,not_compared=n-compared,ambiguous=sum(v.get('ambiguous_optimum',False) for v in rows),exact_fraction_all_eligible=exact/n if n else None,comparison_sha256=w.sha(report))


def run(plan,out):
    frozen=w.sha(plan); obj,x,m,held,entries,eligible,reasons,excluded=preflight(plan); out=Path(out)
    w.require(w.sha(plan)==frozen,'Plan changed during preflight')
    w.require(not out.exists(),'Validation output already exists; no overwrite or rescore')
    out.mkdir(parents=True); w.write(out/'plan_snapshot.json',obj); code={Path(v.__file__).name:w.sha(v.__file__) for v in (w,p,g,a,r)}; code['validation.py']=w.sha(__file__)
    w.write(out/'run.json',dict(state='RUNNING',plan_sha256=frozen,scope=obj['scope'],code_sha256=code))
    cfg=obj['settings']; device=cfg['device']
    # Recreate source crops rather than accepting a self-consistent but unverified manifest.
    w.prepare(x['pdf'],w.sha(x['pdf']),x['review_csv'],x['groups'],out/'verified')
    verified=out/'verified/manifest.json'; w.require(w.sha(verified)==w.sha(x['manifest']),'Recreated source manifest mismatch')
    w.dataset(verified)
    script=w.train(verified,x['script_left'],x['script_right'],x['split'],out/'script',**cfg)
    glyph=g.train(verified,x['glyph_left'],x['glyph_right'],x['alphabet'],x['split'],out/'glyph',device)
    hold=holdout_copy(verified,m,held,out/'heldout')
    p.predict(hold,out/'script/checkpoint.pt',out/'script/report.json',out/'script_inference',device=device,batch=cfg['batch'])
    prediction=w.read(out/'script_inference/predictions.json'); allowed={v['id'] for v in prediction['rows'] if v['label']=='script'}
    # Test-time geometry comes only from pixels, not the held-out reference boxes.
    projected=out/'projection.json'; g.propose(hold,projected,'automatic-projection-not-human',x['alphabet'])
    review=w.read(projected)
    for v in review['regions'].values(): v['status']='single_line' if v['glyphs'] else 'reject'
    w.write(projected,review)
    model=out/'glyph/glyph_model.json'; pred=out/'glyph_predictions.json'
    result=g.predict(hold,projected,x['alphabet'],model,out/'glyph/glyph_report.json',pred,device)
    # Only the frozen held-out cohort is scored. The ungated path is diagnostic.
    gated=track(hold,pred,model,x['alphabet'],entries,x['transcription'],out/'gated',eligible,allowed)
    diagnostic=track(hold,pred,model,x['alphabet'],entries,x['transcription'],out/'ungated',eligible)
    localization={'status':'BLOCKED_NO_EXHAUSTIVE_PAGE_REFERENCE'}
    if 'page_reference' in x:
        pages=sorted({v['page'] for v in held}); loc=out/'localization'
        r.propose(x['pdf'],w.sha(x['pdf']),x['groups'],loc,pages=pages)
        scored=r.evaluate(loc/'manifest.json',x['page_reference'],out/'localization_report.json')
        localization=dict(status='COMPARED',metrics={k:{a:b for a,b in v.items() if a!='pages'} for k,v in scored['metrics'].items()},report_sha256=w.sha(out/'localization_report.json'))
    w.require(w.sha(plan)==frozen,'Plan changed during run'); inputs(plan); w.dataset(x['manifest'])
    report=dict(version=VERSION,technical_status='COMPLETED',scientific_status='UNADJUDICATED',scope=obj['scope'],plan_sha256=frozen,code_sha256=code,device=device,
        heldout_regions=len(held),script_counts=script['counts'],script_exclusions=excluded,script_prediction_counts=prediction['counts'],
        glyph_reference_box_accuracy=glyph['accuracy_including_unknown'],glyph_reference_box_test_n=glyph['test_n'],glyph_reference_box_exclusions=glyph['excluded_regions'],
        projection_candidates=len(result['rows']),projection_unknown=sum(v['predicted']=='unknown' for v in result['rows']),mapping_exclusions=reasons,
        gated=gated,ungated_diagnostic=diagnostic,localization=localization,limitations=['Guided crop recognition and optional full-page proposal evaluation are separate tracks','Reviewer independence and mapping correctness are declarations','No near-duplicate guarantee or calibrated scientific gate','Reference-box glyph metric is not end-to-end accuracy'])
    w.write(out/'validation_report.json',report); w.write(out/'run.json',dict(state='COMPLETED',plan_sha256=frozen,report_sha256=w.sha(out/'validation_report.json'))); return report


def probe(pdf,expected_sha,groups,out,pages):
    """Real source engineering probe, no labels and no accuracy claim."""
    from PIL import Image
    out=Path(out); summary=r.propose(pdf,expected_sha,groups,out,pages=pages)
    manifest=out/'manifest.json'; m=w.dataset(manifest); counts=collections.Counter({str(page):0 for page in pages}); projections=collections.Counter({str(page):0 for page in pages})
    for v in m['regions']:
        key=str(v['page']); counts[key]+=1
        with Image.open(w.within(out,v['file'])) as im: projections[key]+=len(g.boxes(im))
    report=dict(version=VERSION,scope='real_source_engineering_probe',scientific_status='BLOCKED_NO_INDEPENDENT_LABELS',source_sha256=expected_sha,groups_sha256=w.sha(groups),manifest_sha256=w.sha(manifest),code_sha256={Path(v.__file__).name:w.sha(v.__file__) for v in (w,g,r)},pages=pages,screened=summary['screened'],proposal_counts=dict(counts),projection_run_counts=dict(projections),note='Overlapping ink windows and projection runs, not distinct glyphs or text detections.')
    w.write(out/'probe_report.json',report); return report


def main():
    cli=argparse.ArgumentParser(description=__doc__); sub=cli.add_subparsers(dest='cmd',required=True)
    q=sub.add_parser('run'); q.add_argument('plan'); q.add_argument('out')
    q=sub.add_parser('probe'); q.add_argument('pdf'); q.add_argument('expected_sha'); q.add_argument('groups'); q.add_argument('out'); q.add_argument('--pages',nargs='+',type=int,required=True)
    args=vars(cli.parse_args()); cmd=args.pop('cmd'); print(json.dumps({'run':run,'probe':probe}[cmd](**args),indent=2))


if __name__=='__main__': main()

"""v0.6: conservative IVTFF subset parsing and local glyph-to-locus alignment."""
import argparse
import collections
import json
import hashlib
import re
from pathlib import Path
import worker as w

VERSION = '0.6.0'
HEADER = re.compile(r'#=IVTFF (Eva-|STA1) 2\.0 M\s*([0-9]+)\s*')
LOCUS = re.compile(r'^<(f(?:\d+[rv]\d*|Ros)\.\d+),([^>]+)>\s*(.*?)\s*$')
UNIT = {'Eva-': re.compile(r'[a-z]|@[0-9]{3};|\{(?:[a-z\x27]|@[0-9]{3};)+\}|\x27'),
        'STA1': re.compile(r'[A-X][A-Za-z0-9]')}


def units(text, scheme, separators=False):
    """Strict notation units, NOT physical glyphs. No editorial normalization."""
    pat = UNIT[scheme]; result = []; i = 0
    while i < len(text):
        if separators and text[i] == '.':
            i += 1; continue
        m = pat.match(text, i)
        if not m: raise ValueError('Unsupported or uncertain notation')
        result.append(m.group()); i = m.end()
    w.require(bool(result), 'Empty notation')
    return result


def load_source(path, expected_sha):
    w.require(w.sha(path) == expected_sha, 'Transcription SHA256 mismatch')
    lines = Path(path).read_text(encoding='utf-8-sig').splitlines()
    w.require(bool(lines), 'Empty source'); head = HEADER.fullmatch(lines[0]); w.require(head is not None, 'Unsupported IVTFF header')
    scheme = head[1]; rows = {}; ignored = collections.Counter()
    for line in lines[1:]:
        if not line.strip() or line.startswith('#'): continue
        m = LOCUS.fullmatch(line)
        if not m:
            if re.fullmatch(r'<f(?:\d+[rv]\d*|Ros)>\s*.*', line): ignored['page_header'] += 1; continue
            raise ValueError('Unsupported record syntax; parser scope must be extended explicitly')
        key, subtype, raw = m.groups()
        w.require(key not in rows, 'Duplicate locus: ' + key)
        # Only known leading/trailing paragraph delimiters; all other tags are unresolved.
        text = re.sub(r'^<%>', '', raw); text = re.sub(r'<\$>$', '', text)
        try:
            w.require(not text.startswith('.') and not text.endswith('.') and '..' not in text, 'Invalid separator')
            tokens = units(text, scheme, separators=True); reason = None
        except ValueError:
            tokens = None; reason = 'editorial_or_unsupported_notation'
        rows[key] = dict(subtype=subtype, units=tokens, reason=reason)
    w.require(bool(rows), 'No locus records')
    return scheme, rows, dict(version=VERSION, source_sha256=expected_sha, header=lines[0], loci=len(rows), strict=sum(r['units'] is not None for r in rows.values()), unresolved=sum(r['units'] is None for r in rows.values()), ignored=dict(ignored))


def audit_common(inputs):
    """Source-local aggregate audit; never exports transcription strings."""
    w.require(2<=len(inputs)<=8,'Supply two to eight pinned sources')
    rows=[]; summaries=[]
    for path,sha in inputs:
        _,r,summary=load_source(path,sha); rows.append(r); summaries.append(summary)
    w.require(len({s['source_sha256'] for s in summaries})==len(summaries),'Duplicate source bytes')
    common=set.intersection(*(set(r) for r in rows))
    same={k for k in common if len({r[k]['subtype'] for r in rows})==1}
    strict={k for k in same if all(r[k]['units'] is not None for r in rows)}
    return dict(version=VERSION,scientific_status='UNADJUDICATED',sources=summaries,common_loci=len(common),common_subtype=len(same),strict_common=len(strict),code_sha256=w.sha(__file__))


def align(observed, reference):
    """Minimum edit cost; candidate spans may consume multiple notation units.
    Unknown costs one, never credited as match. Multiple optimal paths are flagged.
    """
    n, m = len(observed), len(reference)
    w.require(0 < n <= 512 and 0 < m <= 1024, 'Alignment size outside bound')
    inf = n + m + 1; cost = [[inf]*(m+1) for _ in range(n+1)]; ways = [[0]*(m+1) for _ in range(n+1)]; prev = {}
    cost[0][0] = 0; ways[0][0] = 1
    def push(i,j,ni,nj,delta,op):
        v = cost[i][j]+delta
        if v < cost[ni][nj]:
            cost[ni][nj]=v; ways[ni][nj]=ways[i][j]; prev[ni,nj]=(i,j,op)
        elif v == cost[ni][nj]: ways[ni][nj]=min(2,ways[ni][nj]+ways[i][j])
    for i in range(n+1):
        for j in range(m+1):
            if not ways[i][j]: continue
            if j < m: push(i,j,i,j+1,1,'missing_observation')
            if i == n: continue
            choices = observed[i]
            if j < m:
                if not choices: push(i,j,i+1,j+1,1,'unknown')
                else:
                    for seq in choices:
                        k=len(seq)
                        if j+k <= m and list(seq)==reference[j:j+k]:
                            push(i,j,i+1,j+k,0,'match' if len(choices)==1 else 'alternative_match')
                    if not any(list(seq)==reference[j:j+len(seq)] for seq in choices): push(i,j,i+1,j+1,1,'substitution')
            push(i,j,i+1,j,1,'extra_observation')
    ambiguous=ways[n][m]>1; steps=[]; i,j=n,m
    if not ambiguous:
        while i or j:
            a,b,op=prev[i,j]; steps.append(dict(observed=[a,i],reference=[b,j],operation=op)); i,j=a,b
        steps.reverse()
    return dict(cost=cost[n][m],ambiguous_optimum=ambiguous,steps=steps if not ambiguous else None,
                exact_notation_agreement=cost[n][m]==0 and not ambiguous and all(s['operation']=='match' for s in steps))


def compare(source, expected_sha, observations, output):
    scheme,rows,summary=load_source(source,expected_sha); obj=w.read(observations)
    w.require(obj['schema']==1 and obj['scheme']==scheme and obj['source_sha256']==expected_sha,'Observation convention/source mismatch')
    w.require(re.fullmatch(r'[0-9a-f]{64}',obj['manifest_sha256']) is not None and re.fullmatch(r'[0-9a-f]{64}',obj['prediction_sha256']) is not None,'Missing observation provenance')
    regions=obj['regions']; w.require(isinstance(regions,list) and bool(regions),'No observations')
    w.require(len({r['region_id'] for r in regions})==len(regions),'Duplicate region')
    out=[]
    for r in regions:
        rid=r['region_id']; key=r.get('locus'); confirmed=r.get('mapping_status')=='confirmed' and r.get('scope')=='complete_locus' and isinstance(r.get('mapper'),str) and r['mapper'].strip()
        result=dict(region_id=rid,locus=key,status='UNRESOLVED')
        if not confirmed: result['reason']='physical_mapping_not_confirmed'
        elif r.get('unresolved_compounds',0): result['reason']='segmentation_requires_review'
        elif key not in rows: result['reason']='locus_not_found'
        elif rows[key]['subtype']!=r.get('subtype'): result['reason']='subtype_mismatch'
        elif rows[key]['units'] is None: result['reason']=rows[key]['reason']
        else:
            observed=[]
            for group in r['candidates']:
                w.require(isinstance(group,list) and len(group)<=8,'Invalid candidate alternatives')
                seqs=[]
                for label in group:
                    w.require(isinstance(label,str) and len(label)<=100,'Invalid candidate label')
                    seq=tuple(units(label,scheme)); w.require(len(seq)<=32,'Candidate span too long'); seqs.append(seq)
                w.require(len(set(seqs))==len(seqs),'Duplicate alternatives'); observed.append(seqs)
            if not observed: result['reason']='empty_observations'
            else: result.update(status='COMPARED',**align(observed,rows[key]['units']))
        result['excluded_false_positives']=r.get('excluded_false_positives',0); out.append(result)
    metrics=dict(collections.Counter(r['status'] for r in out)); metrics['exact_notation_agreement']=sum(r.get('exact_notation_agreement',False) for r in out); metrics['ambiguous_optimum']=sum(r.get('ambiguous_optimum',False) for r in out); metrics['unique_compared_loci']=len({r['locus'] for r in out if r['status']=='COMPARED'})
    report=dict(version=VERSION,scientific_status='UNADJUDICATED',source=summary,observations_sha256=w.sha(observations),code_sha256=w.sha(__file__),metrics=metrics,regions=out)
    w.require(not Path(output).exists(),'Output already exists'); w.write(output,report); return metrics


def prepare(manifest,predictions,alphabet,model,mapping,source,expected_sha,output,review=None,references=None,catalog_scheme=None):
    """Adapt v0.5 prediction boxes with an explicit physical locus map; no text search."""
    scheme,_,_=load_source(source,expected_sha); m=w.dataset(manifest); pred=w.read(predictions); inv=w.read(alphabet); maps=w.read(mapping)
    w.require(bool(inv.get('convention')), 'Missing model convention')
    same=inv['convention']==scheme
    w.require(all(x is None for x in (review,references,catalog_scheme)) or all(x is not None for x in (review,references,catalog_scheme)), 'Provide all three review arguments or none')
    w.require(same or review is not None,'Alphabet convention mismatch; use explicit human review instead')
    decisions={}
    if review is not None:
        import active_review as ar
        w.require(catalog_scheme=={'STA1':'sta1','Eva-':'eva-from-sta'}[scheme], 'No implicit cross-convention conversion')
        w.require(Path(review).is_file(),'Review file missing')
        reviewer=w.read(review)['binding']['reviewer']
        schemes,_,data=ar.open_session(manifest,predictions,references,review,reviewer)
        w.require(catalog_scheme in schemes,'Target convention absent from review catalog')
        decisions=data['decisions']
    model_data=w.read(model)
    w.require(pred.get('model_sha256')==w.sha(model) and model_data.get('inventory_sha256')==w.sha(alphabet) and model_data.get('labels')==inv['labels'],'Prediction/model/inventory binding mismatch')
    w.require(pred['manifest_sha256']==w.sha(manifest) and maps['manifest_sha256']==w.sha(manifest) and maps['source_sha256']==expected_sha and maps['scheme']==scheme,'Mapping/prediction provenance mismatch')
    w.require(maps['alphabet_sha256']==w.sha(alphabet) and maps['prediction_sha256']==w.sha(predictions),'Alphabet or prediction binding mismatch')
    records={r['id']:r for r in m['regions']}; entries=maps['regions']; by=collections.defaultdict(list)
    for r in pred['rows']:
        rid=r['region_id']; b=r['box']; label=r['predicted']
        w.require(rid in records and isinstance(b,list) and len(b)==4 and all(type(x) is int for x in b) and 0<=b[0]<b[2] and 0<=b[1]<b[3],'Invalid prediction')
        w.require(label=='unknown' or label in inv['labels'],'Prediction outside inventory'); by[rid].append((b,label))
    w.require(set(entries)==set(records),'Map must account for all regions')
    from PIL import Image
    regions=[]
    for rid,record in records.items():
        entry=entries[rid]; w.require(entry.get('page')==record['page'] and entry.get('group')==record['group'],'Physical mapping page/group mismatch')
        seq=sorted(by[rid],key=lambda x:x[0]);
        with Image.open(w.within(Path(manifest).parent,record['file'])) as im: width,height=im.size
        w.require(all(b[2]<=width and b[3]<=height for b,_ in seq),'Prediction box outside crop')
        w.require(all(a[0][2]<=b[0][0] for a,b in zip(seq,seq[1:])),'Overlapping predictions; correct segmentation first')
        candidates=[]; provenance=[]; false_positives=compounds=0
        for box,label in seq:
            key=hashlib.sha256(json.dumps([rid,box],separators=(',',':')).encode()).hexdigest()
            d=decisions.get(key); selected=None; reason='unresolved'
            if d is not None:
                if d['kind']=='false_positive': false_positives+=1; reason='false_positive'
                elif d['kind']=='compound': compounds+=1; reason='compound'
                elif d['kind']=='glyph':
                    v=d['mapping'][catalog_scheme]; reason=v['state']
                    if v['state']=='mapped': selected=v['label']; reason='human_mapping'
                else: reason='human_uncertain'
            elif same and label!='unknown': selected=label; reason='model_prediction'
            elif not same and label!='unknown': reason='other_model_convention'
            if selected is not None:
                try: units(selected,scheme)
                except ValueError: selected=None; reason='unsupported_label_notation'
            provenance.append(dict(box=box,reason=reason,candidate_index=len(candidates) if reason!='false_positive' else None))
            if reason!='false_positive': candidates.append([selected] if selected is not None else [])
        regions.append(dict(region_id=rid,locus=entry.get('locus'),subtype=entry.get('subtype'),mapping_status=entry.get('mapping_status'),scope=entry.get('scope'),mapper=entry.get('mapper'),candidates=candidates,excluded_false_positives=false_positives,unresolved_compounds=compounds,box_provenance=provenance))
    w.require(not Path(output).exists(),'Output already exists')
    w.write(output,dict(schema=1,scheme=scheme,source_sha256=expected_sha,manifest_sha256=w.sha(manifest),prediction_sha256=w.sha(predictions),alphabet_sha256=w.sha(alphabet),model_sha256=w.sha(model),mapping_sha256=w.sha(mapping),human_review_sha256=w.sha(review) if review is not None else None,catalog_sha256=w.sha(references) if references is not None else None,catalog_scheme=catalog_scheme,regions=regions))


def main():
    p=argparse.ArgumentParser(description=__doc__); s=p.add_subparsers(dest='action',required=True)
    for action,args in [('audit',('source','expected_sha')),('compare',('source','expected_sha','observations','output')),('prepare',('manifest','predictions','alphabet','model','mapping','source','expected_sha','output'))]:
        q=s.add_parser(action)
        for k in args: q.add_argument(k)
        if action=='prepare':
            q.add_argument('--review'); q.add_argument('--references'); q.add_argument('--catalog-scheme')
    q=s.add_parser('audit-common'); q.add_argument('--source',action='append',nargs=2,required=True)
    a=vars(p.parse_args()); action=a.pop('action')
    if action=='audit': result=load_source(a['source'],a['expected_sha'])[2]
    elif action=='audit-common': result=audit_common(a['source'])
    else: result={'prepare':prepare,'compare':compare}[action](**a)
    if result is not None: print(json.dumps(result,indent=2))


if __name__=='__main__': main()

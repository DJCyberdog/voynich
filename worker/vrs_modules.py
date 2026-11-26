"""VRS-124: explicitly installed, local-only research adapters (SDK schema 1)."""
import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path

VERSION = '0.12.1'
HERE = Path(__file__).resolve().parent
MAX_JSON = 4 * 1024 * 1024
MAX_SOURCE = 512 * 1024 * 1024
STA = ('8438ba1c45f47fe1d06b5262cbcdf60ce69158a0edbd4dd802612896f3217e2a',
       '0c0d1eea4b5ab87f8a65fb7f4346864cd90758ad993812b4f2122b3899d4ac88')
LEGACY = '155aea980a6544b5d303e4adb96f0b26b5051791429a3a921b7a2b6ad38bd199'
PDF = 'd095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c'
ASSETS = {
    'legacy_exp0037k.py': '3437973ae10da023981d691511ead6a0941de011',
    'exp0037k_protocol.md': '857b7a36d613418c063d8c9923dacac4eeefe445',
    'exp0037k_summary.json': '3b01dca9118220dd386eb9d1e6bff8293f8a9f49',
    'exp0038f_protocol.md': '24076b4ef4c725ad7724df71eac55b4a7593eb27',
    'exp0038f_packet.csv': 'de80e1541a95b36c4a4b77c6f8362b62fbb5998e',
    'exp0038g_summary.json': 'a13e48ef45d963f486cffa2eb7f8d1e16f89ef49',
}
SPECS = {
    'sample': ('count-outcomes-v1', ('outcomes',), ()),
    'exp0037k': ('historical-replay-v1', ('zl', 'gc'), tuple(list(ASSETS)[:3])),
    'exp0038f': ('anchor-review-audit-v1', ('manuscript', 'zl', 'gc', 'review', 'mapping'), tuple(list(ASSETS)[3:])),
}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def fields(obj, keys):
    need(type(obj) is dict and set(obj) == set(keys), 'Unexpected or missing fields')


def schema(obj):
    need(type(obj['schema']) is int and obj['schema'] == 1, 'Unsupported schema')


def canonical(obj):
    data = json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')
    need(len(data) <= MAX_JSON, 'JSON exceeds limit')
    return data


def digest(data):
    return hashlib.sha256(data).hexdigest()


def valid_hash(s):
    need(type(s) is str and re.fullmatch('[0-9a-f]{64}', s), 'Invalid digest')


def decode(raw):
    def unique(pairs):
        obj = dict(pairs)
        need(len(obj) == len(pairs), 'Duplicate key')
        return obj
    def reject(_):
        raise ValueError('Nonfinite JSON')
    need(len(raw) <= MAX_JSON, 'JSON exceeds limit')
    return json.loads(raw, object_pairs_hook=unique, parse_constant=reject)


def local(root, name, create=False):
    need(type(name) is str and 0 < len(name) <= 512 and not any(x in name for x in ('\\', ':', '\x00')), 'Unsafe path')
    parts = name.split('/')
    need(all(x not in ('', '.', '..') for x in parts), 'Unsafe path')
    path = root
    for part in parts:
        path = path / part
        need(not path.is_symlink(), 'Symlink forbidden')
    need(path.resolve().is_relative_to(root), 'Outside root')
    if not create:
        need(path.is_file(), 'Local file missing')
    return path


def read(path, limit=MAX_JSON):
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    need(len(raw) <= limit, 'File exceeds limit')
    return raw


def artifact(root, ref, limit=MAX_JSON, expected=None, keep=True):
    fields(ref, ('path', 'sha256'))
    valid_hash(ref['sha256'])
    need(expected is None or expected == ref['sha256'], 'Historical source mismatch')
    path = local(root, ref['path'])
    if keep:
        raw = read(path, limit)
        actual = digest(raw)
    else:
        h = hashlib.sha256(); size = 0
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                size += len(chunk); need(size <= limit, 'File exceeds limit'); h.update(chunk)
        actual = h.hexdigest(); raw = None
    need(actual == ref['sha256'], 'Artifact hash mismatch')
    return raw


def installed_asset(name):
    path = local(HERE, 'module_assets/' + name)
    raw = read(path)
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\x00' + raw).hexdigest()
    need(blob == ASSETS[name], 'Installed historical asset changed')
    return raw


def descriptor(name):
    need(type(name) is str and name in SPECS, 'Unknown installed module')
    protocol, roles, assets = SPECS[name]
    return dict(schema=1, sdk=1, module=name, version=VERSION, protocol=protocol,
                inputs=list(roles), backend='cpu', permissions=['local-read', 'local-evidence'],
                code_sha256=digest(read(Path(__file__))), assets={n:digest(installed_asset(n)) for n in assets},
                evidence='aggregate-v1', compatibility='Python >=3.10; local fixed dispatcher')


def publish(root, name, raw):
    path = local(root, name, create=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.vrs-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        try:
            os.link(tmp, path)
        except FileExistsError:
            need(read(local(root, name)) == raw, 'Immutable output collision')
    finally:
        os.unlink(tmp)
    return name


def install(root, name):
    obj = descriptor(name)
    raw = canonical(obj)
    path = publish(root, 'config/vrs-modules/' + name + '/' + digest(raw) + '.json', raw)
    return dict(path=path, sha256=digest(raw))


def sample(raw):
    obj = decode(raw); fields(obj, ('schema', 'outcomes')); schema(obj)
    values = obj['outcomes']; keys = ('accepted', 'abstained', 'failed')
    need(type(values) is list and len(values) <= 100000 and all(type(x) is str and x in keys for x in values), 'Invalid outcomes')
    return dict(total=len(values), counts={k:values.count(k) for k in keys})


def replay(zl, gc):
    # Only the reviewed, byte-pinned installed legacy source is executable.
    need(sys.flags.optimize == 0, 'Historical assertions must be enabled')
    raw = installed_asset('legacy_exp0037k.py')
    ns = {'__name__':'vrs_fixed_legacy'}
    exec(compile(raw, 'installed-exp0037k', 'exec'), ns)
    result = ns['run'](zl, gc)
    original = (json.dumps(result, sort_keys=True, indent=2) + '\n').encode()
    summary = decode(installed_asset('exp0037k_summary.json'))
    need(summary['full_local_result_sha256'] == LEGACY, 'Historical reference mismatch')
    need(digest(original) == LEGACY and result['decision'] == summary['decision'], 'Historical replay differs')
    return dict(experiment='EXP-0037k', historical_decision=result['decision'], exact_replay=True,
                historical_result_sha256=LEGACY, vocab_size=result['vocab_size'], sources=result['sources'],
                directions={k:{x:v['primary'][x] for x in ('N','roots','gain','gates')} for k,v in result['results'].items()})


PACKET = ('review_id','page','drawing_x','drawing_y','text_x','text_y','drawing_valid','writing_valid','attachment','morphology','swelling','branching','notes')
RUBRIC = {'drawing_valid':'YN?', 'writing_valid':'YN?', 'attachment':'UAO?', 'morphology':'RL?', 'swelling':'YN?', 'branching':'YN?'}


def packet_rows(raw):
    reader = csv.DictReader(io.StringIO(raw.decode('ascii')))
    need(tuple(reader.fieldnames or ()) == PACKET, 'Invalid packet header')
    rows = {}
    for row in reader:
        need(set(row) == set(PACKET) and all(type(x) is str for x in row.values()), 'Invalid packet row')
        key = row['review_id']; need(re.fullmatch('B[0-9]{3}', key) and key not in rows, 'Invalid packet ID')
        need(row['page'].isdigit() and int(row['page']) > 0 and all(math.isfinite(float(row[k])) and 0<=float(row[k])<=1 for k in PACKET[2:6]), 'Invalid coordinates')
        need(all(not row[k] for k in PACKET[6:]), 'Packet must be blind and unfilled')
        rows[key] = (int(row['page']), float(row['text_x']), float(row['text_y']))
    return rows


def shared_loci(zl, gc):
    def parse(raw):
        found = set()
        for line in raw.decode('ascii').splitlines():
            m = re.match(r'^<(f\d+[rv]\d?\.\d+,.[Ll]f)>', line)
            if m:
                need(m[1] not in found, 'Duplicate locus'); found.add(m[1])
        return found
    return parse(zl) & parse(gc)


def anchor_audit(root, packet, review, mapping, loci):
    fields(review, ('schema','reviewer','packet_sha256','rows')); schema(review)
    fields(mapping, ('schema','mapper','packet_sha256','rows')); schema(mapping)
    for obj, who in ((review,'reviewer'),(mapping,'mapper')):
        need(type(obj[who]) is str and 0<len(obj[who].strip())<=128, 'Invalid identity')
        need(obj['packet_sha256']==packet[0], 'Packet binding mismatch')
        need(type(obj['rows']) is dict and set(obj['rows'])==set(packet[1]), 'Incomplete candidate accounting')
    need(review['reviewer'] != mapping['mapper'], 'Separate reviewer and mapper required')
    counts = dict(total=len(packet[1]), rejected=0, uncertain=0, unresolved=0, declared_mapped=0)
    used = set(); crops = set()
    for key in sorted(packet[1]):
        v=review['rows'][key]; m=mapping['rows'][key]
        fields(v, RUBRIC); fields(m, ('status','alternatives','selected','crop','page','box','folio'))
        need(all(type(v[k]) is str and len(v[k])==1 and v[k] in allowed for k,allowed in RUBRIC.items()), 'Invalid rubric')
        a=m['alternatives']; need(type(a) is list and len(a)<=128 and all(type(x) is str and x in loci for x in a) and len(set(a))==len(a), 'Unknown or duplicate locus')
        status=m['status']; need(status in ('unresolved','mapped'), 'Invalid mapping status')
        eligible=v['drawing_valid']=='Y' and v['writing_valid']=='Y' and v['attachment']=='U'
        if status=='mapped':
            need(eligible and len(a)==1 and m['selected']==a[0] and a[0] not in used, 'Invalid or duplicate accepted locus')
            page,x,y=packet[1][key]; b=m['box']
            need(type(m['page']) is int and m['page']==page and type(b) is list and len(b)==4 and all(type(z) in (int,float) and math.isfinite(z) for z in b) and 0<=b[0]<=x<=b[2]<=1 and 0<=b[1]<=y<=b[3]<=1 and b[0]<b[2] and b[1]<b[3], 'Invalid region declaration')
            need(m['folio']==a[0].split('.')[0], 'Folio declaration mismatch')
            artifact(root,m['crop']); h=m['crop']['sha256']; need(h not in crops,'Duplicate accepted crop'); crops.add(h); used.add(a[0])
        else:
            need(all(m[k] is None for k in ('selected','crop','page','box','folio')), 'Unresolved mapping cannot assert a match')
        if 'N' in (v['drawing_valid'],v['writing_valid']): counts['rejected']+=1
        elif not eligible: counts['uncertain']+=1
        elif status=='mapped': counts['declared_mapped']+=1
        else: counts['unresolved']+=1
    need(sum(v for k,v in counts.items() if k!='total')==counts['total'], 'Denominator mismatch')
    return counts


def execute(root, plan_path):
    raw=read(local(root,plan_path)); plan=decode(raw)
    fields(plan, ('schema','sdk','module','protocol','installation','inputs')); schema(plan)
    need(type(plan['sdk']) is int and plan['sdk']==1, 'Unsupported SDK')
    name=plan['module']; spec=descriptor(name)
    need(plan['protocol']==spec['protocol'], 'Protocol mismatch')
    need(artifact(root,plan['installation'])==canonical(spec), 'Installation mismatch')
    need(plan['installation']['path']=='config/vrs-modules/'+name+'/'+plan['installation']['sha256']+'.json', 'Explicit local installation required')
    approved=decode(read(local(root,'config/vrs-modules-approved.json')))
    fields(approved,('schema','plans')); schema(approved)
    need(type(approved['plans']) is list and digest(raw) in approved['plans'], 'Plan not locally approved')
    fields(plan['inputs'],spec['inputs']); i=plan['inputs']
    if name=='sample':
        result=sample(artifact(root,i['outcomes']))
    else:
        zl,gc=(artifact(root,i[k],expected=h) for k,h in zip(('zl','gc'),STA))
        if name=='exp0037k': result=replay(zl,gc)
        else:
            artifact(root,i['manuscript'],MAX_SOURCE,PDF,keep=False)
            packet=installed_asset('exp0038f_packet.csv'); rows=packet_rows(packet)
            need(set(rows)=={'B%03d'%n for n in range(1,75)}, 'Historical packet denominator mismatch')
            result=anchor_audit(root,(digest(packet),rows),decode(artifact(root,i['review'])),decode(artifact(root,i['mapping'])),shared_loci(zl,gc))
            historical=decode(installed_asset('exp0038g_summary.json'))
            need(historical['decision']=='NOT_MET' and historical['summary']['n']==74 and historical['summary']['passed']==59,'Historical segmentation evidence mismatch')
            result.update(semantic_status='BLOCKED', historical_segmentation=historical['summary'], mapping_status='DECLARED_ONLY')
    # Recheck plan, approval, installation and inputs prior to publication.
    need(read(local(root,plan_path))==raw and digest(raw) in decode(read(local(root,'config/vrs-modules-approved.json')))['plans'], 'Plan or consent changed')
    need(descriptor(name)==spec and artifact(root,plan['installation'])==canonical(spec), 'Installation changed')
    for k,ref in i.items(): artifact(root,ref,MAX_SOURCE if k=='manuscript' else MAX_JSON,keep=False)
    if name=='exp0038f':
        for m in decode(artifact(root,i['mapping']))['rows'].values():
            if m['status']=='mapped': artifact(root,m['crop'],keep=False)
    evidence=dict(schema=1,sdk=1,module=name,version=VERSION,protocol=spec['protocol'],plan_sha256=digest(raw),
                  installation_sha256=plan['installation']['sha256'],inputs={k:v['sha256'] for k,v in i.items()},
                  backend='cpu',python=sys.version.split()[0],technical_status='COMPLETED',scientific_status='UNADJUDICATED',result=result)
    data=canonical(evidence)
    return publish(root,'workspace/vrs124/evidence/'+digest(data)+'.json',data)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('root'); p.add_argument('action',choices=('list','install','run')); p.add_argument('value',nargs='?')
    a=p.parse_args(); root=Path(a.root).resolve(strict=True); need(root.is_dir(),'Workspace must be a directory')
    if a.action=='list': result=[descriptor(n) for n in SPECS]
    elif a.action=='install': result=install(root,a.value)
    else: result={'evidence':execute(root,a.value)}
    print(json.dumps(result,sort_keys=True,indent=2))

if __name__=='__main__': main()

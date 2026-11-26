"""Hash-bound component and license inventory for an approved local install plan.

Inventory only: declared metadata is not an independent license or provenance
determination. Never use this report alone to authorize redistribution.
"""
import argparse
import hashlib
import re
import zipfile
from email.parser import BytesParser
from pathlib import Path
from vrs_portable import acquire, digest, local, need, plan, save, PROFILES
from vrs_prepare_plan import wheel_identity

NOTICE_LIMIT=4*1024**2
TOTAL_NOTICE_LIMIT=64*1024**2
BINARY_LIMIT=16*1024**3

def sha(data):
    return hashlib.sha256(data).hexdigest()

def bounded(z,i,limit=NOTICE_LIMIT):
    need(0<=i.file_size<=limit,'Notice or metadata size quota')
    with z.open(i) as f:
        data=f.read(limit+1)
    need(len(data)==i.file_size,'Archive member size mismatch')
    return data

def member_inventory(z):
    items=z.infolist()
    need(len(items)<=100000,'Archive member quota')
    seen=set()
    for i in items:
        n=i.filename
        need(i.orig_filename==n and n and not any(ord(c)<32 for c in n)
             and '\\' not in n and ':' not in n and not n.startswith('/')
             and all(x not in ('','.','..') for x in n.rstrip('/').split('/')),
             'Unsafe archive member')
        key=n.rstrip('/').casefold()
        need(key not in seen,'Archive member collision')
        seen.add(key)
    return items

def notices(z,items):
    rows=[]; total=0
    for i in items:
        if i.is_dir():continue
        parts=i.filename.lower().split('/')
        leaf=parts[-1]
        if not (any(x in ('licenses','licences') for x in parts[:-1])
                or re.fullmatch(r'(?:licen[cs]e|copying|notice|copyright|third[-_ ]party(?:[-_ ]notices?)?)(?:[-_. ].*)?',leaf)):
            continue
        total+=i.file_size
        need(total<=TOTAL_NOTICE_LIMIT and len(rows)<2048,'Notice inventory quota')
        data=bounded(z,i)
        rows.append(dict(member=i.filename,bytes=len(data),sha256=sha(data)))
    return sorted(rows,key=lambda r:r['member'])

def binary_components(z,items):
    """Hash actual native binaries and embedded wheel archives without extracting."""
    rows=[]; total=0
    for i in items:
        if i.is_dir() or not re.search(r'\.(?:dll|pyd|exe|so(?:\.\d+)*|dylib|lib|whl)$',i.filename,re.I):
            continue
        total+=i.file_size
        need(0<=i.file_size<=BINARY_LIMIT and total<=BINARY_LIMIT and len(rows)<20000,'Binary inventory quota')
        h=hashlib.sha256(); size=0
        with z.open(i) as f:
            for chunk in iter(lambda:f.read(1024**2),b''):
                size+=len(chunk);need(size<=i.file_size,'Binary size mismatch');h.update(chunk)
        need(size==i.file_size,'Binary size mismatch')
        rows.append(dict(member=i.filename,bytes=size,sha256=h.hexdigest()))
    return sorted(rows,key=lambda row:row['member'])


def clean(text):
    # Unfold email metadata without silently clipping licensing or dependency facts.
    value=re.sub(r'\r?\n[ \t]+',' ',str(text)).strip()
    need(len(value)<=4096 and not any(ord(ch)<32 and ch!='\t' for ch in value),'Metadata value quota or control character')
    return value


def dependency_fields(message):
    values=message.get_all('Requires-Dist',[])
    need(len(values)<=256,'Dependency metadata quota')
    return [clean(value) for value in values]


def unresolved_license_files(metadata_member,declared,notice_rows):
    # Core metadata License-File paths are relative to .dist-info/licenses.
    # Do not extract or resolve an untrusted declaration as a filesystem path.
    prefix=metadata_member.rsplit('/',1)[0]+'/licenses/'
    present={row['member'] for row in notice_rows}
    return [value for value in declared if prefix+value not in present]

def wheel(path,item,expected):
    name,version=wheel_identity(path)
    need((name,version)==expected,'Wheel identity differs from locked requirement')
    with zipfile.ZipFile(path) as z:
        items=member_inventory(z)
        metas=[i for i in items if re.fullmatch(r'[^/]+\.dist-info/METADATA',i.filename)]
        need(len(metas)==1,'Metadata cardinality')
        data=bounded(z,metas[0]); m=BytesParser().parsebytes(data)
        expression=[clean(x) for x in m.get_all('License-Expression',[])]
        legacy=[sha(str(x).encode('utf-8')) for x in m.get_all('License',[])]
        classifiers=[clean(x) for x in m.get_all('Classifier',[]) if str(x).startswith('License ::')]
        declared_files=[clean(x) for x in m.get_all('License-File',[])]
        need(len(expression)<=1 and len(legacy)<=1 and len(classifiers)<=128 and len(declared_files)<=2048,'License metadata quota')
        files=notices(z,items)
        binaries=binary_components(z,items)
        dependencies=dependency_fields(m)
        unresolved=unresolved_license_files(metas[0].filename,declared_files,files)
    need(digest(path)==item['sha256'],'Asset changed during inventory')
    return dict(name=name,version=version,file=item['file'],sha256=item['sha256'],
                bytes=item['size'],metadata_sha256=sha(data),
                declared_license_expression=expression,legacy_license_field_sha256=legacy,
                license_classifiers=classifiers,declared_license_files=declared_files,
                notice_files=files,native_components=binaries,requires_dist=dependencies,
                unresolved_declared_license_files=unresolved,
                license_review='PENDING_MANUAL_REVIEW',
                missing_declared_license=not bool(expression or legacy or classifiers),
                missing_notice_files=not bool(files))

def inventory(root,profile,rel,approved):
    root=Path(root).resolve(strict=True)
    v=plan(root,profile,rel,approved)
    # The existing lock is the single authority for identities and asset hashes.
    expected={}
    for line in v['requirements']:
        pkg,h=line.split(' --hash=sha256:')
        name,version=pkg.split('==')
        expected[h]=(re.sub(r'[-_.]+','-',name).lower(),version)
    runtime=acquire(root,v['runtime'])
    with zipfile.ZipFile(runtime) as z:
        items=member_inventory(z)
        runtime_notices=notices(z,items)
        embedded=[i.filename for i in items if i.filename.endswith('.whl')]
        runtime_binaries=binary_components(z,items)
    need(digest(runtime)==v['runtime']['sha256'],'Runtime changed during inventory')
    rows=[]
    for item in v['wheels']:
        rows.append(wheel(acquire(root,item),item,expected[item['sha256']]))
    return dict(schema=1,kind='VRS_COMPONENT_LICENSE_INVENTORY',profile=profile,
                plan_sha256=approved,source_manifest_sha256=digest(local(root,'portable_sources.json')),
                status='REVIEW_REQUIRED',redistribution_approved=False,
                runtime=dict(file=v['runtime']['file'],sha256=v['runtime']['sha256'],
                             bytes=v['runtime']['size'],notice_files=runtime_notices,
                             embedded_wheels=embedded,native_components=runtime_binaries,bundled_component_review='PENDING'),
                wheels=sorted(rows,key=lambda r:r['name']),
                limitations=['Declared metadata only; no independent license determination.',
                             'Runtime embedded wheels, native libraries and vendored components require separate review.',
                             'Source and research asset redistribution rights require separate owner review.',
                             'No source or wheel publisher attestation inferred from locally generated hashes.'])

def cyclonedx(report):
    """Deterministic component BOM; not a concluded license or vulnerability audit."""
    def component(kind,name,hash_value,version=None,children=None,properties=None):
        value=dict(type=kind,name=name,hashes=[dict(alg='SHA-256',content=hash_value)])
        if version is not None:value['version']=version
        if children:value['components']=children
        if properties:value['properties']=[dict(name=k,value=v) for k,v in properties]
        return value
    def files(rows):
        return [component('file',x['member'],x['sha256']) for x in rows]
    rt=report['runtime']
    components=[component('application',rt['file'],rt['sha256'],children=files(rt['native_components']))]
    for x in report['wheels']:
        props=[('vrs:license-review','PENDING_MANUAL_REVIEW')]
        props.extend(('vrs:declared-license-expression',v) for v in x['declared_license_expression'])
        props.extend(('vrs:requires-dist',v) for v in x['requires_dist'])
        components.append(component('library',x['name'],x['sha256'],x['version'],files(x['native_components']),props))
    return dict(bomFormat='CycloneDX',specVersion='1.6',version=1,
                metadata=dict(component=component('application','Voynich Research Studio '+report['profile'],
                    report['source_manifest_sha256'],properties=[('vrs:plan-sha256',report['plan_sha256']),
                    ('vrs:redistribution-approved','false'),('vrs:scope','locked candidate; nested/vendored component, license and dependency graph review pending')])),
                components=components)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('profile',choices=PROFILES);p.add_argument('--plan',required=True)
    p.add_argument('--approve',required=True);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    a=p.parse_args();root=a.root.resolve(strict=True)
    r=inventory(root,a.profile,a.plan,a.approve)
    out=local(root,'workspace/distribution/license-inventory-'+a.profile+'-'+a.approve+'.json')
    save(out,r)
    bom=out.with_name('sbom-'+a.profile+'-'+a.approve+'.cdx.json');save(bom,cyclonedx(r));print(out);print(bom)

if __name__=='__main__':main()

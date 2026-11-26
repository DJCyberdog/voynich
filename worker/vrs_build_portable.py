"""Deterministic source-only distribution; runtime and wheelhouse are separately approved assets."""
import hashlib
import json
import os
import shutil
import tempfile
import sys
import zipfile
from pathlib import Path
from vrs_portable import local, need, load, plan, acquire, digest, extract


RELEASE_VERSION='0.14.0-rc.1'


def source_payload(root):
    root=Path(root).resolve(strict=True); p=local(root,'portable_sources.json'); manifest=load(p)
    need(set(manifest)=={'schema','files'} and manifest['schema']==1 and 0<len(manifest['files'])<=500,'Invalid source manifest')
    files={}
    for rel,sha in manifest['files'].items():
        need(rel not in ('portable_sources.json',) and not rel.startswith(('config/','workspace/','logs/','cache/','data/','runtime/','.venv/','temp/','dist/','bootstrap/','models/')),'Private path refused')
        src=local(root,rel); need(src.is_file() and src.stat().st_size<=8*1024**2,'Source file quota'); data=src.read_bytes()
        need(hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==sha,'Source blob mismatch'); files[rel]=data; need(sum(map(len,files.values()))<=64*1024**2,'Source bundle quota')
    files['portable_sources.json']=p.read_bytes()
    return files


def build(root):
    root=Path(root).resolve(strict=True); files=source_payload(root); home=local(root,'dist'); home.mkdir(exist_ok=True); out=local(root,'dist/VRS-'+RELEASE_VERSION+'-source.zip'); need(not out.exists(),'Existing build; remove explicitly')
    with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):
            i=zipfile.ZipInfo('Voynich Research Studio/'+name,(2026,11,26,0,0,0)); i.compress_type=zipfile.ZIP_DEFLATED; i.external_attr=0o100644<<16; z.writestr(i,data)
    return out


def build_candidate(root,profile,rel,approved):
    """Local test candidate, NOT an authorized redistributable release."""
    root=Path(root).resolve(strict=True)
    need(rel=='config/install-'+profile+'.json','Canonical candidate plan required')
    v=plan(root,profile,rel,approved); sources=source_payload(root)
    assets=[(item,acquire(root,item)) for item in [v['runtime'],*v['wheels']]]
    from vrs_license_inventory import inventory,cyclonedx
    component_report=inventory(root,profile,rel,approved)
    home=local(root,'dist');home.mkdir(exist_ok=True)
    out=local(root,'dist/VRS-'+RELEASE_VERSION+'-'+profile+'-candidate.zip')
    need(not out.exists(),'Existing candidate; remove explicitly')
    prefix='Voynich Research Studio/'
    def info(name,compression):
        entry=zipfile.ZipInfo(prefix+name,(2026,11,26,0,0,0))
        entry.compress_type=compression;entry.external_attr=0o100644<<16
        return entry
    with tempfile.TemporaryDirectory(dir=home,prefix='.candidate-') as d:
        staging=Path(d);boot=staging/'bootstrap';boot.mkdir()
        extract(assets[0][1],boot)
        need(digest(assets[0][1])==v['runtime']['sha256'],'Runtime changed during extraction')
        archive=staging/'candidate.zip'
        with zipfile.ZipFile(archive,'x',allowZip64=True) as z:
            for name,data in sorted(sources.items()):
                z.writestr(info(name,zipfile.ZIP_DEFLATED),data)
            raw=local(root,rel).read_bytes()
            need(hashlib.sha256(raw).hexdigest()==approved,'Plan changed during packaging')
            z.writestr(info(rel,zipfile.ZIP_DEFLATED),raw)
            z.writestr(info('CANDIDATE.json',zipfile.ZIP_DEFLATED),json.dumps(
                dict(schema=1,version=RELEASE_VERSION,profile=profile,plan_sha256=approved,source_manifest_sha256=hashlib.sha256(sources['portable_sources.json']).hexdigest(),redistribution_approved=False,release_approved=False),sort_keys=True))
            z.writestr(info('COMPONENTS.json',zipfile.ZIP_DEFLATED),json.dumps(component_report,sort_keys=True,ensure_ascii=True))
            z.writestr(info('SBOM.cdx.json',zipfile.ZIP_DEFLATED),json.dumps(cyclonedx(component_report),sort_keys=True,ensure_ascii=True))
            for item,path in assets:
                h=hashlib.sha256()
                name='cache/downloads/'+item['sha256']+'/'+item['file']
                with path.open('rb') as src,z.open(info(name,zipfile.ZIP_STORED),'w',force_zip64=True) as dst:
                    for block in iter(lambda:src.read(1024**2),b''):
                        h.update(block);dst.write(block)
                need(h.hexdigest()==item['sha256'],'Asset changed during packaging')
            for p in sorted(boot.rglob('*')):
                if p.is_file():
                    with p.open('rb') as src,z.open(info('bootstrap/'+p.relative_to(boot).as_posix(),zipfile.ZIP_DEFLATED),'w',force_zip64=True) as dst:
                        shutil.copyfileobj(src,dst,1024**2)
        os.link(archive,out)
    return out


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',nargs='?',type=Path,default=Path(__file__).resolve().parent)
    p.add_argument('--profile',choices=('review','cpu','cuda'));p.add_argument('--plan');p.add_argument('--approve')
    a=p.parse_args()
    if a.profile:
        if not (a.plan and a.approve):p.error('--plan and --approve required')
        print(build_candidate(a.root,a.profile,a.plan,a.approve))
    else:print(build(a.root))

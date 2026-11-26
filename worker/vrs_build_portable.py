"""Deterministic source-only distribution; runtime and wheelhouse are separately approved assets."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from vrs_portable import local, need, load


def build(root):
    root=Path(root).resolve(strict=True); p=local(root,'portable_sources.json'); manifest=load(p)
    need(set(manifest)=={'schema','files'} and manifest['schema']==1 and 0<len(manifest['files'])<=500,'Invalid source manifest')
    files={}
    for rel,sha in manifest['files'].items():
        need(rel not in ('portable_sources.json',) and not rel.startswith(('config/','workspace/','logs/','cache/','data/','runtime/','.venv/','temp/','dist/','bootstrap/','models/')),'Private path refused')
        src=local(root,rel); need(src.is_file() and src.stat().st_size<=8*1024**2,'Source file quota'); data=src.read_bytes()
        need(hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==sha,'Source blob mismatch'); files[rel]=data; need(sum(map(len,files.values()))<=64*1024**2,'Source bundle quota')
    files['portable_sources.json']=p.read_bytes(); home=local(root,'dist'); home.mkdir(exist_ok=True); out=local(root,'dist/VRS-0.13.0-source.zip'); need(not out.exists(),'Existing build; remove explicitly')
    with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):
            i=zipfile.ZipInfo('Voynich Research Studio/'+name,(2026,11,26,0,0,0)); i.compress_type=zipfile.ZIP_DEFLATED; i.external_attr=0o100644<<16; z.writestr(i,data)
    return out


if __name__=='__main__':print(build(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent))

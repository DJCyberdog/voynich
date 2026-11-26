"""CI-only independent validation of exact candidate BOM against pinned upstream schema."""
import hashlib
import json
import sys
from pathlib import Path
from urllib.request import urlopen
from jsonschema import Draft7Validator
from referencing import Registry, Resource

UPSTREAM='0bd48c88d1b1877c7a3536252e06893850763190'
PINS={'bom-1.6.schema.json':'b6c096a999d6ee9e408a9c3ae6c6227d6981c9ba',
      'jsf-0.82.schema.json':'f46bfb1e52731ad1280123ff3e2bd29bd18d4bc2',
      'spdx.schema.json':'4b837b7009aef894aa708aa61ef866cadfdc3091'}

def main(report):
    report=Path(report)
    evidence=json.loads(report.read_text(encoding='utf-8'))
    raw=report.with_name(report.stem+'-sbom.json').read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=evidence['candidate_zip']['sbom_sha256']:raise ValueError('SBOM bytes differ from candidate')
    docs={}
    registry=Registry()
    for name,expected in PINS.items():
        url='https://raw.githubusercontent.com/CycloneDX/specification/'+UPSTREAM+'/schema/'+name
        with urlopen(url,timeout=30) as response:data=response.read(1024**2+1)
        if len(data)>1024**2 or hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=expected:
            raise ValueError('Upstream schema pin mismatch: '+name)
        doc=json.loads(data);docs[name]=doc
        resource=Resource.from_contents(doc,default_specification=__import__('referencing.jsonschema',fromlist=['DRAFT7']).DRAFT7)
        for base in ('http://cyclonedx.org/schema/','https://cyclonedx.org/schema/'):
            registry=registry.with_resource(base+name,resource)
        if '$id' in doc:registry=registry.with_resource(doc['$id'],resource)
    Draft7Validator.check_schema(docs['bom-1.6.schema.json'])
    Draft7Validator(docs['bom-1.6.schema.json'],registry=registry).validate(json.loads(raw))
    result=dict(status='PASS',scope='CYCLONEDX_SCHEMA_ONLY',schema_commit=UPSTREAM,schemas=PINS,sbom_sha256=digest)
    report.with_name(report.stem+'-schema-evidence.json').write_text(json.dumps(result,sort_keys=True),encoding='utf-8')
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main(sys.argv[1])

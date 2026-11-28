"""Audit exact installed CPU distributions; only approved Torch local tag is projected."""
import argparse
import importlib.metadata as md
import json
import re
from pathlib import Path


def project(rows):
    exact={}
    for name,version in rows:
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_.-]+',name) or not isinstance(version,str) or not re.fullmatch(r'[A-Za-z0-9.+!-]+',version):
            raise ValueError('invalid installed distribution identity')
        key=re.sub(r'[-_.]+','-',name).lower()
        if key in exact:raise ValueError('duplicate installed distribution')
        exact[key]=version
    if exact.get('torch')!='2.13.0+cpu' or exact.get('pillow')!='13.0.0' or exact.get('setuptools')!='84.1.0':
        raise ValueError('unexpected installed security pins')
    projected=dict(exact);projected['torch']='2.13.0'
    if any('+' in v for v in projected.values()):raise ValueError('unqualified local version tag')
    return dict(exact=dict(sorted(exact.items())),advisory_versions=dict(sorted(projected.items())),projection={'torch':{'installed':'2.13.0+cpu','advisory':'2.13.0'}},binary_audit=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('requirements',type=Path);p.add_argument('inventory',type=Path);a=p.parse_args()
    report=project((d.metadata['Name'],d.version) for d in md.distributions())
    with a.requirements.open('x',encoding='ascii') as f:
        for name,version in report['advisory_versions'].items():f.write(f'{name}=={version}\n')
    with a.inventory.open('x',encoding='utf-8') as f:json.dump(report,f,sort_keys=True,indent=2)
    print(json.dumps(report,sort_keys=True))

if __name__=='__main__':main()

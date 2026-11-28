"""Prepare a private RC2 candidate from an approved RC1 snapshot; never activate it."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path, PurePosixPath


GENERATED_TREES=('runtime','.venv','bootstrap','cache/downloads','cache/pyc','__pycache__','module_assets/__pycache__')


def need(ok,message):
    if not ok:raise ValueError(message)


def layout(inventory,old_sources,new_sources,profile):
    """Partition exact snapshot leaves. Excluded bytes remain in the verified snapshot."""
    need(profile in ('review','cpu','cuda'),'invalid profile')
    files=inventory['files'];dirs=inventory['dirs']
    old=set(old_sources);new=set(new_sources)
    need(old<=set(files),'snapshot missing managed source')
    generated={'config/portable.json','config/bootstrap-origin.json',f'config/install-{profile}.json'}
    def tree(n):return any(n==p or n.startswith(p+'/') for p in GENERATED_TREES)
    need(not any(tree(n) or n in generated for n in old|new),'managed source in generated state')
    need(not any(n.startswith('config/install-') and n.endswith('.json') and n not in generated for n in files),'multiple install plans require explicit migration')
    need(not any(n in files for n in ('workspace/source-update/journal.json','workspace/source-update/rc2-receipt.json')),'pending or prior RC2 source transaction')
    excluded={n for n in files if n in old or n in generated or tree(n)}
    kept={n:v for n,v in files.items() if n not in excluded}
    kept_dirs=[n for n in dirs if not tree(n)]
    state={n.casefold() for n in kept}|{n.casefold() for n in kept_dirs}
    leaves={n.casefold() for n in kept}
    for n in new:
        need(n.casefold() not in state,'candidate source collides with retained state')
        need(not any(str(p).casefold() in leaves for p in PurePosixPath(n).parents if str(p)!='.'),'candidate parent collides with retained file')
    subset=dict(dirs=sorted(kept_dirs),files=kept,bytes=sum(v['bytes'] for v in kept.values()))
    return subset,dict(retained_files=len(kept),retained_bytes=subset['bytes'],replaced_source_files=len(old),omitted_generated_files=len(excluded-old),omitted_generated_bytes=sum(files[n]['bytes'] for n in excluded-old))


def prepare(snapshot,approved,bundle,bundle_sha,target_sha,out):
    import vrs_rc_snapshot as snap
    import vrs_source_update as source
    from vrs_portable import local,load,digest
    snapshot=snap.existing_directory(snapshot);out=snap.destination(out,snapshot)
    manifest=snap.verify(snapshot,approved);payload=local(snapshot,'payload')
    old,_=source.installed(payload)
    need(source.blob(old[source.MANIFEST])==source.RC1_BASE_BLOB,'wrong immutable RC1 base')
    new,_=source.read_bundle(bundle,bundle_sha)
    need(hashlib.sha256(new[source.MANIFEST]).hexdigest()==target_sha,'wrong target manifest')
    need(source.blob(new[source.MANIFEST])!=source.RC1_BASE_BLOB,'target still RC1')
    state=load(local(payload,'config/portable.json'))
    need(set(state)=={'schema','profile','root','plan','sha256'} and state['schema']==1 and state['profile'] in ('review','cpu','cuda'),'invalid installed receipt')
    profile=state['profile'];rel=f'config/install-{profile}.json'
    need(state['plan']==rel and digest(local(payload,rel))==state['sha256'],'old plan receipt mismatch')
    subset,counts=layout(manifest['inventory'],old,new,profile)
    need(shutil.disk_usage(out.parent).free>=subset['bytes']+sum(map(len,new.values()))+1024**2,'insufficient candidate storage')
    snap.private_directory(out)
    try:
        partial=out/'.partial';snap.copy_tree(payload,partial,subset)
        for name,data in sorted(new.items()):
            p=local(partial,name);p.parent.mkdir(parents=True,exist_ok=True);snap.write_new(p,data)
        need(source.installed(partial)[0]==new,'target source verification failed')
        actual=snap.scan(partial)
        need(set(actual['files'])==set(subset['files'])|set(new),'unexpected candidate leaves')
        need(all(actual['files'][n]==v for n,v in subset['files'].items()),'retained state changed')
        need(snap.preflight(partial)==manifest['ledger_logical_sha256'],'candidate ledger mismatch')
        need(snap.verify(snapshot,approved)==manifest,'snapshot changed')
        report=dict(schema=1,status='CANDIDATE_PREPARED',profile=profile,snapshot_sha256=approved,target_manifest_sha256=target_sha,bundle_sha256=bundle_sha,ledger_logical_sha256=manifest['ledger_logical_sha256'],counts=counts,execution_authorized=False,setup_required=True,activation_performed=False)
        partial.rename(out/'app');snap.write_new(out/'candidate.json',snap.encode(report))
    except BaseException:
        shutil.rmtree(out);raise
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('snapshot',type=Path);p.add_argument('bundle',type=Path);p.add_argument('destination',type=Path);p.add_argument('--snapshot-sha256',required=True);p.add_argument('--bundle-sha256',required=True);p.add_argument('--target-sha256',required=True);p.add_argument('--private-local',required=True,action='store_true');a=p.parse_args()
    print(json.dumps(prepare(a.snapshot,a.snapshot_sha256,a.bundle,a.bundle_sha256,a.target_sha256,a.destination),sort_keys=True))

if __name__=='__main__':main()

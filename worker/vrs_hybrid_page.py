"""Native hybrid sidecar: bounded geometry comparison, no occurrence migration."""
import gzip
import hashlib
import json
import zlib
import numpy as np

POLICY = 'native-hybrid-page-evidence-v1'
MAX_BYTES = 32 * 1024 * 1024
MAX_DECODED_BYTES = 96 * 1024 * 1024
MASKS = ('union', 'majority', 'intersection')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def coverage(boxes, size):
    """Integral map of union of half-open boxes; overlap, not ink accuracy."""
    w,h = size
    require(type(w) is int and type(h) is int and 0 < w*h <= 4_000_000 and w>0 and h>0, 'native page budget')
    d = np.zeros((h+1,w+1), np.int32)
    for l,t,r,b in boxes:
        require(all(type(x) is int for x in (l,t,r,b)) and 0<=l<r<=w and 0<=t<b<=h, 'native box outside image')
        d[t,l]+=1; d[b,l]-=1; d[t,r]-=1; d[b,r]+=1
    occupied = d.cumsum(0,dtype=np.int32).cumsum(1,dtype=np.int32)[:-1,:-1]>0
    return np.pad(occupied.cumsum(0,dtype=np.int64).cumsum(1,dtype=np.int64),((1,0),(1,0)))


def intersects(sums, box):
    l,t,r,b=box
    require(all(type(x) is int for x in box) and 0<=l<r<sums.shape[1] and 0<=t<b<sums.shape[0], 'native overlap box outside image')
    return bool(sums[b,r]-sums[t,r]-sums[b,l]+sums[t,l])


def comparison(manifest, proposals, meta, hybrid, mapper):
    """Compare envelopes in common native coordinates; keep legacy identities."""
    require(len(manifest['regions'])==len(proposals), 'legacy region count mismatch')
    size=meta['size']; legacy=[]; unmapped=0
    for region, proposal in zip(manifest['regions'],proposals):
        require(region['id']==proposal['id'], 'legacy region order mismatch')
        ox,oy,_,_=region['pixel_box']
        for l,t,r,b in proposal['boxes']:
            box=mapper(meta,[ox+l,oy+t,ox+r,oy+b])
            if box is None: unmapped+=1
            else: legacy.append(box)
    sums=coverage(legacy,size)
    result=dict(legacy=len(legacy)+unmapped,mapped=len(legacy),unmapped=unmapped,masks={})
    for name in MASKS:
        m=hybrid['grouping']['masks'][name]
        boxes=[r['box'] for r in m['components']]
        pairs=[r['box'] for r in m['pairs']]
        current=coverage(boxes,size)
        result['masks'][name]=dict(components=len(boxes),pairs=len(pairs),legacy_overlap=sum(intersects(current,b) for b in legacy),component_overlap=sum(intersects(sums,b) for b in boxes),pair_overlap=sum(intersects(sums,b) for b in pairs))
    return result


def assemble(source, page, manifest_ref, manifest, proposals, meta, hybrid, mapper):
    require(manifest['source_sha256']==source['sha256'] and set(manifest['page_dimensions'])=={str(page)}, 'source page mismatch')
    require(meta['page']==page, 'native page mismatch')
    if meta['status']=='METADATA_ONLY':
        require(page==1 and not manifest['regions'] and not proposals and hybrid is None, 'metadata page mismatch')
        counts=dict(legacy=0,mapped=0,unmapped=0,masks={})
    else:
        require(meta['status']=='NATIVE_IMAGE' and hybrid is not None, 'native evidence missing')
        context=hybrid['grouping']['context']
        require(context['source_sha256']==source['sha256'] and context['page']==page and context['image_sha256']==meta['rgb_sha256'] and context['page_size']==meta['size'] and context['origin']==[0,0] and hybrid['native_px_to_pt']==meta['native_px_to_pt'], 'hybrid source binding mismatch')
        require(hybrid['scientific_status']=='UNADJUDICATED' and hybrid['exclusion_authorized'] is False, 'scientific assertion forbidden')
        counts=comparison(manifest,proposals,meta,hybrid,mapper)
    record=dict(policy=POLICY,source=source,page=page,manifest=manifest_ref,legacy_sha256=digest(proposals),native=meta,hybrid=hybrid,comparison=counts,scientific_status='UNADJUDICATED',exclusion_authorized=False)
    record['id']=digest(record)
    require(len(canonical(record))+1<=MAX_DECODED_BYTES,'hybrid decoded page budget exceeded')
    return record


def produce(pdf, source, page, manifest_ref, manifest, proposals, boundary=lambda:None):
    import fitz
    import vrs_ink as ink
    import vrs_hybrid_grouping as grouping
    require(source['sha256']==ink.SOURCE_SHA256,'unsupported native source')
    with pdf.open('rb') as stream:
        require(hashlib.file_digest(stream,'sha256').hexdigest()==source['sha256'],'native source hash mismatch')
    boundary()
    with fitz.open(pdf) as doc:
        require(len(doc)==214 and 1<=page<=len(doc),'native page scope')
        image, meta=ink.native_page(doc[page-1])
    if image is not None:
        require(image.width*image.height<=4_000_000,'native page budget')
        hybrid=grouping.analyze_native(image,source_sha256=source['sha256'],meta=meta,boundary=boundary)
    else:
        hybrid=None
    boundary()
    return assemble(source,page,manifest_ref,manifest,proposals,meta,hybrid,ink.native_box)


def check(record, source, page, manifest_ref, manifest, proposals, mapper):
    """Replay deterministic comparison and canonical bindings, not image decoding."""
    expected=assemble(source,page,manifest_ref,manifest,proposals,record['native'],record['hybrid'],mapper)
    require(digest(record)==digest(expected),'hybrid page evidence mismatch')


def write(path, record):
    """Write immutable plain legacy JSON or deterministic bounded gzip JSON."""
    import os
    data=canonical(record)+b'\n'
    require(len(data)<=MAX_DECODED_BYTES,'hybrid decoded page budget exceeded')
    if path.suffix=='.gz':
        data=gzip.compress(data,compresslevel=3,mtime=0)
    require(len(data)<=MAX_BYTES,'hybrid stored page budget exceeded')
    with path.open('xb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())


def read(path):
    """Bound compressed and decoded input, reject ambiguous JSON; old JSON readable."""
    require(path.stat().st_size<=MAX_BYTES,'hybrid stored page budget exceeded')
    with path.open('rb') as f:
        magic=f.read(2);f.seek(0)
        if magic==b'\x1f\x8b':
            try:
                with gzip.GzipFile(fileobj=f,mode='rb') as g:
                    data=g.read(MAX_DECODED_BYTES+1)
            except (OSError,EOFError,zlib.error) as exc:
                raise ValueError('invalid hybrid gzip') from exc
        else:
            data=f.read(MAX_BYTES+1)
            require(len(data)<=MAX_BYTES,'hybrid stored page budget exceeded')
    require(len(data)<=MAX_DECODED_BYTES,'hybrid decoded page budget exceeded')
    def unique(pairs):
        result={}
        for key,value in pairs:
            require(key not in result,'duplicate hybrid JSON key')
            result[key]=value
        return result
    def reject(value):
        raise ValueError('invalid hybrid JSON constant')
    return json.loads(data.decode('utf-8'),object_pairs_hook=unique,parse_constant=reject)


def validate_ref(root, value, manifest, *, expected_source=None, required=False):
    """Validate immutable page attachment and actual native image identity.

    Replay the geometry comparison only; a scientific/full-engine replay is
    a separate qualification, not inferred from a matching content hash.
    """
    if 'hybrid_evidence' not in value:
        require(not required, 'Missing hybrid page evidence')
        return
    import fitz
    import vrs_contract as c
    import vrs_ink as ink
    record=read(c.artifact(root,value['hybrid_evidence']))
    source=record['source']
    require(source['sha256']==ink.SOURCE_SHA256 and (expected_source is None or source==expected_source),'hybrid evidence source mismatch')
    pdf=c.artifact(root,source)
    page=int(next(iter(manifest['page_dimensions'])))
    with fitz.open(pdf) as doc:
        require(len(doc)==214 and 1<=page<=len(doc),'native page scope')
        _,meta=ink.native_page(doc[page-1])
    require(record['native']==meta,'native metadata replay mismatch')
    if record['hybrid'] is not None:
        h=record['hybrid']
        for item in (h,h['grouping'],h['region']):
            require(item['id']==digest({k:v for k,v in item.items() if k!='id'}),'hybrid nested digest mismatch')
    check(record,source,page,value['source'],manifest,value['regions'],ink.native_box)
    return record


def qualify_ref(root, value, manifest, *, expected_source, boundary=lambda:None):
    """Explicit full pixel-to-evidence replay for qualification, not normal resume."""
    import vrs_contract as c
    old=validate_ref(root,value,manifest,expected_source=expected_source,required=True)
    expected=digest(old); page=old['page']; del old
    pdf=c.artifact(root,expected_source)
    actual=produce(pdf,expected_source,page,value['source'],manifest,value['regions'],boundary)
    require(digest(actual)==expected,'full hybrid replay mismatch')
    return actual['id']

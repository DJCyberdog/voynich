"""RC2-02g: deterministic native-mask grouping evidence, never a glyph verdict."""
import hashlib
import json
from collections import defaultdict
import numpy as np
import vrs_hybrid_alternatives as alternatives

POLICY = 'native-hybrid-grouping-v1'
MASKS = ('union', 'majority', 'intersection')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def hash_bytes(value):
    return hashlib.sha256(value).hexdigest()


def build(votes, n, *, source_sha256, page, image_sha256, origin, page_size,
          labeler, contourer, skeletonizer, grapher, boundary=lambda: None):
    """Use existing component/vector engines, with all alternative masks retained.

    Groups are hypotheses, not occurrences or confirmed compounds. No candidate
    is erased or promoted. IDs are scoped to the source, window and mask policy.
    """
    v = np.asarray(votes)
    if (v.ndim != 2 or not v.size or v.dtype.kind not in 'ui' or type(n) is not int
            or not 1 <= n <= 65535 or np.any(v < 0) or np.any(v > n)):
        raise ValueError('invalid votes')
    h, w = v.shape
    ox, oy = origin
    pw, ph = page_size
    if (type(page) is not int or page < 1 or any(type(i) is not int for i in (ox, oy, pw, ph))
            or not (0 <= ox < ox+w <= pw and 0 <= oy < oy+h <= ph)
            or any(not isinstance(s, str) or len(s) != 64 or any(c not in '0123456789abcdef' for c in s)
                   for s in (source_sha256, image_sha256))):
        raise ValueError('invalid source geometry')
    context = dict(policy=POLICY, source_sha256=source_sha256, page=page,
                   image_sha256=image_sha256, origin=[ox, oy], page_size=[pw, ph],
                   shape=[h, w], votes_sha256=hash_bytes(v.astype('<u2').tobytes()), methods=n)
    scope = digest(context)
    masks = dict(union=v > 0, majority=v > n/2, intersection=v == n)
    outputs = {}
    labels_by_mask = {}
    for name in MASKS:
        boundary()
        mask = masks[name]
        lab, count = labeler(mask)
        if type(count) is not int and not isinstance(count, np.integer):
            raise ValueError('invalid component count')
        if count < 0 or count > 100000:
            raise ValueError('component budget exceeded; no complete record')
        if lab.shape != mask.shape or not np.array_equal(lab > 0, mask):
            raise ValueError('label conservation failure')
        yy, xx = np.nonzero(mask)
        ids = lab[yy, xx]
        order = np.argsort(ids, kind='stable')
        yy, xx, ids = yy[order], xx[order], ids[order]
        if not np.array_equal(np.unique(ids), np.arange(1, count+1)):
            raise ValueError('invalid component identities')
        cuts = np.searchsorted(ids, np.arange(1, count+2))
        rows = []
        for i in range(count):
            if i % 128 == 0:
                boundary()
            y, x = yy[cuts[i]:cuts[i+1]], xx[cuts[i]:cuts[i+1]]
            l, t, r, b = map(int, (x.min(), y.min(), x.max()+1, y.max()+1))
            component = lab[t:b, l:r] == i+1
            loops = contourer(component)
            sk, fallback = skeletonizer(component)
            if sk.shape != component.shape or not sk.any() or np.any(sk & ~component):
                raise ValueError('invalid skeleton')
            graph = grapher(sk)
            row = dict(box=[l+ox,t+oy,r+ox,b+oy], area=int(component.sum()),
                       mask_sha256=hash_bytes(component.astype(np.uint8).tobytes()),
                       contours_sha256=digest(loops), graph_sha256=digest(graph),
                       contours=loops, graph=graph,
                       contour_count=len(loops), skeleton_pixels=int(sk.sum()),
                       graph_nodes=len(graph['nodes']), fallback=bool(fallback),
                       script_status='UNRESOLVED')
            row['id'] = digest([scope, name, row])
            rows.append(row)
        if sum(r['area'] for r in rows) != int(mask.sum()):
            raise ValueError('component accounting')
        # Bounded pair hypotheses; single components are always retained.
        # Only adjacent native boxes sharing vertical support or horizontal overlap
        # are eligible. Tiny marks remain eligible, and pair grouping is optional.
        grid = defaultdict(list)
        pairs = []
        cell = 16
        for i, row in enumerate(rows):
            if i % 128 == 0:
                boundary()
            l,t,r,b = row['box']
            if r-l > 64 or b-t > 64:
                continue
            near = set()
            for gy in range((t-4)//cell, (b+4)//cell+1):
                for gx in range((l-4)//cell, (r+4)//cell+1):
                    near.update(grid[(gx,gy)])
            for j in sorted(near):
                other = rows[j]
                L,T,R,B = other['box']
                dx,dy = max(l-R,L-r,0),max(t-B,T-b,0)
                xo,yo = min(r,R)-max(l,L),min(b,B)-max(t,T)
                if max(dx,dy) > 4 or not (xo>0 or yo>0):
                    continue
                box=[min(l,L),min(t,T),max(r,R),max(b,B)]
                members=sorted([row['id'],other['id']])
                pair=dict(box=box,members=members,kind='POSSIBLE_COMPOUND',script_status='UNRESOLVED')
                pair['id']=digest([scope,name,pair])
                pairs.append(pair)
                if len(pairs)>100000:
                    raise ValueError('pair hypothesis budget exceeded; no complete record')
            for gy in range(t//cell,(b-1)//cell+1):
                for gx in range(l//cell,(r-1)//cell+1):
                    grid[(gx,gy)].append(i)
        labels_by_mask[name] = lab
        outputs[name] = dict(mask_sha256=hash_bytes(mask.astype(np.uint8).tobytes()),
                             pixels=int(mask.sum()), components=rows, pairs=pairs)
    extra = alternatives.build(outputs, labels_by_mask, origin, boundary=boundary)
    record = dict(context=context, masks=outputs, alternatives=extra, scientific_status='UNADJUDICATED',
                  exclusion_authorized=False)
    record['id'] = digest(record)
    return record


def validate(record, votes, n, **kwargs):
    """Full deterministic replay; do not accept a self-rehashed edited record."""
    if digest(record) != digest(build(votes, n, **kwargs)):
        raise ValueError('hybrid evidence replay mismatch')


def analyze_native(rgb, *, source_sha256, meta, boundary=lambda: None):
    """Adapter for a full native page from vrs_ink.native_page.

    It creates evidence, not existing Runtime box proposals; no migration or
    scientific decision is authorized. Caller verifies PDF bytes before decode.
    """
    from PIL import Image
    import vrs_binarize as binarize
    import vrs_artifacts as artifacts
    import vrs_region_evidence as regions
    import vrs_vectors as vectors
    if not isinstance(rgb, Image.Image) or rgb.mode != 'RGB' or not min(rgb.size):
        raise ValueError('expected native RGB')
    image_hash = hash_bytes(rgb.tobytes())
    if (meta.get('status') != 'NATIVE_IMAGE' or meta.get('size') != list(rgb.size)
            or meta.get('rgb_sha256') != image_hash):
        raise ValueError('native image binding mismatch')
    affine = meta.get('native_px_to_pt', [])
    if len(affine) != 4 or not all(np.isfinite(affine)) or min(affine[:2]) <= 0:
        raise ValueError('invalid native affine')
    boundary()
    g = np.asarray(rgb.convert('L')); ng = binarize.normalize(g)
    alternatives = []
    for a, method in [(g,'sauvola'),(g,'wolf'),(ng,'sauvola'),(ng,'wolf'),
                      (binarize.normalize(np.asarray(rgb.getchannel('R'))),'sauvola'),
                      (binarize.normalize(np.asarray(rgb.getchannel('B'))),'sauvola')]:
        boundary()
        alternatives.append(binarize.adaptive(a,31,.25,method))
    agreement = binarize.agreement(alternatives)
    votes, n = agreement['votes'], agreement['n']
    _, rows = artifacts.analyze(rgb,votes,n,origin=(0,0),page_size=rgb.size)
    region, _ = regions.region_record(rgb,votes,n,rows,source_sha256=source_sha256,
                                     page=meta['page'],origin=(0,0),image_size=rgb.size)
    def exact_contours(mask):
        loops = vectors.contours(mask)
        if not np.array_equal(vectors.rasterize(loops,mask.shape),mask):
            raise ValueError('contour roundtrip mismatch')
        return loops
    grouping = build(votes,n,source_sha256=source_sha256,page=meta['page'],
                     image_sha256=image_hash,origin=(0,0),page_size=rgb.size,
                     labeler=artifacts.component_labels,contourer=exact_contours,
                     skeletonizer=vectors.skeleton,grapher=vectors.graph,boundary=boundary)
    record = dict(policy=POLICY, native_px_to_pt=list(affine), ensemble=list(binarize.ENSEMBLE),
                  region=region, grouping=grouping, scientific_status='UNADJUDICATED',
                  exclusion_authorized=False)
    record['id'] = digest(record)
    return record

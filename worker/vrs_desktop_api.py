"""Lightweight desktop boundary. Read-only ledger; all authoritative writes via runtime CLI."""
import json
import os
import shutil
import sqlite3
import subprocess
from vrs_process import background_options
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

import vrs_contract as c
from vrs_core import require, sha
from vrs_ledger import Ledger
from vrs_exceptions import ExceptionQueue, load_page
from vrs_decisions import Decisions

VERSION = '0.10.0'


def safe(root, rel):
    p = Path(root).resolve(strict=True)
    require(isinstance(rel, str) and rel and not any(x in rel for x in ('\\', ':', '\x00')), 'Invalid local path')
    for part in rel.split('/'):
        require(part not in ('', '.', '..'), 'Invalid local path')
        p = p / part
        require(not p.is_symlink() and not getattr(p, 'is_junction', lambda: False)(), 'Workspace link forbidden')
    require(p.resolve().is_relative_to(root), 'Workspace escape')
    return p


def pinned(root, ref):
    safe(root, ref['path'])
    return c.artifact(root, ref)


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('.' + path.name + '-' + uuid.uuid4().hex)
    try:
        with tmp.open('x', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=True, allow_nan=False, indent=2)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


class ReadLedger(Ledger):
    def __init__(self, root):
        self.root = root; self.db = safe(root, 'workspace/vrs095/ledger.sqlite')
        require(self.db.is_file(), 'No local run ledger yet')

    @contextmanager
    def _tx(self):
        conn = sqlite3.connect(self.db.as_uri() + '?mode=ro', uri=True, timeout=3, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute('PRAGMA query_only=ON'); conn.execute('BEGIN')
            require(conn.execute('PRAGMA user_version').fetchone()[0] == 1, 'Unsupported ledger schema')
            yield conn
        finally: conn.close()


class ReadQueue(ExceptionQueue):
    def __init__(self, ledger): self.ledger = ledger; self.root = ledger.root


class ReadDecisions(Decisions):
    def __init__(self, ledger): self.ledger = ledger; self.root = ledger.root; self.queue = ReadQueue(ledger)


def vector_window(image, target, components, pairs=(), alternatives=None):
    """Bounded native preview; overlaps and group proposals are not glyph matches."""
    from vrs_exceptions import box_key
    w,h=image.size; a,b,cx,d=box_key(target)
    require(cx<=w and d<=h,'Native candidate outside image')
    def checked(box):
        l,t,r,bot=box_key(box)
        require(r<=w and bot<=h,'Native component outside image')
        return l,t,r,bot
    selected=[]; lookup={}; points=0
    for row in components:
        l,t,r,bot=checked(row['box'])
        if 'id' in row:
            require(row['id'] not in lookup,'Duplicate component identity')
            lookup[row['id']]=(l,t,r,bot)
        if max(l,a)>=min(r,cx) or max(t,b)>=min(bot,d):continue
        require(len(selected)<2000,'Vector preview component budget exceeded')
        selected.append((row,(l,t,r,bot)))
    ids={row['id'] for row,_ in selected if 'id' in row}
    extra=alternatives or {}
    options={'splits':[],'pairs':[],'compounds':[]}
    for row in extra.get('splits',()):
        if row['parent'] not in ids:continue
        parent=lookup[row['parent']]
        boxes=[checked(p['box']) for p in row['parts']]
        require(len(boxes)==2 and all(parent[0]<=q[0]<q[2]<=parent[2] and parent[1]<=q[1]<q[3]<=parent[3] for q in boxes),'Split outside parent')
        options['splits'].append((row['id'],boxes))
        require(len(options['splits'])<=2000,'Split preview budget exceeded')
    for kind,rows in (('pairs',pairs),('compounds',extra.get('compounds',()))):
        for row in rows:
            members=row['members']
            if not ids.intersection(members):continue
            require(len(set(members))==len(members) and (len(members)==2 if kind=='pairs' else 3<=len(members)<=4) and all(k in lookup for k in members),'Invalid group members')
            boxes=[lookup[k] for k in members]; envelope=checked(row['box'])
            require(envelope==(min(q[0] for q in boxes),min(q[1] for q in boxes),max(q[2] for q in boxes),max(q[3] for q in boxes)),'Group envelope mismatch')
            options[kind].append((row['id'],[envelope]+boxes))
            require(len(options[kind])<=2000,'Group preview budget exceeded')
    # Large intersecting material components can span an entire manuscript page.
    # Keep their identity/count, but show their exact visible geometry in a local viewport.
    large=[row for row,q in selected if max(q[2]-q[0],q[3]-q[1])>256]
    bounds=[(a,b,cx,d)]+[q for _,q in selected if max(q[2]-q[0],q[3]-q[1])<=256]+[q for rows in options.values() for _,boxes in rows for q in boxes]
    left=max(0,min(p[0] for p in bounds)-24); top=max(0,min(p[1] for p in bounds)-24)
    right=min(w,max(p[2] for p in bounds)+24); bottom=min(h,max(p[3] for p in bounds)+24)
    require((right-left)*(bottom-top)<=1_000_000,'Vector preview pixel budget exceeded')
    paths=[]; skeleton=[]; nodes=[]; fallback=0; clipped_paths=0; outside_nodes=0
    def shifted(box):return [box[0]-left,box[1]-top,box[2]-left,box[3]-top]
    def visible(point):return 0<=point[0]<=right-left and 0<=point[1]<=bottom-top
    def clip_segment(p,q):
        # Liang-Barsky clipping; no artificial edge along viewport boundary.
        x,y=p;dx=q[0]-x;dy=q[1]-y;lo,hi=0.,1.
        for delta,dist in ((-dx,x),(dx,right-left-x),(-dy,y),(dy,bottom-top-y)):
            if delta==0:
                if dist<0:return None
            elif delta<0:lo=max(lo,dist/delta)
            else:hi=min(hi,dist/delta)
            if lo>hi:return None
        def at(k):return (min(right-left,max(0,x+k*dx)),min(bottom-top,max(0,y+k*dy)))
        P,Q=at(lo),at(hi)
        return (P,Q) if P!=Q else None
    def append_visible(path,out):
        nonlocal points,clipped_paths
        if all(visible(q) for q in path):
            fragments=[path]
        else:
            clipped_paths+=1;fragments=[];current=[]
            for p,q in zip(path,path[1:]):
                segment=clip_segment(p,q)
                if segment is None:
                    if current:fragments.append(current);current=[]
                elif current and current[-1]==segment[0]:
                    current.append(segment[1])
                else:
                    if current:fragments.append(current)
                    current=list(segment)
            if current:fragments.append(current)
        for fragment in fragments:
            points+=len(fragment)
            require(points<=20000 and len(out)<2000,'Vector visible path budget exceeded')
            out.append(fragment)
    for row,(l,t,r,bot) in selected:
        def translate(path,center=False):
            result=[]; shift=.5 if center else 0
            for x,y in path:
                require(type(x) is int and type(y) is int and 0<=x<=r-l-int(center) and 0<=y<=bot-t-int(center),'Invalid component coordinates')
                result.append((l+x-left+shift,t+y-top+shift))
            return result
        for loop in row['contours']:
            require(len(loop)>=4 and loop[0]==loop[-1],'Invalid vector loop')
            append_visible(translate(loop),paths)
        graph=row.get('graph',{})
        fallback+=int(bool(row.get('fallback',False)))
        for path in graph.get('paths',()):
            require(len(path)>=2,'Invalid skeleton path')
            append_visible(translate(path,True),skeleton)
        for node in graph.get('nodes',()):
            degree=node['degree'];require(type(degree) is int and 0<=degree<=8,'Invalid graph node')
            x,y=translate([node['point']],True)[0]
            if not (0<=x<right-left and 0<=y<bottom-top):outside_nodes+=1;continue
            points+=1;require(points<=20000 and len(nodes)<2000,'Vector visible node budget exceeded')
            nodes.append((x,y,degree))
    layers=dict(skeleton=skeleton,nodes=nodes,fallback=fallback,clipping=dict(large_components=len(large),clipped_paths=clipped_paths,outside_nodes=outside_nodes),
                hypotheses={k:[(rid,[shifted(q) for q in boxes]) for rid,boxes in sorted(rows)] for k,rows in options.items()})
    return image.crop((left,top,right,bottom)),shifted((a,b,cx,d)),paths,len(selected),layers


class Desktop:
    def __init__(self, root): self.root = Path(root).resolve(strict=True)

    def _validate_settings(self, v):
        c.fields(v, ('schema','theme','language','reviewer','interpreter','catalog','geometry','project'))
        require(type(v['schema']) is int and v['schema']==1 and v['theme'] in ('dark','light') and v['language'] in ('de','en') and all(type(v[k]) is str and len(v[k])<=512 for k in ('reviewer','interpreter','catalog','geometry','project')), 'Invalid UI settings')
        import re
        require(re.fullmatch(r'\d{3,5}x\d{3,5}',v['geometry']) is not None, 'Invalid window geometry')
        if v['catalog']: safe(self.root,v['catalog'])
        return v

    def settings(self):
        p = safe(self.root, 'config/vrs-desktop.json')
        if not p.exists(): return dict(schema=1, theme='dark', language='de', reviewer='', interpreter='', catalog='', geometry='1280x800', project='')
        return self._validate_settings(c.load(p))

    def save_settings(self, value):
        # No secrets or raw source bytes in settings.
        self._validate_settings(value); p = safe(self.root, 'config/vrs-desktop.json'); atomic_json(p, value)
        return self.settings()

    def runs(self):
        db = safe(self.root, 'workspace/vrs095/ledger.sqlite')
        if not db.exists(): return []
        ledger = ReadLedger(self.root)
        with ledger._tx() as conn:
            return [dict(id=r['id'], control=r['control'], stage=ledger._next(json.loads(r['receipts'])), locked=r['token'] is not None) for r in conn.execute('SELECT * FROM runs ORDER BY rowid')]

    def review(self, run, offset=0, limit=24):
        c.digest_ok(run); c.number(offset); c.number(limit,100); require(limit>0,'Invalid page size')
        l=ReadLedger(self.root); d=ReadDecisions(l)
        with l._tx() as conn:
            r=l._row(conn,'runs',run); manifest,receipts,_=l._validate(r)
            refs=load_page(pinned(self.root,manifest['inputs']['references'])); c.fields(refs,('schema','inventories'))
            require(refs['schema']==1 and 1<=len(refs['inventories'])<=12,'Invalid inventory bundle')
            inv={}
            for item in refs['inventories']:
                c.fields(item,('alphabet',)); value=load_page(pinned(self.root,item['alphabet'])); name=value['convention']; labels=value['labels']
                require(type(name) is str and name and name not in inv and type(labels) is list and 2<=len(labels)<=256 and all(type(x) is str and x and x!='unknown' for x in labels) and len(set(labels))==len(labels),'Invalid inventory')
                inv[name]=labels
            tables={x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'vrs096_decisions' not in tables or 'vrs095_queue_runs' not in tables or not conn.execute('SELECT 1 FROM vrs095_queue_runs WHERE run_id=?',(run,)).fetchone():
                return dict(items=[],snapshot=None,inventory=inv,next_offset=None,control=r['control'])
            snap, latest=d.snapshot(conn,run); items=[]; skipped=0; more=False
            for row in conn.execute('SELECT id,payload FROM vrs095_queue_items WHERE run_id=? ORDER BY position',(run,)):
                decision=latest.get(row['id'])
                if decision and decision['kind'] in ('glyph','false_positive'): continue
                if skipped<offset: skipped+=1; continue
                if len(items)==limit: more=True; break
                item=json.loads(row['payload']); pinned(self.root,item['crop']); item['revision']=decision['expected_revision']+1 if decision else 0; item['deferred']=bool(decision); items.append(item)
            return dict(items=items,snapshot=snap,inventory=inv,next_offset=offset+len(items) if more else None,control=r['control'])

    def crop(self, item):
        from PIL import Image
        with Image.open(pinned(self.root,item['crop'])) as source:
            require(source.width*source.height<=16_000_000,'Crop too large for review')
            box=item['box']; require(0<=box[0]<box[2]<=source.width and 0<=box[1]<box[3]<=source.height,'Invalid glyph geometry')
            return source.convert('RGB'),box

    def locus_context(self,item):
        """Show only explicitly declared locus provenance; never expose reading hints."""
        run=item['run_id'];c.digest_ok(run);ledger=ReadLedger(self.root)
        with ledger._tx() as conn:
            row=ledger._row(conn,'runs',run); manifest,receipts,_=ledger._validate(row)
            stored=conn.execute('SELECT payload FROM vrs095_queue_items WHERE run_id=? AND id=?',(run,item['id'])).fetchone()
            require(stored is not None,'Unknown review candidate')
            require(all(item.get(k)==v for k,v in json.loads(stored['payload']).items()),'Candidate binding mismatch')
        policy=load_page(pinned(self.root,manifest['inputs']['recognition_policy']))
        c.fields(policy,('schema','approval','mapping'))
        sources=manifest['transcriptions']; key=f"{item['page']}:{item['region_id']}"
        result=[]
        if policy['mapping'] is None:
            return [dict(source_sha256=s['sha256'],status='UNDECLARED') for s in sources]
        maps=load_page(pinned(self.root,policy['mapping']))
        c.fields(maps,('schema','manuscript_sha256','sources'))
        require(maps['schema']==1 and maps['manuscript_sha256']==manifest['inputs']['manuscript']['sha256'],'Mapping source mismatch')
        require(set(maps['sources'])=={s['sha256'] for s in sources},'Mapping transcription coverage mismatch')
        for source in sources:
            entries=maps['sources'][source['sha256']];require(type(entries) is dict,'Invalid locus map')
            entry=entries.get(key)
            info=dict(source_sha256=source['sha256'],status='UNDECLARED')
            if entry is not None:
                c.fields(entry,('crop_sha256','locus','subtype','mapper'))
                require(entry['crop_sha256']==item['crop']['sha256'] and all(type(entry[k]) is str and 0<len(entry[k].strip())<=512 for k in ('locus','subtype','mapper')),'Invalid physical mapping')
                require(sum(isinstance(v,dict) and v.get('locus')==entry['locus'] for v in entries.values())==1,'Duplicate mapped locus')
                import alignment
                scheme,rows,_=alignment.load_source(pinned(self.root,source),source['sha256'])
                require(entry['locus'] in rows and rows[entry['locus']]['subtype']==entry['subtype'],'Declared locus not found in transcription')
                info.update(status='DECLARED',scheme=scheme,locus=entry['locus'],subtype=entry['subtype'],mapper=entry['mapper'])
            result.append(info)
        return result

    def page_context(self, item):
        """Opt-in full page; exact region replay or fail closed. No alignment inference."""
        from PIL import Image
        import fitz
        import vrs_surface as surface
        run=item['run_id']; c.digest_ok(run)
        ledger=ReadLedger(self.root)
        with ledger._tx() as conn:
            row=ledger._row(conn,'runs',run); manifest,receipts,_=ledger._validate(row)
            stored=conn.execute('SELECT payload FROM vrs095_queue_items WHERE run_id=? AND id=?',(run,item['id'])).fetchone()
            require(stored is not None,'Unknown review candidate')
            payload=json.loads(stored['payload'])
            require(all(item.get(k)==v for k,v in payload.items()),'Candidate binding mismatch')
            receipt=receipts['script_regions']; require(receipt['state']=='COMPLETED','Region context unavailable')
            index=load_page(pinned(self.root,receipt['artifact']))
            require(index['run_id']==run and index['stage']=='script_regions','Region index binding mismatch')
            matches=[r for r in index['pages'] if r['page']==item['page']]
            require(len(matches)==1,'Page context unavailable')
            mp=pinned(self.root,matches[0]['manifest']); region_manifest=load_page(mp)
        source=manifest['inputs']['manuscript']
        require(region_manifest['source_sha256']==source['sha256'] and region_manifest['dpi']==200 and region_manifest['renderer']==fitz.VersionBind,'Page rendering provenance mismatch')
        dims=region_manifest['page_dimensions'][str(item['page'])]
        require(len(dims)==2 and all(type(x) is int and x>0 for x in dims) and dims[0]*dims[1]<=16_000_000,'Page too large for review')
        matches=[x for x in region_manifest['regions'] if x['id']==item['region_id'] and x['page']==item['page']]
        require(len(matches)==1,'Region context unavailable')
        region=matches[0]; px=region['pixel_box']
        require(dict(path=(mp.parent.relative_to(self.root)/region['file']).as_posix(),sha256=region['sha256'])==item['crop'],'Region crop binding mismatch')
        require(len(px)==4 and all(type(x) is int for x in px) and 0<=px[0]<px[2]<=dims[0] and 0<=px[1]<px[3]<=dims[1],'Invalid page geometry')
        crop,box=self.crop(item)
        with fitz.open(pinned(self.root,source)) as doc:
            require(doc.is_pdf and not doc.needs_pass and 1<=item['page']<=len(doc),'Invalid source page')
            page=doc[item['page']-1]
            expected=(page.rect*fitz.Matrix(200/72,200/72)).irect
            require(expected.width*expected.height<=16_000_000,'Page raster exceeds review limit')
            if 'surface_policy' in region_manifest:
                require(region_manifest['surface_policy']==surface.POLICY,'Unsupported surface policy')
                pix,_=surface.isolate_page(page,source['sha256'])
            else:
                pix=page.get_pixmap(dpi=200,colorspace=fitz.csRGB,alpha=False)
            require([pix.width,pix.height]==dims,'Page dimensions changed')
            im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
        require(im.crop(px).size==crop.size and im.crop(px).tobytes()==crop.tobytes(),'Page/crop pixels differ; alignment unverified')
        absolute=[px[0]+box[0],px[1]+box[1],px[0]+box[2],px[1]+box[3]]
        return im,absolute

    def vector_context(self, item, mask):
        """Explicit read-only native overlay of persisted hybrid evidence."""
        require(mask in ('union','majority','intersection'),'Invalid evidence mask')
        # page_context authenticates queue identity, source, crop and absolute coordinates.
        page_image,absolute=self.page_context(item); del page_image
        import fitz
        import vrs_ink as ink
        import vrs_hybrid_page as hybrid
        ledger=ReadLedger(self.root); run=item['run_id']
        with ledger._tx() as conn:
            row=ledger._row(conn,'runs',run); manifest,receipts,_=ledger._validate(row)
            region_receipt=receipts['script_regions']; seg_receipt=receipts['glyph_segmentation']
            require(seg_receipt['state']=='COMPLETED','Hybrid segmentation not completed')
            ri=load_page(pinned(self.root,region_receipt['artifact']))
            si=load_page(pinned(self.root,seg_receipt['artifact']))
            require(si['run_id']==run and si['stage']=='glyph_segmentation' and si['source']==region_receipt['artifact'],'Segmentation binding mismatch')
            rr=[x for x in ri['pages'] if x['page']==item['page']]
            ss=[x for x in si['pages'] if x['page']==item['page']]
            require(len(rr)==len(ss)==1,'Missing hybrid page')
            m=load_page(pinned(self.root,rr[0]['manifest']))
            value=load_page(pinned(self.root,ss[0]['proposals']))
            require(value['source']==rr[0]['manifest'],'Hybrid region binding mismatch')
            require('hybrid_evidence' in value,'No hybrid evidence for this run')
            pinned(self.root,value['hybrid_evidence'])
        source=manifest['inputs']['manuscript']
        record=hybrid.validate_ref(self.root,value,m,expected_source=source,required=True)
        require(record['hybrid'] is not None,'No native image evidence')
        with fitz.open(pinned(self.root,source)) as doc:
            image,meta=ink.native_page(doc[item['page']-1])
        require(meta==record['native'] and image is not None,'Native source mismatch')
        target=ink.native_box(meta,absolute)
        require(target is not None,'Native candidate alignment unavailable')
        grouping=record['hybrid']['grouping']; rows=grouping['masks'][mask]
        alternatives=grouping.get('alternatives',{}).get('by_mask',{}).get(mask,{})
        return vector_window(image,target,rows['components'],rows['pairs'],alternatives)

    def catalog(self, rel):
        # Explicit scheme IDs only, no inferred cross-convention mappings.
        if not rel: return {}
        path=safe(self.root,rel); obj=load_page(path); require(obj['schema']==1 and type(obj['schemes']) is list and len(obj['schemes'])<=12,'Invalid visual catalog')
        out={}
        for scheme in obj['schemes']:
            key=scheme['id']; require(type(key) is str and key and key not in out and all(type(scheme[x]) is str and scheme[x] for x in ('name','version','source')),'Invalid catalog provenance')
            entries={}
            for entry in scheme['entries']:
                label=entry['label']; require(type(label) is str and label and label not in entries and 1<=len(entry['samples'])<=8,'Invalid visual entry')
                refs=[]
                for sample in entry['samples']:
                    relpath=(path.parent.relative_to(self.root)/sample['file']).as_posix()
                    ref=dict(path=relpath,sha256=sample['sha256']); pinned(self.root,ref)
                    require(type(sample['source']) is str and sample['source'],'Missing sample provenance')
                    refs.append((ref,sample['source']))
                entries[label]=refs
            require(0<len(entries)<=1024,'Invalid visual catalog coverage')
            out[key]=dict(entries=entries,version=scheme['version'],source=scheme['source'],coverage=scheme.get('coverage','not established'),preview=obj.get('preview',True))
        return out

    def reference_image(self, ref):
        from PIL import Image
        with Image.open(pinned(self.root,ref)) as im:
            require(im.width*im.height<=4_000_000,'Reference too large'); im=im.convert('RGB'); im.thumbnail((240,140)); return im

    def stage_decision(self, item, snapshot, inventory, reviewer, kind, mappings):
        require(type(reviewer) is str and 0<len(reviewer.strip())<=128,'Reviewer required')
        require(kind in ('glyph','false_positive','compound','deferred'),'Invalid decision')
        if kind=='glyph':
            require(set(mappings)==set(inventory),'Every inventory requires a decision')
            for name,row in mappings.items():
                c.fields(row,('state','label')); require(row['state'] in ('mapped','absent','unknown') and (row['label'] in inventory[name] if row['state']=='mapped' else row['label'] is None),'Invalid label/disposition')
        else: require(not mappings,'Non-glyph decision cannot map labels')
        decision=dict(schema=1,run_id=item['run_id'],queue_sha256=snapshot['queue_sha256'],candidate_id=item['id'],expected_revision=item['revision'],reviewer=reviewer.strip(),kind=kind,mappings=mappings)
        path=safe(self.root,'workspace/vrs-desktop/drafts/'+c.digest(decision)+'.json')
        if path.exists(): require(c.load(path)==decision,'Draft collision')
        else: atomic_json(path,decision)
        return path.relative_to(self.root).as_posix()

    def drafts(self):
        base=safe(self.root,'workspace/vrs-desktop/drafts')
        if not base.exists(): return []
        result=[]
        for p in sorted(base.glob('*.json')):
            rel=p.relative_to(self.root).as_posix(); value=c.load(safe(self.root,rel)); require(p.stem==c.digest(value),'Draft integrity mismatch')
            result.append(dict(path=rel,run_id=value['run_id'],candidate_id=value['candidate_id'],kind=value['kind'],revision=value['expected_revision']))
        return result

    def submit_draft(self,interpreter,rel):
        require(rel in {x['path'] for x in self.drafts()},'Unknown local draft')
        return self.command(interpreter,'decide',rel)

    def file_ref(self,rel):
        p=safe(self.root,rel); require(p.is_file(),'Missing local file')
        return dict(path=rel,sha256=sha(p))

    def make_manifest(self,roles,transcriptions,seed=7):
        c.fields(roles,c.ROLES); c.number(seed,2**32-1)
        manifest=dict(schema=1,module=c.MODULE,protocol=c.PROTOCOL,backend='cpu',seed=seed,run_nonce=uuid.uuid4().hex,inputs={k:self.file_ref(v) for k,v in roles.items()},transcriptions=[self.file_ref(v) for v in transcriptions])
        c.manifest(self.root,manifest)
        import vrs_recognition
        vrs_recognition.inputs(self.root,manifest)
        # Validate the local page scope and supported transcription syntax before recording.
        groups=c.load(pinned(self.root,manifest['inputs']['groups']))
        require(type(groups) is dict and 1<=len(groups)<=213 and all(type(k) is str and k.isdecimal() and str(int(k))==k and int(k)>0 and type(v) is str and v.strip() for k,v in groups.items()),'Invalid page scope')
        import fitz, alignment
        with fitz.open(pinned(self.root,manifest['inputs']['manuscript'])) as doc:
            require(doc.is_pdf and not doc.needs_pass and all(int(k)<=len(doc) for k in groups),'Invalid manuscript or page scope')
        for entry in manifest['transcriptions']: alignment.load_source(pinned(self.root,entry),entry['sha256'])
        rel='config/runs/'+manifest['run_nonce']+'.json'; p=safe(self.root,rel); require(not p.exists(),'Manifest collision'); atomic_json(p,manifest)
        return dict(path=rel,**self.manifest_info(rel))

    def build_catalog(self,pdf,plan,preview=False):
        import reference_import
        source=safe(self.root,pdf); approved=safe(self.root,plan); rel='data/catalogs/'+uuid.uuid4().hex
        target=safe(self.root,rel); target.parent.mkdir(parents=True,exist_ok=True)
        try:
            details=reference_import.build(source,approved,target,preview=preview)
            self.catalog(rel+'/references.json')
            return dict(path=rel+'/references.json',details=details,preview=preview)
        except BaseException:
            if target.exists(): shutil.rmtree(target)
            raise

    def command(self, interpreter, action, arg):
        require(action in ('decide','register'),'Unapproved command')
        p=Path(interpreter)
        require(p.is_absolute() and p.is_file() and p.name.lower() in ('python','python3','python.exe','python3.exe','python3.13','python3.12'),'Select local compute Python explicitly')
        script=Path(__file__).with_name('vrs_runtime.py').resolve(strict=True); safe(self.root,arg)
        result=subprocess.run([str(p),str(script),str(self.root),action,arg],cwd=self.root,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120,**background_options())
        require(result.returncode==0, 'Worker rejected request: '+(result.stdout or result.stderr)[-800:])
        return json.loads(result.stdout)

    def import_source(self, path, role):
        """Explicit local copy only. Content addressed; no external file mutated."""
        source=Path(path).resolve(strict=True); require(source.is_file(),'Source not a file')
        require(role in ('manuscript','reference_pdf','transcription','json'),'Invalid source role')
        require(0<source.stat().st_size<=1024**3,'Source outside size limit')
        digest=sha(source); suffix={'manuscript':'.pdf','reference_pdf':'.pdf','transcription':'.txt','json':'.json'}[role]
        target=safe(self.root,f'data/imports/{digest}{suffix}'); target.parent.mkdir(parents=True,exist_ok=True)
        tmp=target.with_name('.'+uuid.uuid4().hex+'.part')
        try:
            if not target.exists():
                with source.open('rb') as f,tmp.open('xb') as out: shutil.copyfileobj(f,out,1024*1024); out.flush(); os.fsync(out.fileno())
                require(sha(tmp)==digest,'Source changed during import'); inspect=tmp
            else: require(sha(target)==digest,'Existing import corrupt'); inspect=target
            if role in ('manuscript','reference_pdf'):
                import fitz
                with fitz.open(inspect,filetype='pdf') as doc: require(doc.is_pdf and not doc.needs_pass and 0<len(doc)<=10000,'Invalid or encrypted PDF'); details=dict(pages=len(doc))
            elif role=='transcription':
                import alignment
                _,_,details=alignment.load_source(inspect,digest)
            else: details=dict(keys=sorted(c.load(inspect).keys()))
            if inspect==tmp:
                # No replace, concurrent same-content import safe.
                try: os.link(tmp,target)
                except FileExistsError: require(sha(target)==digest,'Import collision')
            result=dict(role=role,path=target.relative_to(self.root).as_posix(),sha256=digest,details=details)
            record=safe(self.root,'data/imports/index/'+role+'-'+digest+'.json'); atomic_json(record,result)
            return result
        finally: tmp.unlink(missing_ok=True)

    def sources(self):
        base=safe(self.root,'data/imports/index')
        if not base.exists(): return []
        result=[]
        for p in sorted(base.glob('*.json')):
            value=c.load(safe(self.root,p.relative_to(self.root).as_posix())); pinned(self.root,dict(path=value['path'],sha256=value['sha256'])); result.append(value)
        return result

    def manifest_info(self, rel):
        value=c.load(safe(self.root,rel)); run=c.manifest(self.root,value)
        # Verify source roles, bundles and nested pins via the existing lightweight input validator.
        import vrs_recognition
        inv,models,approval,mapping=vrs_recognition.inputs(self.root,value)
        return dict(run_id=run,backend=value['backend'],inventories={k:len(v[0]) for k,v in inv.items()},models=list(models),approved=approval is not None,mapping=mapping is not None,transcriptions=len(value['transcriptions']))

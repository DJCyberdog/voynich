"""Explicit real-source RC2-02g qualification; no scientific approval or data publication."""
import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
import glyphs as g
import vrs_contract as c
import vrs_core as core
import vrs_hybrid_page as hybrid
import vrs_segmentation as segmentation
import vrs_surface as surface
from vrs_coordinator import ref
from vrs_exceptions import load_page
from vrs_runtime import Runtime


@unittest.skipUnless(os.environ.get('VRS_RC2_PRIVATE_YALE_PDF'), 'Explicit pinned Yale PDF not supplied')
class HybridRuntimeQualification(unittest.TestCase):
    def test_native_segmentation_checkpoint_and_replay(self):
        start=time.perf_counter()
        pdf=Path(os.environ['VRS_RC2_PRIVATE_YALE_PDF']).resolve(strict=True)
        self.assertEqual(core.sha(pdf),surface.YALE_SHA256)
        with tempfile.TemporaryDirectory(prefix='vrs-hybrid-qualification-') as tmp:
            root=Path(tmp).resolve()
            shutil.copyfile(pdf,root/'source.pdf')
            source=ref(root,root/'source.pdf')
            def file(name,obj):
                p=root/name
                p.write_text(json.dumps(obj,sort_keys=True),encoding='utf-8')
                return ref(root,p)
            # Deliberately synthetic inventories; test stops before classification.
            alphabet=file('alphabet.json',dict(convention='Eva-',labels=['a','b']))
            model=file('model.json',dict(version=g.VERSION,labels=['a','b'],
                inventory_sha256=alphabet['sha256'],code_sha256=core.sha(g.__file__),
                thresholds=[.12,.005],prototypes=[[0.]*1024,[1.]*1024]))
            report=file('report.json',dict(model_sha256=model['sha256']))
            (root/'transcription.txt').write_text('synthetic qualification fixture\n',encoding='utf-8')
            manifest=dict(schema=1,module=c.MODULE,protocol=c.PROTOCOL,backend='cpu',seed=271126,
                run_nonce='7'*32,inputs=dict(manuscript=source,
                    groups=file('groups.json',{'1':'metadata','4':'f1r','127':'qualification-page-127'}),
                    references=file('references.json',dict(schema=1,inventories=[dict(alphabet=alphabet)])),
                    model=file('models.json',dict(schema=1,models=[dict(convention='Eva-',model=model,report=report)])),
                    recognition_policy=file('policy.json',dict(schema=1,approval=None,mapping=None))),
                transcriptions=[ref(root,root/'transcription.txt')])
            app=Runtime(root,hybrid_evidence=True)
            run=app.register(manifest)
            self.assertEqual(app.sweep(),[dict(run_id=run,stage='script_regions',control='READY',reason='NONE')])
            print('script_regions completed',round(time.perf_counter()-start,2),flush=True)
            checkpoint=app.ledger.checkpoint
            def stop_after_real_page(*args):
                checkpoint(*args)
                cp=app.ledger.status(run)['checkpoint']
                data=c.load(c.artifact(root,cp['artifact']))
                if len(data['pages'])==2:
                    app.stop.set()
            with patch.object(app.ledger,'checkpoint',side_effect=stop_after_real_page):
                result=app.sweep()
            self.assertEqual(result[0]['control'],'STOP_REQUESTED',result)
            status=app.ledger.status(run)
            self.assertFalse(status['locked'])
            self.assertEqual(status['next_stage'],'glyph_segmentation')
            cp=c.load(c.artifact(root,status['checkpoint']['artifact']))
            self.assertEqual([r['page'] for r in cp['pages']],[1,4])
            # The sidecar is an actual immutable attachment, not a new candidate ID.
            value=load_page(c.artifact(root,cp['pages'][1]['proposals']))
            side=c.artifact(root,value['hybrid_evidence'])
            side_bytes=side.read_bytes()
            self.assertEqual(side_bytes[:2],b'\x1f\x8b')
            # Deliberate test-only corruption in the disposable workspace.
            try:
                side.write_bytes(side_bytes+b'bad')
                with self.assertRaisesRegex(ValueError,'Artifact hash mismatch'):
                    c.artifact(root,value['hybrid_evidence'])
            finally:
                side.write_bytes(side_bytes)
            print('real-page stop, immutable attachment and corruption control PASS',flush=True)
            resumed=Runtime(root,hybrid_evidence=True)
            self.assertEqual(resumed.identity,app.identity)
            calls=[]; original=resumed._page
            def observe(run,stage,page,source,attempt):
                calls.append(page)
                return original(run,stage,page,source,attempt)
            with patch.object(resumed,'_page',side_effect=observe):
                result=resumed.sweep()
            self.assertEqual(result[0]['control'],'READY',result)
            self.assertEqual(calls,[127])
            status=resumed.ledger.status(run)
            self.assertEqual(status['next_stage'],'glyph_classification')
            self.assertIsNone(status['checkpoint'])
            data=load_page(c.artifact(root,status['receipts']['glyph_segmentation']['artifact']))
            self.assertEqual(data['pages'][:2],cp['pages'])
            self.assertEqual([r['page'] for r in data['pages']],[1,4,127])
            for row in data['pages']:
                t=time.perf_counter()
                value=load_page(c.artifact(root,row['proposals']))
                mp=c.artifact(root,value['source']); m=load_page(mp)
                # Recompute the unchanged raster baseline from original receipt crops.
                legacy,lineage=segmentation.generate(m,lambda region:Image.open(mp.parent/region['file']))
                self.assertEqual(legacy,value['regions'])
                self.assertEqual(lineage,value['dedup'])
                evidence=hybrid.validate_ref(root,value,m,expected_source=source,required=True)
                self.assertEqual(evidence['comparison']['legacy'],row['candidates'])
                self.assertEqual(evidence['scientific_status'],'UNADJUDICATED')
                self.assertFalse(evidence['exclusion_authorized'])
                stored=c.artifact(root,value['hybrid_evidence']).stat().st_size
                decoded=len(hybrid.canonical(evidence))+1
                comparison=evidence['comparison']; expected=evidence['id']
                del evidence
                self.assertEqual(hybrid.qualify_ref(root,value,m,expected_source=source),expected)
                print(json.dumps(dict(page=row['page'],legacy_candidates=row['candidates'],
                    stored_bytes=stored,decoded_bytes=decoded,comparison=comparison,
                    replay_seconds=round(time.perf_counter()-t,2))),flush=True)
            print('elapsed_seconds',round(time.perf_counter()-start,2),flush=True)
            # Linux reports peak process RSS in KiB; no cross-platform assumption.
            if os.name!='nt':
                import resource
                print('peak_rss_platform_units',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,flush=True)


if __name__=='__main__':unittest.main()

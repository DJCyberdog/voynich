import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import vrs_modules as m


class Modules(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup); self.root=Path(temp.name)
    def put(self,name,obj,raw=False):
        p=self.root/name; p.parent.mkdir(parents=True,exist_ok=True)
        data=obj if raw else m.canonical(obj); p.write_bytes(data)
        return dict(path=name,sha256=m.digest(data))
    def plan(self,name='sample',inputs=None):
        installed=m.install(self.root,name)
        if inputs is None: inputs={'outcomes':self.put('data.json',dict(schema=1,outcomes=['accepted','abstained','failed','accepted']))}
        obj=dict(schema=1,sdk=1,module=name,protocol=m.SPECS[name][0],installation=installed,inputs=inputs)
        return obj
    def authorize(self,plan):
        r=self.put('plan.json',plan); self.put('config/vrs-modules-approved.json',dict(schema=1,plans=[r['sha256']])); return r['path']
    def test_sample_installed_and_idempotent(self):
        p=self.authorize(self.plan()); a=m.execute(self.root,p); self.assertEqual(a,m.execute(self.root,p)); r=json.loads((self.root/a).read_bytes())
        self.assertEqual(r['result'],dict(total=4,counts=dict(accepted=2,abstained=1,failed=1)))
        self.assertEqual(r['scientific_status'],'UNADJUDICATED'); self.assertEqual(len(list((self.root/'workspace/vrs124/evidence').glob('*.json'))),1)
    def test_no_remote_modules_or_schema_changes(self):
        with self.assertRaises(ValueError): m.install(self.root,'https://example.org/code.py')
        plan=self.plan(); plan['sdk']=2
        with self.assertRaisesRegex(ValueError,'Unsupported SDK'): m.execute(self.root,self.authorize(plan))
        plan['sdk']=1; plan['protocol']='other'
        with self.assertRaisesRegex(ValueError,'Protocol mismatch'): m.execute(self.root,self.authorize(plan))
        plan['protocol']=m.SPECS['sample'][0]; plan['command']='anything'
        with self.assertRaises(ValueError): m.execute(self.root,self.authorize(plan))
    def test_consent_and_tamper(self):
        plan=self.plan(); path=self.put('plan.json',plan)['path']; self.put('config/vrs-modules-approved.json',dict(schema=1,plans=[]))
        with self.assertRaisesRegex(ValueError,'not locally approved'): m.execute(self.root,path)
        self.authorize(plan); (self.root/'data.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'hash mismatch'): m.execute(self.root,path)
        self.assertFalse((self.root/'workspace').exists())
        (self.root/plan['installation']['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'hash mismatch'): m.execute(self.root,path)
    def test_paths_and_json(self):
        for name in ('../x','/x','C:x','a\\b','a//b'):
            with self.assertRaises(ValueError): m.local(self.root,name,create=True)
        with self.assertRaises(ValueError): m.decode(b'{"a":1,"a":2}')
        with self.assertRaises(ValueError): m.decode(b'{"a":NaN}')
        if os.name != 'nt':
            (self.root/'link').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError): m.local(self.root,'link')
    def test_revoked_during_run_and_collision(self):
        p=self.authorize(self.plan()); original=m.sample
        def revoked(raw):
            self.put('config/vrs-modules-approved.json',dict(schema=1,plans=[])); return original(raw)
        with patch.object(m,'sample',side_effect=revoked):
            with self.assertRaisesRegex(ValueError,'consent changed'): m.execute(self.root,p)
        self.assertFalse((self.root/'workspace').exists()); self.authorize(self.plan()); a=m.execute(self.root,p); (self.root/a).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'collision'): m.execute(self.root,p)
    def anchor_fixture(self):
        output=io.StringIO(); writer=csv.writer(output); writer.writerow(m.PACKET)
        for n in (1,2,3): writer.writerow(['B%03d'%n,1,.5,.5,.4,.4]+['']*7)
        raw=output.getvalue().encode(); packet=(m.digest(raw),m.packet_rows(raw)); ids=packet[1]
        review=dict(schema=1,reviewer='visual',packet_sha256=packet[0],rows={k:dict(drawing_valid='Y',writing_valid='Y',attachment='U',morphology='R',swelling='?',branching='N') for k in ids})
        review['rows']['B003']['drawing_valid']='N'
        unresolved=dict(status='unresolved',alternatives=['f1r.1,=Lf'],selected=None,crop=None,page=None,box=None,folio=None)
        mapping=dict(schema=1,mapper='mapping',packet_sha256=packet[0],rows={k:dict(unresolved) for k in ids})
        mapping['rows']['B001']=dict(status='mapped',alternatives=['f1r.1,=Lf'],selected='f1r.1,=Lf',crop=self.put('crop.png',b'fixture bytes',raw=True),page=1,box=[.3,.3,.5,.5],folio='f1r')
        return packet,review,mapping,{'f1r.1,=Lf'}
    def test_anchor_counts_and_controls(self):
        a,b,c,d=self.anchor_fixture(); self.assertEqual(m.anchor_audit(self.root,a,b,c,d),dict(total=3,rejected=1,uncertain=0,unresolved=1,declared_mapped=1))
        c['rows']['B002']=dict(c['rows']['B001'])
        with self.assertRaisesRegex(ValueError,'duplicate accepted locus'): m.anchor_audit(self.root,a,b,c,d)
        a,b,c,d=self.anchor_fixture(); c['mapper']='visual'
        with self.assertRaisesRegex(ValueError,'Separate reviewer'): m.anchor_audit(self.root,a,b,c,d)
        a,b,c,d=self.anchor_fixture(); c['rows']['B001']['page']=2
        with self.assertRaisesRegex(ValueError,'region declaration'): m.anchor_audit(self.root,a,b,c,d)
        a,b,c,d=self.anchor_fixture(); del b['rows']['B002']
        with self.assertRaisesRegex(ValueError,'Incomplete'): m.anchor_audit(self.root,a,b,c,d)
    def test_historical_replay(self):
        source=os.environ.get('VRS_STA_FIXTURES')
        if not source: self.skipTest('Explicit private historical source directory required')
        refs={}
        for role,name in [('zl','ZL3b.txt'),('gc','GC2a_1.txt')]:
            refs[role]=self.put(name,(Path(source)/name).read_bytes(),raw=True)
        p=self.authorize(self.plan('exp0037k',refs)); result=json.loads((self.root/m.execute(self.root,p)).read_bytes())
        self.assertEqual(result['result']['historical_result_sha256'],m.LEGACY)
        self.assertEqual(result['result']['historical_decision'],'NOT_MET'); self.assertTrue(result['result']['exact_replay'])
        self.assertEqual(result['result']['sources']['ZL']['tokens'],28464)
        self.assertEqual(result['result']['sources']['GC']['tokens'],30691)
        self.assertEqual(result['scientific_status'],'UNADJUDICATED')
        refs['zl']=refs['gc']; p=self.authorize(self.plan('exp0037k',refs))
        with self.assertRaisesRegex(ValueError,'Historical source mismatch'): m.execute(self.root,p)

if __name__=='__main__': unittest.main()

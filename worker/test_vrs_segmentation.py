"""RC2-02 geometry/lineage controls; synthetic marks are not Voynich ground truth."""
import copy
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw
import glyphs
import vrs_segmentation as seg


def fixture():
    im=Image.new('RGB',(100,60),'white');d=ImageDraw.Draw(im)
    # Same-looking shapes at distinct positions, two lines and a clipping control.
    for x,y in [(15,10),(30,10),(15,35),(30,35),(70,10)]:
        d.rectangle((x,y,x+4,y+6),fill='black')
    regions=[dict(id=name,page=1,pixel_box=box) for name,box in
             [('whole',[0,0,100,60]),('left',[5,5,60,50]),('clip',[17,8,50,24]),
              ('line',[0,5,60,25]),('repeat',[60,0,90,25])]]
    return im,dict(page_dimensions={'1':[100,60]},regions=regions)


class SegmentationTests(unittest.TestCase):
    def test_projection_parity_and_alternative_lines(self):
        im,m=fixture()
        for r in m['regions']:
            crop=im.crop(r['pixel_box']);h=seg.hypotheses(crop)
            self.assertEqual([list(b) for b,k in h if k&1],sorted(glyphs.boxes(crop)))
        h=dict(seg.hypotheses(im))
        self.assertEqual(h[(15,10,20,42)],1)
        self.assertEqual(h[(15,10,20,17)],2)
        self.assertEqual(h[(15,35,20,42)],2)
        self.assertEqual(seg.hypotheses(Image.new('RGB',(20,20),'white')),[])

    def test_exact_aliases_distinct_positions_and_clipping_preserved(self):
        im,m=fixture()
        p,d=seg.generate(m,lambda r:im.crop(r['pixel_box']))
        stats=d['counts']
        self.assertGreater(stats['exact_duplicates'],0)
        self.assertEqual(stats['raw'],stats['retained']+stats['exact_duplicates'])
        self.assertEqual(len(d['aliases']),stats['exact_duplicates'])
        self.assertGreater(stats['edge_touching_raw'],0)
        absolute={seg.absolute(seg.rect(r['pixel_box']),b) for r,v in zip(m['regions'],p) for b in v['boxes']}
        self.assertTrue({(15,10,20,17),(30,10,35,17),(70,10,75,17),
                         (17,10,20,17),(15,35,20,42),(15,10,20,42)}<=absolute)
        self.assertEqual(len(absolute),stats['retained'])
        seg.validate(m,dict(regions=p,dedup=d),required=True)
        self.assertEqual((p,d),seg.generate(m,lambda r:im.crop(r['pixel_box'])))

    def test_pixel_conflict_is_not_merged(self):
        im=Image.new('RGB',(30,30),'white');ImageDraw.Draw(im).rectangle((8,9,13,16),fill='black')
        other=im.copy();other.putpixel((10,11),(1,1,1))
        m=dict(page_dimensions={'1':[30,30]},regions=[dict(id=r,page=1,pixel_box=[0,0,30,30]) for r in ['a','b']])
        p,d=seg.generate(m,lambda r:(im if r['id']=='a' else other).copy())
        self.assertEqual(d['counts']['pixel_conflict_coordinates'],1)
        self.assertEqual(d['counts']['retained'],2)
        self.assertEqual(d['aliases'],[])

    def test_tamper_and_page_scope(self):
        im,m=fixture();p,d=seg.generate(m,lambda r:im.crop(r['pixel_box']))
        for key in ('counts','aliases','raw'):
            broken=copy.deepcopy(d)
            if key=='counts':broken[key]['retained']+=1
            else:broken[key].pop()
            with self.assertRaises(ValueError):seg.validate(m,dict(regions=p,dedup=broken),required=True)
        with self.assertRaisesRegex(ValueError,'Missing RC2'):seg.validate(m,dict(regions=p),required=True)
        seg.validate(m,dict(regions=p)) # historical read-only contract
        broken=copy.deepcopy(m);broken['regions'][0]['page']=2
        with self.assertRaisesRegex(ValueError,'outside source page'):seg.assemble(broken,d['raw'])
        broken=copy.deepcopy(m);broken['page_dimensions']['2']=[100,60]
        with self.assertRaisesRegex(ValueError,'one source page'):seg.assemble(broken,d['raw'])

    def test_budget_boundary_and_blank(self):
        im,m=fixture()
        with patch.object(seg,'MAX_RAW',1):
            with self.assertRaisesRegex(ValueError,'budget exceeded'):seg.generate(m,lambda r:im.crop(r['pixel_box']))
        def stop():raise InterruptedError('cooperative boundary')
        with self.assertRaises(InterruptedError):seg.generate(m,lambda r:im.crop(r['pixel_box']),stop)
        with self.assertRaisesRegex(ValueError,'dimensions'):seg.generate(m,lambda r:Image.new('RGB',(1,1)))
        blank=dict(page_dimensions={'1':[100,60]},regions=[])
        p,d=seg.generate(blank,lambda r:None)
        self.assertEqual(p,[]);self.assertEqual(d['counts']['retained'],0)
        seg.validate(blank,dict(regions=p,dedup=d),required=True)

    def test_representative_independent_of_input_order(self):
        im,m=fixture();p,d=seg.generate(m,lambda r:im.crop(r['pixel_box']))
        reverse=dict(m,regions=list(reversed(m['regions'])))
        q,e=seg.generate(reverse,lambda r:im.crop(r['pixel_box']))
        self.assertEqual({r['id']:r['boxes'] for r in p},{r['id']:r['boxes'] for r in q})
        self.assertEqual(d['aliases'],e['aliases'])
        self.assertEqual(d['counts'],e['counts'])


if __name__=='__main__':unittest.main()

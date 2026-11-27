"""Opt-in exact-source reproduction of RC1 first exception; never redistribute PDF."""
import os
import unittest
from pathlib import Path

import fitz
import numpy as np
from PIL import Image
import regions
import vrs_surface as surface
import worker


class ExactCaption(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('VRS_RC2_PRIVATE_YALE_PDF'),'Private exact Yale PDF not supplied')
    def test_rc1_first_exception_removed(self):
        pdf=Path(os.environ['VRS_RC2_PRIVATE_YALE_PDF'])
        self.assertEqual(worker.sha(pdf),surface.YALE_SHA256)
        with fitz.open(pdf) as doc:
            self.assertEqual(len(doc),214)
            page=doc[3]
            pix=page.get_pixmap(dpi=200,colorspace=fitz.csRGB,alpha=False)
            self.assertEqual((pix.width,pix.height),(1654,2339))
            old=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
            candidate=(629,42,703,84)
            self.assertIn((0,candidate,True),regions.screened_boxes(old,[0,0,pix.width,pix.height]))
            clip=fitz.Rect(*(x*72/200 for x in candidate))
            self.assertEqual([w[4] for w in page.get_text('words',clip=clip)],['Ya'])
            new,audit=surface.isolate_page(page,surface.YALE_SHA256)
            x0,y0,x1,y1=audit['pixel_box']
            self.assertLessEqual(candidate[3],y0)
            image=Image.frombytes('RGB',(new.width,new.height),new.samples)
            self.assertTrue(np.all(np.asarray(image.crop(candidate))==255))
            selected=[b for _,b,ok in regions.screened_boxes(image,audit['pixel_box']) if ok]
            self.assertGreater(len(selected),0)
            self.assertTrue(all(b[1]>=y0 for b in selected))


if __name__=='__main__':unittest.main()

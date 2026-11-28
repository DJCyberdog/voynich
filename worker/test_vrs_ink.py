import unittest
from types import SimpleNamespace
from io import BytesIO
import numpy as np
from PIL import Image, ImageDraw
import vrs_ink as ink


class InkTests(unittest.TestCase):
    def test_channels_and_background_do_not_mutate_source(self):
        image = Image.new('RGB', (80, 60), (200, 170, 140))
        ImageDraw.Draw(image).rectangle((37, 20, 40, 40), fill=(40, 30, 20))
        original = image.tobytes()
        views = ink.channels(image)
        self.assertEqual(tuple(views), ink.CHANNELS)
        for v in views.values():
            bg, norm, residual = ink.background_views(v, 8)
            self.assertEqual(bg.size, v.size)
            self.assertEqual(norm.size, v.size)
            self.assertEqual(residual.shape, (60, 80))
            self.assertLess(norm.getpixel((38, 30)), norm.getpixel((5, 5)))
            self.assertGreater(residual[30, 38], 0)
        self.assertEqual(image.tobytes(), original)

    def test_constant_and_zero(self):
        for x in (0, 128, 255):
            bg, norm, residual = ink.background_views(Image.new('L', (16, 16), x), 3)
            self.assertTrue(np.all(residual == 0))
            self.assertEqual(norm.getpixel((4, 4)), 255 if x else 0)
        for r in (0, 257, 1.5):
            with self.assertRaises(ValueError):
                ink.background_views(Image.new('L', (10, 10)), r)

    def test_native_geometry_and_color(self):
        import fitz
        im = Image.new('RGB', (40, 30), (180, 140, 100))
        stream = BytesIO(); im.save(stream, format='JPEG', quality=95)
        with fitz.open() as doc:
            doc.new_page(width=200, height=200)
            page = doc.new_page(width=200, height=200)
            page.insert_image(fitz.Rect(20, 30, 100, 90), stream=stream.getvalue(), keep_proportion=False)
            self.assertIsNone(ink.native_page(doc[0])[0])
            result, meta = ink.native_page(page)
            self.assertEqual(result.size, im.size)
            self.assertEqual(meta['native_px_to_pt'], [2, 2, 20, 30])
            self.assertEqual(ink.native_box(meta, [20, 30, 100, 90], dpi=72), [0, 0, 40, 30])
            self.assertIsNone(ink.native_box(meta, [0, 0, 10, 10], dpi=72))
            self.assertEqual(ink.native_box(meta, [21, 31, 23, 33], dpi=72), [0, 0, 2, 2])
            self.assertEqual(ink.sha256(result.tobytes()), meta['rgb_sha256'])

    def test_wrong_source_refused(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'wrong.pdf'; p.write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError, 'Source hash mismatch'):
                ink.inventory(p)


if __name__ == '__main__': unittest.main()

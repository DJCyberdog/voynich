"""RC2-02a experimental native image and background analysis; no ink verdict."""
import hashlib
import math
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

SOURCE_SHA256 = 'd095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c'
POLICY = 'native-rgb-background-v1'
CHANNELS = ('gray', 'red', 'green', 'blue')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def native_page(page):
    """Caller verifies immutable PDF hash first. Decode only the embedded image."""
    require(page.rotation == 0 and page.rect.x0 == page.rect.y0 == 0, 'Unsupported page geometry')
    images = [b for b in page.get_text('dict')['blocks'] if b['type'] == 1]
    if page.number == 0:
        require(not images, 'Unexpected catalog image')
        return None, dict(page=1, status='METADATA_ONLY')
    require(len(images) == 1, 'Ambiguous embedded image')
    b = images[0]
    x0, y0, x1, y1 = map(float, b['bbox'])
    t = b['transform']
    require(0 <= x0 < x1 <= page.rect.width and 0 <= y0 < y1 <= page.rect.height
            and t[0] > 0 and t[3] > 0 and abs(t[1])+abs(t[2]) < .001
            and b.get('mask') is None, 'Unsupported embedded image placement')
    with Image.open(BytesIO(b['image'])) as decoded:
        require(decoded.size == (b['width'], b['height']), 'Decoded image dimensions mismatch')
        require(decoded.mode == 'RGB', 'Unexpected image color mode')
        image = decoded.copy()
    meta = dict(page=page.number+1, status='NATIVE_IMAGE', size=list(image.size),
                box_pt=[x0, y0, x1, y1], encoded_sha256=sha256(b['image']),
                rgb_sha256=sha256(image.tobytes()),
                native_px_to_pt=[(x1-x0)/image.width, (y1-y0)/image.height, x0, y0])
    return image, meta


def native_box(meta, box, dpi=200):
    """Conservative mapping of legacy PDF raster rectangle, not a new label."""
    require(meta['status'] == 'NATIVE_IMAGE' and len(box) == 4 and dpi > 0, 'Invalid coordinate request')
    sx, sy, tx, ty = meta['native_px_to_pt']
    w, h = meta['size']
    a,b,c,d = box
    require(a<c and b<d, 'Empty input rectangle')
    v = [(a*72/dpi-tx)/sx, (b*72/dpi-ty)/sy, (c*72/dpi-tx)/sx, (d*72/dpi-ty)/sy]
    out = [max(0, min(w, math.floor(v[0]))), max(0, min(h, math.floor(v[1]))),
           max(0, min(w, math.ceil(v[2]))), max(0, min(h, math.ceil(v[3])))]
    return out if out[0]<out[2] and out[1]<out[3] else None


def channels(image):
    require(image.mode == 'RGB' and image.width > 0 and image.height > 0, 'Expected nonempty native RGB')
    return dict(gray=image.convert('L'), red=image.getchannel('R'),
                green=image.getchannel('G'), blue=image.getchannel('B'))


def background_views(channel, radius):
    """Return estimate, ratio normalization and signed residual separately.

    Gaussian background is a hypothesis, not an ink segmentation. All output
    stays aligned to input pixels; no morphology, erasure or resampling.
    """
    require(channel.mode == 'L' and type(radius) is int and 1 <= radius <= 256, 'Invalid background parameters')
    estimate = channel.filter(ImageFilter.GaussianBlur(radius))
    value = np.asarray(channel, dtype=np.float32)
    bg = np.asarray(estimate, dtype=np.float32)
    ratio = np.clip(np.rint(255*value/np.maximum(bg, 1)), 0, 255).astype(np.uint8)
    residual = bg.astype(np.int16)-value.astype(np.int16)
    return estimate, Image.fromarray(ratio), residual


def inventory(pdf):
    """Local metadata-only full PDF inventory; does not publish images."""
    import fitz
    with Path(pdf).open('rb') as stream:
        require(hashlib.file_digest(stream, 'sha256').hexdigest() == SOURCE_SHA256, 'Source hash mismatch')
    rows = []
    with fitz.open(pdf) as doc:
        require(len(doc) == 214, 'Source page count mismatch')
        for page in doc:
            _, meta = native_page(page)
            rows.append(meta)
    return dict(policy=POLICY, source_sha256=SOURCE_SHA256, pages=rows, scientific_status='UNADJUDICATED')

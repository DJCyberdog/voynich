"""Local aggregate material proposal audit; no scientific boundary claim."""
import hashlib
import io
import json
import sys
import time
from pathlib import Path
import fitz
import numpy as np
from PIL import Image
import vrs_region_evidence as r

PIN='d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c'

def main(pdf):
    with Path(pdf).open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=PIN: raise ValueError('source mismatch')
    counts=dict(pages=0,images=0,metadata=0,pixels=0,core=0,uncertain=0,outside=0,empty_core=0)
    start=time.perf_counter()
    with fitz.open(pdf) as doc:
        if len(doc)!=214:raise ValueError('page count mismatch')
        for page in doc:
            b=[x for x in page.get_text('dict')['blocks'] if x['type']==1];counts['pages']+=1
            if page.number==0 and not b: counts['metadata']+=1;continue
            if len(b)!=1:raise ValueError('image inventory')
            im=Image.open(io.BytesIO(b[0]['image']));before=im.tobytes();m=r.material_hypotheses(im)
            if not np.all(m['core'].astype(np.uint8)+m['uncertain']+m['outside']==1):raise ValueError('partition')
            if not np.array_equal(m['core'],np.logical_and.reduce(list(m['masks'].values()))) or not np.array_equal(~m['outside'],np.logical_or.reduce(list(m['masks'].values()))):raise ValueError('agreement')
            if before!=im.tobytes():raise ValueError('image mutation')
            counts['images']+=1;counts['pixels']+=im.width*im.height;counts['empty_core']+=int(not m['core'].any())
            for k in ('core','uncertain','outside'):counts[k]+=int(m[k].sum())
            if counts['pages']%40==0: print('pages',counts['pages'],flush=True)
    print(json.dumps(dict(counts=counts,seconds=round(time.perf_counter()-start,2)),indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])

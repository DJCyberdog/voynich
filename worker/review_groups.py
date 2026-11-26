"""Deterministic visual grouping for review order only; no label propagation."""
from collections import defaultdict
from pathlib import Path
import vrs_core as w


def ordered(manifest, rows):
    from PIL import Image, ImageOps
    buckets=defaultdict(list); groups=[]
    for row in rows:
        with Image.open(w.within(Path(manifest).parent,row['record']['file'])) as im:
            patch=im.crop(row['box']).convert('L')
            mask=ImageOps.pad(patch,(16,16),color=255).point(lambda v: 1 if v<160 else 0)
            bits=int.from_bytes(bytes(mask.tobytes()),'big')
        # Compare bounded recent representatives of similar ink density.
        bucket=bits.bit_count()//8
        candidates=[g for k in (bucket-1,bucket,bucket+1) for g in buckets[k][-32:]]
        best=min(candidates,key=lambda g:((bits^g['bits']).bit_count(),g['index']),default=None)
        if best is None or (bits^best['bits']).bit_count()>12:
            best={'bits':bits,'index':len(groups),'rows':[]}; groups.append(best); buckets[bucket].append(best)
        best['rows'].append(row)
    return [dict(row,visual_group=g['index']+1,group_size=len(g['rows'])) for g in groups for row in g['rows']]

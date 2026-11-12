#!/usr/bin/env python3
"""EXPLORATORY POST-HOC C1 supplement: within-line token-order shuffles.
Not part of the preregistered C1 semantics experiment; stdlib only.
"""
import argparse
import hashlib
import json
import random
import re
import statistics
from pathlib import Path
from c1_context_model import extract_ivtff, metrics


def run(path, folio=None, permutations=200, seed=425121):
    raw = Path(path).read_bytes()
    text = raw.decode('utf-8')
    if not (text.startswith('#=IVTFF Eva- 2.0') and 'Version 3b of 13/05/2025' in text[:300]):
        raise ValueError('Source is not labeled ZL3b-n v3b IVTFF')
    folios = [folio] if folio else sorted(set(re.findall(r'^<(f\d+[rv](?:\d+)?)\.\d+,[^>]*>', text, re.M)))
    lines = [line for f in folios for line in extract_ivtff(text, f)]
    original = metrics(lines)
    rng = random.Random(seed)
    null_values = []
    for _ in range(permutations):
        shuffled = [line.copy() for line in lines]
        for line in shuffled:
            rng.shuffle(line)
        null_values.append(metrics(shuffled)['local_edit_le1_rate'])
    obs = original['local_edit_le1_rate']
    return {'scope':'POSTHOC_EXPLORATORY', 'seed':seed, 'folio':folio or 'all',
            'sha256':hashlib.sha256(raw).hexdigest(), 'lines':len(lines),
            'tokens':original['tokens'], 'observed_local_edit_le1':obs,
            'null_mean':statistics.mean(null_values),
            'null_min':min(null_values),'null_max':max(null_values),
            'permutations':permutations,
            'empirical_upper_tail_p':(1+sum(x>=obs for x in null_values))/(permutations+1)}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True)
    p.add_argument('--folio')
    p.add_argument('--permutations',type=int,default=200)
    p.add_argument('--seed',type=int,default=425121)
    args=p.parse_args()
    print(json.dumps(run(args.input,args.folio,args.permutations,args.seed),sort_keys=True,indent=2))

if __name__ == '__main__':
    main()

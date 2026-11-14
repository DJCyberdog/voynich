#!/usr/bin/env python3
"""EXP-0026: preregistered A-05 EVA-q continuation-line onset test.
Stdlib only. Requires owner-held SHA-pinned ZL3b-n v3b. Does not export text.
"""
import hashlib
import json
import math
import re
import sys
from pathlib import Path

SOURCE_SHA = 'bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'
FOLIO_LINE = re.compile(r'^<(f\d+[rv](?:\d+)?)\.(\d+),([^>]+)>\s*(.*)$')
CERTAIN = re.compile(r'[a-z]+\Z')
COMMENT = re.compile(r'<![^>]*>')
MARKUP = re.compile(r'<[^>]*>')
ROOT = re.compile(r'^(f\d+)[rv](?:\d+)?$')


def is_test(root):
    digest = hashlib.sha256(('EXP0026-A05-ROOT-v1|' + root).encode('ascii')).digest()
    return int.from_bytes(digest[:8], 'big') % 5 == 0


def tokenize(body):
    body = COMMENT.sub('', body).replace('<->', '.').replace('<~>', '.')
    body = MARKUP.sub('', body)  # blank paragraph/end tags, other markup fails closed if first
    parts = body.split('.')
    if not parts or CERTAIN.fullmatch(parts[0]) is None:
        return None
    return [s for s in parts if CERTAIN.fullmatch(s) is not None]


def poisson_binomial(probs):
    arr = [1.0]
    for p in probs:
        if not (0.0 <= p <= 1.0):
            raise AssertionError('probability outside [0,1]')
        next_arr = [0.0] * (len(arr) + 1)
        for i, v in enumerate(arr):
            next_arr[i] += v * (1.0-p)
            next_arr[i+1] += v*p
        arr = next_arr
    if not math.isclose(sum(arr), 1.0, rel_tol=1e-10, abs_tol=1e-10):
        raise AssertionError('Poisson-binomial PMF lost total mass')
    return arr


def summarize(rows):
    probs = []
    actual = 0
    informative = 0
    for tokens in rows:
        first = tokens[0]
        peers = [t for t in tokens if len(t) == len(first)]
        q = sum(t.startswith('q') for t in peers)
        p = q / len(peers)
        probs.append(p)
        actual += int(first.startswith('q'))
        informative += int(0 < p < 1)
    if not probs:
        return None
    dist = poisson_binomial(probs)
    expected = sum(probs)
    delta = (expected-actual) / len(probs)
    pleft = sum(dist[:actual+1])
    passed = (pleft <= 0.05 and delta >= 0.015)
    return {'lines':len(probs),'informative_lines':informative,
            'observed_q_first':actual,'null_expected_q_first':expected,
            'observed_rate':actual/len(probs),'null_expected_rate':expected/len(probs),
            'depletion_absolute':delta,'one_sided_p_exact':pleft,
            'decision':'NARROW_DEPLETION_SUPPORTED' if passed else 'NARROW_DEPLETION_NOT_SUPPORTED'}


def run(data):
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA:
        raise ValueError('SOURCE SHA MISMATCH; FAIL CLOSED')
    text = data.decode('utf-8-sig')
    if not text.startswith('#=IVTFF Eva- 2.0 M 5\n') or 'Version 3b of 13/05/2025' not in text[:200]:
        raise ValueError('Version header mismatch')
    groups = {'train':[],'test':[]}
    roots = {'train':set(),'test':set()}
    folios = {'train':set(),'test':set()}
    discarded = {'not_plus_P0':0,'ambiguous_first':0,'single_word':0,'prior_f3_f8_roots':0}
    for raw in text.splitlines():
        match = FOLIO_LINE.match(raw)
        if match is None:
            continue
        folio, line_number, tag, body = match.groups()
        if tag != '+P0':
            discarded['not_plus_P0'] += 1
            continue
        root_match = ROOT.match(folio)
        if root_match is None:
            raise AssertionError('unexpected folio ID')
        root = root_match.group(1)
        if root in ('f3','f8'):
            discarded['prior_f3_f8_roots'] += 1
            continue
        tokens = tokenize(body)
        if tokens is None:
            discarded['ambiguous_first'] += 1
            continue
        if len(tokens) < 2:
            discarded['single_word'] += 1
            continue
        grp = 'test' if is_test(root) else 'train'
        groups[grp].append(tokens)
        roots[grp].add(root)
        folios[grp].add(folio)
    if not groups['test'] or not groups['train']:
        raise AssertionError('empty holdout or training group')
    assert not (roots['train'] & roots['test'])
    pos = summarize([['aaa','qqq'] for _ in range(40)])
    neg = summarize([(['qqq','aaa'] if k%2==0 else ['aaa','qqq']) for k in range(40)])
    assert pos['decision']=='NARROW_DEPLETION_SUPPORTED' and pos['observed_q_first']==0
    assert neg['decision']=='NARROW_DEPLETION_NOT_SUPPORTED' and neg['observed_q_first']==20
    assert poisson_binomial([0.5,0.5]) == [0.25,0.5,0.25]
    return {'experiment':'EXP-0026','source_sha256':SOURCE_SHA,
            'predeclared_split':'EXP0026-A05-ROOT-v1|fNNN, sha256 first8 uint64 mod5 == 0 for TEST',
            'prior_folios_excluded':['f3*','f8*'],
            'parse_policy':'only +P0; certain dot boundaries; ASCII a-z; first certain; >=2 tokens; same-length within-line null',
            'train_folio_roots':len(roots['train']),'test_folio_roots':len(roots['test']),
            'train_folio_side_ids':len(folios['train']),'test_folio_side_ids':len(folios['test']),
            'test_root_ids':sorted(roots['test'],key=lambda x:int(x[1:])),
            'excluded_line_counts':discarded,'exploratory_train':summarize(groups['train']),
            'primary_heldout_test':summarize(groups['test']),
            'controls':{'positive_forced_nonq':pos,'negative_balanced':neg,'poisson_binomial_two_fair':[0.25,0.5,0.25]},
            'semantic_decipherment_claim':False}


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('usage: exp0026_a05_folio_root_q_test.py /path/to/ZL3b-n.txt')
    print(json.dumps(run(Path(sys.argv[1]).read_bytes()),sort_keys=True,indent=2))

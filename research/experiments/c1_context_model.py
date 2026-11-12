#!/usr/bin/env python3
"""C-1A/B semantic toy generators and a morphology-only Voynich diagnostic.

Own implementation, Python standard library only. No Voynich meanings inferred.
Data are read locally; no files are downloaded or redistributed.
"""
import argparse
import hashlib
import json
import math
import random
import re
import statistics
from pathlib import Path

VERSION = 'C1-2026-11-12-freeze-1'
SEED = 421307
# 25 artificial meaning stems. These are NOT EVA transcriptions or readings.
STEMS = {
    'dak': 'water/liquid', 'en': 'animal', 'tir': 'drink', 'vek': 'vessel',
    'sal': 'movement/swim', 'rin': 'river', 'tor': 'earth/land', 'mir': 'plant',
    'nar': 'fire', 'hel': 'air', 'pol': 'stone', 'kal': 'tree',
    'bel': 'leaf', 'var': 'flower', 'sun': 'sun', 'lun': 'moon',
    'dor': 'house', 'ger': 'door', 'val': 'way', 'hum': 'human',
    'kin': 'child', 'fen': 'fish', 'hur': 'dog', 'kat': 'cat', 'mus': 'mouse'
}
SENSES = ('li', 'su')
CUES = {'tir': 'li', 'vek': 'li', 'sal': 'su', 'rin': 'su'}
SUFFIXES = ('dy', 'ey', 'ol', 'in')  # fixed surface diagnostics, NOT translations
IVTFF_LINE = re.compile(r'^<(?P<folio>f\d+[rv](?:\d+)?)\.(?P<line>\d+),[^>]*>\s*(?P<body>.*)$')


def scenario_lines(n=800, seed=SEED):
    rng = random.Random(seed)
    noncue = [s for s in STEMS if s not in CUES]
    output = []
    for _ in range(n):
        length = rng.randrange(7, 12)
        target = 3
        words = [rng.choice(noncue) for _ in range(length)]
        # Independently specified intended sense is hidden from the reader.
        sense = rng.choice(SENSES)
        ambiguous = rng.random() < 0.80
        words[target] = 'endak' if ambiguous else 'daken'
        for p in (1, 2, 4, 5):
            if rng.random() < 0.55:
                hint = sense if rng.random() < 0.75 else ('su' if sense == 'li' else 'li')
                words[p] = rng.choice([s for s, v in CUES.items() if v == hint])
        # Two-stem compounds in the background, no semantics claimed.
        for p in range(length):
            if p not in (target, 1, 2, 4, 5) and rng.random() < 0.24:
                words[p] = words[p] + rng.choice(noncue)
        output.append((words, target, sense, ambiguous))
    return output


def cue_difference(words, target, sense):
    vote = {'li': 0, 'su': 0}
    for i in range(max(0, target-2), min(len(words), target+3)):
        if i != target and words[i] in CUES:
            vote[CUES[words[i]]] += 1
    return vote[sense] - vote['su' if sense == 'li' else 'li'], vote


def encode(words, target, sense, ambiguous, policy):
    out = list(words)
    if not ambiguous:
        return out, False
    margin, _ = cue_difference(words, target, sense)
    # C1A explicitness margin >=2; C1B economy margin >=1.
    threshold = 2 if policy == 'C1A' else 1
    mark = margin < threshold
    if mark:
        out[target] = 'endak' + sense
    return out, mark


def decode(words, target):
    w = words[target]
    if w == 'daken':
        return 'unambiguous'
    for suffix in SENSES:
        if w == 'endak' + suffix:
            return suffix
    _, vote = cue_difference(words, target, 'li')
    if vote['li'] > vote['su']:
        return 'li'
    if vote['su'] > vote['li']:
        return 'su'
    return None


def shuffled_context_accuracy(rows, scenarios, seed=SEED):
    rng = random.Random(seed+42)
    controls = [list(row) for row in rows]
    order = list(range(len(rows)))
    rng.shuffle(order)
    for i, src in enumerate(order):
        for offset in (1,2,4,5):
            controls[i][offset] = rows[src][offset]
    successes = total = 0
    for row, (_original, target, sense, ambiguous) in zip(controls, scenarios):
        if ambiguous:
            total += 1
            successes += int(decode(row,target)==sense)
    return successes/total if total else 0

def generate(policy, scenarios):
    rows, marked, correct, ambiguous_count, correct_ambiguous = [], 0, 0, 0, 0
    for words, target, sense, ambiguous in scenarios:
        produced, is_marked = encode(words, target, sense, ambiguous, policy)
        rows.append(produced)
        if ambiguous:
            ambiguous_count += 1
            marked += int(is_marked)
            is_correct = decode(produced, target) == sense
            correct_ambiguous += int(is_correct)
        correct += int(decode(produced, target) == (sense if ambiguous else 'unambiguous'))
    return rows, {'scenarios': len(scenarios), 'ambiguous': ambiguous_count,
                  'marker_count': marked,
                  'marker_rate_ambiguous': marked/ambiguous_count if ambiguous_count else 0,
                  'ambiguous_decode_accuracy': correct_ambiguous/ambiguous_count if ambiguous_count else 0,
                  'all_decode_accuracy': correct/len(scenarios) if scenarios else 0}


def mechanical(lengths, seed=SEED):
    rng = random.Random(seed + 1)
    roots = tuple(STEMS)
    alphabet = 'aekilnorstuyv'
    rows = []
    for length in lengths:
        line = []
        for _ in range(length):
            if line and rng.random() < 0.70:
                base = rng.choice(line[-min(4,len(line)):])
                ix = rng.randrange(len(base))
                candidate = rng.choice(alphabet)
                new = base[:ix] + candidate + base[ix+1:]
            else:
                new = rng.choice(roots)
            line.append(new)
        rows.append(line)
    return rows


def distance_up_to_one(a, b):
    if abs(len(a)-len(b)) > 1:
        return False
    if a == b:
        return True
    if len(a) > len(b):
        a, b = b, a
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a,b)) <= 1
    i=j=0
    misses=0
    while i < len(a) and j < len(b):
        if a[i] != b[j]:
            misses += 1
            if misses > 1:
                return False
            j += 1
        else:
            i += 1
            j += 1
    return True


def metrics(lines):
    words = [w for line in lines for w in line]
    if not words:
        return {'lines':len(lines), 'tokens':0}
    eligible, exact, near, sameprefix = 0,0,0,0
    for line in lines:
        for i, w in enumerate(line):
            if i == 0:
                continue
            eligible += 1
            prior = line[max(i-4,0):i]
            exact += int(any(w==p for p in prior))
            near += int(any(distance_up_to_one(w,p) for p in prior))
            sameprefix += int(any(w[:2]==p[:2] for p in prior))
    tails = [w[-2:] for w in words if len(w)>=2]
    tail_counts = {v:tails.count(v) for v in set(tails)}
    total = len(tails)
    entropy = -sum((n/total)*math.log(n/total) for n in tail_counts.values()) if total else 0.0
    top2 = sum(sorted(tail_counts.values(), reverse=True)[:2])/total if total else 0.0
    return {'lines':len(lines), 'tokens':len(words), 'mean_length':statistics.mean(map(len,words)),
            'median_length':statistics.median(map(len,words)),
            'top2_ending_share':top2,'ending2_entropy_nats':entropy,
            'local_exact_rate':exact/eligible if eligible else None,
            'local_edit_le1_rate':near/eligible if eligible else None,
            'local_prefix2_rate':sameprefix/eligible if eligible else None,
            'ending_proxy_rate':sum(w.endswith(SUFFIXES) for w in words)/len(words)}


def extract_ivtff(text, wanted):
    """Conservative: dot is certain space; comma-containing segments excluded."""
    lines = []
    for raw in text.splitlines():
        m = IVTFF_LINE.match(raw)
        if not m or m['folio'] != wanted:
            continue
        body = m['body']
        body = re.sub(r'<!.*?>', '', body)
        body = body.replace('<->', '.').replace('<%>', '').replace('<$>', '')
        parts = re.split(r'[.\s]+', body)
        kept = [p for p in parts if re.fullmatch(r'[a-z]+',p) and ',' not in p and len(p) >= 2]
        if kept:
            lines.append(kept)
    return lines


def pilot(seed=SEED, input_path=None, folio='f4r', inline_text=None, expected_sha256=None):
    all_scenarios = scenario_lines(seed=seed)
    # The first 640 are development examples; no parameter is fitted.
    scenarios = all_scenarios[640:]
    a, ar = generate('C1A',scenarios)
    b, br = generate('C1B',scenarios)
    m = mechanical([len(line) for line in a],seed)
    ar['shuffled_context_decode_accuracy'] = shuffled_context_accuracy(a, scenarios, seed)
    br['shuffled_context_decode_accuracy'] = shuffled_context_accuracy(b, scenarios, seed)
    result = {'version':VERSION,'seed':seed,'stems':len(STEMS),
              'synthetic_split': {'development_scenarios': 640,'heldout_scenarios':160,
                                  'note':'fixed rules; zero parameters fitted on development'},
              'synthetic':{'C1A':{'controls':ar,'surface':metrics(a)},
                           'C1B':{'controls':br,'surface':metrics(b)},
                           'mechanical':{'surface':metrics(m)}}}
    if input_path or inline_text is not None:
        raw = Path(input_path).read_bytes() if input_path else inline_text.encode('utf-8')
        actual_sha = hashlib.sha256(raw).hexdigest()
        if expected_sha256 and actual_sha != expected_sha256:
            raise ValueError('input SHA-256 mismatch: ' + actual_sha)
        text = raw.decode('utf-8')
        if input_path and not (text.startswith('#=IVTFF Eva- 2.0') and 'Version 3b of 13/05/2025' in text[:300]):
            raise ValueError('expected ZL3b-n IVTFF 2.0 header missing')
        lines = extract_ivtff(text, folio)
        result['observed'] = {'source_sha256':actual_sha,
                               'source_type':'local_IVTFF_file' if input_path else 'manual_excerpt_from_source',
                               'folio':folio,'metrics':metrics(lines),
                               'limitation':'orthographic surface only; no Voynich semantics; manual subset not full-file provenance' if not input_path else 'orthographic surface only; not a translation'}
    return result


def self_test():
    assert len(STEMS) == 25
    cases = scenario_lines(n=300)
    a, av = generate('C1A',cases)
    b, bv = generate('C1B',cases)
    assert av['marker_count'] >= bv['marker_count']
    assert av['ambiguous_decode_accuracy'] == 1.0
    assert bv['ambiguous_decode_accuracy'] == 1.0
    assert shuffled_context_accuracy(a,cases) < av['ambiguous_decode_accuracy']
    assert shuffled_context_accuracy(b,cases) < bv['ambiguous_decode_accuracy']
    assert extract_ivtff('<f4r.1,+P0>     dak.en,tor.mir<!note><->sal<$>\n', 'f4r') == [['dak','mir','sal']]
    assert distance_up_to_one('dak','daken') is False
    assert distance_up_to_one('dak','dak') and distance_up_to_one('dak','dat')
    assert not distance_up_to_one('dak','tuv')
    return {'self_test':'PASS', 'rules_frozen': VERSION, 'ambiguous_test_cases':av['ambiguous']}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',help='local source-file path; never downloaded')
    ap.add_argument('--folio',default='f4r')
    ap.add_argument('--seed',type=int,default=SEED)
    ap.add_argument('--expected-sha256',help='optional expected digest, must match exact input bytes')
    ap.add_argument('--self-test',action='store_true')
    args=ap.parse_args()
    print(json.dumps(self_test() if args.self_test else pilot(seed=args.seed,input_path=args.input,folio=args.folio,expected_sha256=args.expected_sha256),indent=2,sort_keys=True))

if __name__ == '__main__':
    main()

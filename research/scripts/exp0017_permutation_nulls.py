#!/usr/bin/env python3
"""EXP-0017: reproducible, composition-preserving permutation tests of EXP-0015.

Requires existing NumPy and Numba installations and the owner's original CV script.
No network calls; no third-party packages installed by this script.
The original CV file is imported for its exact parser/line/fold implementation.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import random
from pathlib import Path

import numpy as np
from numba import njit

@njit
def fy_shuffle_blocks(arr, starts, ends, state):
    """Deterministic Fisher-Yates using explicit SplitMix64 RNG state."""
    for block in range(len(starts)):
        a = int(starts[block])
        b = int(ends[block])
        for i in range(b-1, a, -1):
            state += np.uint64(0x9E3779B97F4A7C15)
            z = state
            z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
            z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
            z = z ^ (z >> np.uint64(31))
            j = a + int(z % np.uint64(i-a+1))
            v = arr[i]
            arr[i] = arr[j]
            arr[j] = v
    return state


EXPECTED_DATA_SHA256 = 'bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'
EXPECTED_OWNER_CV_SHA256 = '7acf5cb70b6197549d71cd2f1b91bda3a72d1c7885d63db76522454083017e89'
CLASS_TO_INT = {'OTHER': 0, 'EDY': 1, 'OL': 2, 'ORY': 3}
POLICIES = ('exclude', 'join', 'split')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_module(path):
    spec = importlib.util.spec_from_file_location('owner_cv_exp0015', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_arrays(mod, text, policy, baseline, seed=377, folds=5):
    folios, matched, empty = mod.load(text, policy)
    expected = baseline['policy_results'][policy]
    assert (matched, empty, len(folios)) == (expected['matched_transcription_lines'], expected['lines_with_no_accepted_tokens'], expected['folios'])
    original = mod.evaluate(folios, seed, folds)
    for key in ('folios', 'lines', 'tokens', 'transitions', 'unigram_loss', 'markov_loss', 'markov_advantage_nats'):
        assert math.isclose(float(original[key]), float(expected[key]), rel_tol=0, abs_tol=1e-12), (policy, key)
    for f1, f2 in zip(original['folds'], expected['folds']):
        for key in ('transitions', 'unigram_loss', 'markov_loss', 'markov_advantage_nats'):
            assert math.isclose(float(f1[key]), float(f2[key]), rel_tol=0, abs_tol=1e-12), (policy, f1['fold'], key)

    keys = sorted(folios)
    r = random.Random(seed)
    r.shuffle(keys)
    groups = [keys[i::folds] for i in range(folds)]
    fold_of_folio = {k: i for i, group in enumerate(groups) for k in group}
    flat, folio_id, line_id, token_fold = [], [], [], []
    left_idx, right_idx, edge_fold = [], [], []
    lid = 0
    for fid, k in enumerate(sorted(folios)):
        fold = fold_of_folio[k]
        for line in folios[k]:
            n = len(line)
            start = len(flat)
            flat.extend(CLASS_TO_INT[t] for t in line)
            folio_id.extend([fid] * n)
            line_id.extend([lid] * n)
            token_fold.extend([fold] * n)
            if n >= 2:
                left_idx.extend(range(start, start + n - 1))
                right_idx.extend(range(start + 1, start + n))
                edge_fold.extend([fold] * (n - 1))
            lid += 1
    data = {
        'x': np.array(flat, dtype=np.int8),
        'folio_id': np.array(folio_id, dtype=np.int32),
        'line_id': np.array(line_id, dtype=np.int32),
        'token_fold': np.array(token_fold, dtype=np.int8),
        'left': np.array(left_idx, dtype=np.int32),
        'right': np.array(right_idx, dtype=np.int32),
        'edge_fold': np.array(edge_fold, dtype=np.int8),
    }
    assert len(data['x']) == expected['tokens']
    assert len(data['left']) == expected['transitions']
    data['fold_uni'] = np.bincount(data['token_fold'].astype(np.int64) * 4 + data['x'].astype(np.int64), minlength=folds * 4).reshape(folds, 4)
    return data, original


def score(x, data, folds=5, alpha=0.5):
    pair_codes = 16 * data['edge_fold'].astype(np.int64) + 4 * x[data['left']].astype(np.int64) + x[data['right']].astype(np.int64)
    test_bi = np.bincount(pair_codes, minlength=folds * 16).reshape(folds, 4, 4)
    train_uni = data['fold_uni'].sum(axis=0)[None, :] - data['fold_uni']
    uni_probs = (train_uni + alpha) / (train_uni.sum(axis=1, keepdims=True) + 4 * alpha)
    train_bi = test_bi.sum(axis=0)[None, :, :] - test_bi
    markov_probs = (train_bi + alpha) / (train_bi.sum(axis=2, keepdims=True) + 4 * alpha)
    n = test_bi.sum()
    u = -float(np.sum(test_bi * np.log(uni_probs[:, None, :]))) / n
    m = -float(np.sum(test_bi * np.log(markov_probs))) / n
    return u-m, u, m


def test_policy(data, baseline, count=1000, seed=150377):
    observed, u, m = score(data['x'], data)
    assert abs(observed - baseline['markov_advantage_nats']) < 1e-12, (observed, baseline['markov_advantage_nats'])
    results = {}
    for family, ids in [('within_folio', data['folio_id']), ('within_line', data['line_id'])]:
        # Each block comprises contiguous folio/line token slots; preserve its exact class composition.
        changes = np.flatnonzero(ids[1:] != ids[:-1]) + 1
        starts = np.r_[0, changes].astype(np.int32)
        ends = np.r_[changes, len(ids)].astype(np.int32)
        state = np.uint64(seed)
        scores = []
        for j in range(count):
            shuffled = data['x'].copy()
            state = np.uint64(fy_shuffle_blocks(shuffled, starts, ends, np.uint64(state)))
            gain, _, _ = score(shuffled, data)
            scores.append(gain)
        scores = np.array(scores)
        exceed = int((scores >= observed).sum())
        results[family] = {
            'seed': seed,
            'iterations': count,
            'null_mean': float(scores.mean()),
            'null_sd': float(scores.std(ddof=1)),
            'null_2_5_percentile': float(np.percentile(scores, 2.5)),
            'null_97_5_percentile': float(np.percentile(scores, 97.5)),
            'null_min': float(scores.min()),
            'null_max': float(scores.max()),
            'exceedances': exceed,
            'one_sided_empirical_p': (exceed + 1) / (count + 1),
            'raw_null_gains_nats': scores.tolist(),
        }
    return {'observed_gain': observed, 'observed_unigram_loss': u, 'observed_markov_loss': m, 'nulls': results}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--original-cv', type=Path, required=True)
    ap.add_argument('--baseline-json', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--permutations', type=int, default=1000)
    ap.add_argument('--seed', type=int, default=150377)
    args = ap.parse_args()
    assert args.permutations >= 1
    digest = sha256(args.input)
    code_digest = sha256(args.original_cv)
    assert digest == EXPECTED_DATA_SHA256, digest
    assert code_digest == EXPECTED_OWNER_CV_SHA256, code_digest
    baseline = json.loads(args.baseline_json.read_text(encoding='utf-8'))
    assert baseline['sha256'] == digest and baseline['seed'] == 377 and baseline['folds'] == 5 and baseline['alpha'] == 0.5
    mod = load_module(args.original_cv)
    text = args.input.read_bytes().decode('utf-8-sig')
    output = {'experiment_id': 'EXP-0017', 'input_sha256': digest, 'owner_cv_script_sha256': code_digest,
              'baseline_json_sha256': sha256(args.baseline_json), 'seed': args.seed,
              'permutations_per_policy_per_family': args.permutations,
              'numpy_version': np.__version__,
              'null_rng': 'explicit SplitMix64, state 150377, Numba-compiled Fisher-Yates',
              'shuffle_method': 'per-block Fisher-Yates from original class slots, sequential pseudorandom draws',
              'baseline_validation': 'Original Python evaluator matches uploaded JSON and vectorized sufficient statistics within 1e-12',
              'policy_results': {}}
    for policy in POLICIES:
        data, original = build_arrays(mod, text, policy, baseline)
        result = test_policy(data, baseline['policy_results'][policy], args.permutations, args.seed)
        output['policy_results'][policy] = result
        summary = {family:{k:v for k,v in z.items() if k != 'raw_null_gains_nats'} for family,z in result['nulls'].items()}
        print(json.dumps({'policy':policy, 'observed':result['observed_gain'], 'nulls':summary}, ensure_ascii=False), flush=True)
    args.output.write_text(json.dumps(output, indent=2), encoding='utf-8')
    print('OUTPUT', args.output, flush=True)

if __name__ == '__main__':
    main()

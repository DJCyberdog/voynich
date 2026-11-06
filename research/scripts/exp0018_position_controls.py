#!/usr/bin/env python3
"""EXP-0018: position- and line-length-exact permutation nulls.

Primary null: independently exchangeable four-class tokens across *different
lines* only within (folio ID, accepted-token line length, exact token offset).
This preserves every folio's 2D class histogram by (line length, position),
as well as line lengths, fold allocation, and all univariate statistics.

Secondary null: within (folio ID, exact token offset) irrespective of length.
This preserves exact absolute position by folio but not its joint distribution
with line length. The primary null is more conservative.

This tests position-conditioned exchangeability, not linguistic semantics.
No downloads, external packages installation, or corpus redistributions.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
from numba import njit

INPUT_SHA = 'bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'
OWNER_SHA = '7acf5cb70b6197549d71cd2f1b91bda3a72d1c7885d63db76522454083017e89'
SCORE_SHA = '24bebe12f1e214636122f0bf90351bcaa36584b1d86e9ba8f04c7d34acea97d3'


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_path(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


@njit
# SplitMix64 + Fisher-Yates; state is persisted between randomizations
# Match EXP-0017's RNG and sampling protocol, but shuffle INDIRECT noncontiguous slots.
def shuffle_strata(values, order, starts, ends, state):
    for k in range(len(starts)):
        a = int(starts[k]); b = int(ends[k])
        for off in range(b - 1, a, -1):
            state += np.uint64(0x9E3779B97F4A7C15)
            z = state
            z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
            z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
            z = z ^ (z >> np.uint64(31))
            j = a + int(z % np.uint64(off - a + 1))
            left, right = int(order[off]), int(order[j])
            tmp = values[left]
            values[left] = values[right]
            values[right] = tmp
    return state


def strata(data, kind):
    x = data['x']
    line_id = data['line_id']
    nlines = (int(line_id.max()) + 1)
    lengths = np.bincount(line_id, minlength=nlines)
    starts = np.zeros(nlines, dtype=np.int64)
    starts[1:] = np.cumsum(lengths)[:-1]
    pos = np.arange(len(x), dtype=np.int64) - starts[line_id]
    token_len = lengths[line_id]
    fid = data['folio_id'].astype(np.int64)
    if kind == 'folio_len_pos':
        # sort exact lexicographic triples with position minor key
        order = np.lexsort((pos, token_len, fid)).astype(np.int32)
        changed = (fid[order][1:] != fid[order][:-1]) | (token_len[order][1:] != token_len[order][:-1]) | (pos[order][1:] != pos[order][:-1])
    elif kind == 'folio_pos':
        order = np.lexsort((pos, fid)).astype(np.int32)
        changed = (fid[order][1:] != fid[order][:-1]) | (pos[order][1:] != pos[order][:-1])
    else:
        raise ValueError(kind)
    boundaries = np.flatnonzero(changed) + 1
    starts = np.r_[0, boundaries].astype(np.int32)
    ends = np.r_[boundaries, len(x)].astype(np.int32)
    sizes = ends - starts
    eligible = np.zeros(len(x), dtype=bool)
    for a, b in zip(starts[sizes >= 2], ends[sizes >= 2]):
        eligible[order[a:b]] = True
    mobile_edge = eligible[data['left']] & eligible[data['right']]
    return order, starts, ends, {
        'group_count': len(starts),
        'groups_size_at_least_2': int((sizes >= 2).sum()),
        'group_size_max': int(sizes.max()),
        'eligible_tokens': int(eligible.sum()),
        'eligible_token_fraction': float(eligible.mean()),
        'both_endpoints_mobile_edges': int(mobile_edge.sum()),
        'both_endpoints_mobile_edges_fraction': float(mobile_edge.mean()),
    }, (fid, token_len, pos)


def verify_preservation(x, perm, feature_key):
    """Compare exact per-stratum class counts and all group IDs before and after."""
    _, inv = np.unique(feature_key, return_inverse=True, axis=0)
    codes_original = inv * 4 + x
    codes_perm = inv * 4 + perm
    total = (int(inv.max())+1) * 4
    assert np.array_equal(np.bincount(codes_original, minlength=total), np.bincount(codes_perm, minlength=total))


def execute_policy(mod, score_mod, text, baseline, policy, permutations, seed):
    data, original = score_mod.build_arrays(mod, text, policy, baseline)
    observed, u, m = score_mod.score(data['x'], data)
    assert abs(observed - baseline['policy_results'][policy]['markov_advantage_nats']) < 1e-12
    nulls = {}
    for family in ('folio_len_pos', 'folio_pos'):
        order, starts, ends, stats, (folio, lengths, pos) = strata(data, family)
        feature_key = np.stack((folio, lengths, pos), axis=1) if family == 'folio_len_pos' else np.stack((folio, pos), axis=1)
        rng_state = np.uint64(seed)
        scores = np.empty(permutations)
        for i in range(permutations):
            shuffled = data['x'].copy()
            rng_state = np.uint64(shuffle_strata(shuffled, order, starts, ends, rng_state))
            if i in (0, permutations - 1):
                verify_preservation(data['x'], shuffled, feature_key)
                assert np.array_equal(np.bincount(data['folio_id'] * 4 + shuffled, minlength=226 * 4),
                                      np.bincount(data['folio_id'] * 4 + data['x'], minlength=226 * 4))
            scores[i] = score_mod.score(shuffled, data)[0]
        exceedances = int(np.count_nonzero(scores >= observed))
        nulls[family] = {
            'preserved': 'exact per-folio x line-length x absolute-position class counts' if family == 'folio_len_pos' else 'exact per-folio x absolute-position class counts',
            **stats,
            'iterations': int(permutations), 'null_mean': float(scores.mean()),
            'null_sd': float(scores.std(ddof=1)),
            'null_2_5_percentile': float(np.percentile(scores, 2.5)),
            'null_97_5_percentile': float(np.percentile(scores, 97.5)),
            'null_max': float(scores.max()), 'null_min': float(scores.min()),
            'exceedances': exceedances, 'one_sided_empirical_p': (exceedances + 1)/(permutations + 1),
            'raw_null_gains': scores.tolist()
        }
    return {'observed_gain': float(observed), 'original_unigram_loss': float(u), 'original_markov_loss': float(m), 'transitions': int(len(data['left'])), 'nulls': nulls}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--owner-script', type=Path, required=True)
    ap.add_argument('--previous-evaluator', type=Path, required=True)
    ap.add_argument('--baseline-json', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--permutations', type=int, default=1000)
    ap.add_argument('--seed', type=int, default=180377)
    args = ap.parse_args()
    assert args.permutations >= 1
    assert checksum(args.input) == INPUT_SHA
    assert checksum(args.owner_script) == OWNER_SHA
    assert checksum(args.previous_evaluator) == SCORE_SHA
    baseline = json.loads(args.baseline_json.read_text())
    assert baseline['sha256'] == INPUT_SHA and baseline['seed'] == 377 and baseline['folds'] == 5
    mod = load_path(args.owner_script, 'owner_exp0015')
    score_mod = load_path(args.previous_evaluator, 'score_exp0017')
    text = args.input.read_bytes().decode('utf-8-sig')
    results = {'experiment': 'EXP-0018', 'dataset_sha256':INPUT_SHA,
               'owner_evaluator_sha256': OWNER_SHA, 'score_evaluator_sha256': SCORE_SHA,
               'baseline_sha256': checksum(args.baseline_json),
               'seed':args.seed,'permutations_per_policy_per_null':args.permutations,
               'fold_seed':377,'score_alpha':0.5,'status':'EXPLORATORY (experiment was preregistered as a test family but this exact strict stratification was frozen before these draws)',
               'policy_results':{}}
    for policy in ('exclude','join','split'):
        print('Running',policy,flush=True)
        results['policy_results'][policy] = execute_policy(mod,score_mod,text,baseline,policy,args.permutations,args.seed)
        for key,item in results['policy_results'][policy]['nulls'].items():
            print(policy,key,'mean',round(item['null_mean'],9),'p',item['one_sided_empirical_p'],'eligible',round(item['eligible_token_fraction'],3),'max',round(item['null_max'],9),flush=True)
    args.output.write_text(json.dumps(results,indent=2),encoding='utf-8')
    print('Output:',args.output,flush=True)

if __name__ == '__main__':
    main()

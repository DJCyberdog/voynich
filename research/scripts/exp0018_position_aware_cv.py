#!/usr/bin/env python3
"""EXP-0018 secondary exploratory position-aware held-out prediction.

Baseline: P(next class | exact accepted-token line length, exact next offset)
Augmented: P(next class | preceding class, same length, same next offset).
Identical five original folio-held-out folds, training-only smoothing priors.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def evaluate(owner, score_mod, corpus, baseline, policy):
    data, _ = score_mod.build_arrays(owner, corpus, policy, baseline)
    line_id = data['line_id']
    count = np.bincount(line_id)
    line_starts = np.r_[0, np.cumsum(count)[:-1]]
    offset = np.arange(len(line_id)) - line_starts[line_id]
    line_length = count[line_id]
    exact_features, g = np.unique(
        np.stack((line_length[data['right']], offset[data['right']]), axis=1),
        return_inverse=True, axis=0)
    context_count = len(exact_features)
    f = data['edge_fold']
    previous = data['x'][data['left']]
    target = data['x'][data['right']]
    edges = len(target)
    # Counts indexed by held-out fold, exact length-position context, previous, target.
    all_counts = np.bincount(
        (((f.astype(np.int64) * context_count + g) * 4 + previous) * 4 + target),
        minlength=5 * context_count * 16
    ).reshape(5, context_count, 4, 4)
    beta_results = {5: [0., 0.], 20: [0., 0.], 100: [0., 0.]}
    fold_results = {}
    for fold in range(5):
        training = all_counts.sum(axis=0) - all_counts[fold]
        # Training-only target-class prior. Never fit on withheld folio labels.
        global_targ = training.sum(axis=(0, 1))
        global_prior = (global_targ + 0.5)/(global_targ.sum() + 2.)
        poscounts = training.sum(axis=1)
        posprob = (poscounts + 20. * global_prior[None, :]) / (poscounts.sum(axis=1)[:, None] + 20.)
        which = (f == fold)
        gg, aa, bb = g[which], previous[which], target[which]
        baseline_nll = -np.log(posprob[gg, bb]).sum()
        fold_results[str(fold + 1)] = {'transitions': int(which.sum()), 'extra_gain_by_beta': {}}
        for beta in (5, 20, 100):
            augmented = (training + beta * posprob[:, None, :]) / (training.sum(axis=2)[:, :, None] + beta)
            markov_nll = -np.log(augmented[gg, aa, bb]).sum()
            beta_results[beta][0] += baseline_nll
            beta_results[beta][1] += markov_nll
            fold_results[str(fold + 1)]['extra_gain_by_beta'][str(beta)] = float((baseline_nll - markov_nll)/which.sum())
    return {
        'exact_length_position_context_count': context_count,
        'transitions': edges,
        'folds': fold_results,
        'results_by_beta': {
            str(beta): {
                'position_only_loss': float(result[0]/edges),
                'position_plus_previous_loss': float(result[1]/edges),
                'extra_gain': float((result[0]-result[1])/edges)
            } for beta, result in beta_results.items()
        }
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--owner-script',type=Path,required=True)
    p.add_argument('--previous-evaluator',type=Path,required=True)
    p.add_argument('--baseline-json',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    assert digest(args.input)=='bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'
    assert digest(args.owner_script)=='7acf5cb70b6197549d71cd2f1b91bda3a72d1c7885d63db76522454083017e89'
    assert digest(args.previous_evaluator)=='24bebe12f1e214636122f0bf90351bcaa36584b1d86e9ba8f04c7d34acea97d3'
    corpus=args.input.read_bytes().decode('utf-8-sig')
    baseline=json.loads(args.baseline_json.read_text())
    assert baseline['sha256']==digest(args.input)
    owner=load(args.owner_script,'owner_exp0015')
    scorer=load(args.previous_evaluator,'scorer_exp0017')
    output={'experiment':'EXP-0018', 'type':'EXPLORATORY held-out position-aware comparison',
            'dataset_sha256':digest(args.input),'fold_seed':377,
            'position_prior_strength':20,'previous_class_prior_strengths':[5,20,100],
            'policies':{}}
    for policy in ('exclude','join','split'):
        output['policies'][policy]=evaluate(owner,scorer,corpus,baseline,policy)
        print(policy,output['policies'][policy]['results_by_beta'],flush=True)
    args.output.write_text(json.dumps(output,indent=2),encoding='utf-8')
if __name__=='__main__':
    main()

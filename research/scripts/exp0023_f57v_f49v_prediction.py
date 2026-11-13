#!/usr/bin/env python3
"""EXP-0023: retrospective f57v/f49v list prediction, Python stdlib only.
Requires owner-held ZL3b-n v3b IVTFF source; does not fetch/copy source data.
Programmatic masking is NOT prospective independent manuscript blinding.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import re

SOURCE_SHA = "bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc"

def parse(path):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise ValueError("ZL3b-n v3b source SHA256 mismatch")
    text = raw.decode("utf-8-sig")
    line = next(s for s in text.splitlines() if s.startswith("<f57v.3,+Cc>"))
    body = re.sub(r"^<f57v\\.3,\\+Cc>\\s*<![^>]*>", "", line).strip()
    ring = body.split(".")
    if ring[-1] == "":
        ring.pop()
    assert len(ring) == 68 and all(ring[i] == "o" for i in (0, 17, 34, 51))
    margin = []
    for line in text.splitlines():
        match = re.match(r"^<f49v\\.\\d+,[*@]L0>\\s+(\\S+)\\s*$", line)
        if match:
            margin.append(match.group(1))
    assert len(margin) == 26
    return ring, margin

def select_lag(training, minimum, maximum, min_pairs):
    scores = {}
    for lag in range(minimum, maximum + 1):
        n = len(training) - lag
        if n < min_pairs:
            continue
        hits = sum(training[i] == training[i - lag] for i in range(lag, len(training)))
        scores[lag] = dict(hits=hits, pairs=n, rate=hits / n)
    selected = max(scores, key=lambda k: (scores[k]["rate"], scores[k]["hits"], -k))
    return selected, scores

def fixed_predict(training, length, lag):
    reference = training[-lag:]
    return [reference[i % lag] for i in range(length)]

def shuffle_diagnostic(pred, target, seed=57049, reps=10000):
    rng = random.Random(seed)
    copy = list(target)
    obs = sum(a == b for a, b in zip(pred, target))
    vals = []
    for _ in range(reps):
        rng.shuffle(copy)
        vals.append(sum(a == b for a, b in zip(pred, copy)))
    return dict(draws=reps, observed=obs, null_mean=sum(vals)/len(vals),
                null_max=max(vals), exceedances=sum(v >= obs for v in vals),
                monte_carlo_p=(sum(v >= obs for v in vals)+1)/(len(vals)+1))

def evaluate(ring, margin):
    training, target = ring[:34], ring[34:]
    lag, scores = select_lag(training, 2, 20, 14)
    predictions = fixed_predict(training, len(target), lag)
    result = {
        "source_sha256": SOURCE_SHA, "evidence_scope": "RETROSPECTIVE_IVTFF_ONLY",
        "f57v": {
            "transcription_units": len(ring), "cycles": 4, "units_per_cycle": 17,
            "training_units": 34, "test_units": 34, "learned_lag": lag,
            "lag17_training_hits": scores[17]["hits"],
            "test_hits": sum(a == b for a, b in zip(predictions, target)),
            "test_cycle_hits": [
                sum(a == b for a,b in zip(predictions[k:k+17], target[k:k+17]))
                for k in (0,17)],
            "missed_positions_1based": [
                i + 35 for i,(a,b) in enumerate(zip(predictions,target)) if a != b],
            "permutation_control": shuffle_diagnostic(predictions,target),
        }
    }
    training, target = margin[:14], margin[14:]
    lag, scores = select_lag(training, 2, 9, 5)
    predictions = fixed_predict(training, len(target), lag)
    output = {
        "transcription_units": 26, "training_units": 14, "test_units": 12,
        "learned_period": lag, "training_hits": scores[lag]["hits"],
        "training_pair_count": scores[lag]["pairs"],
        "test_hits": sum(a == b for a,b in zip(predictions,target)),
        "fixed_period_control": shuffle_diagnostic(predictions,target),
    }
    # Automatically choose a training-only, nonoverlapping near-repeat,
    # same first symbol, at most one error. Last exemplar is the template.
    candidates=[]
    for width in range(3,9):
        for i in range(len(training)-width+1):
            for j in range(i+width,len(training)-width+1):
                left,right=training[i:i+width],training[j:j+width]
                errors=sum(a != b for a,b in zip(left,right))
                if left[0]==right[0] and errors<=1:
                    candidates.append((width,-errors,j,i))
    assert candidates
    width,negative_errors,j,i=max(candidates)
    exemplar=training[j:j+width]
    anchors=[h for h in range(14,len(margin)-width+1) if margin[h]==exemplar[0]]
    forecasts={k:exemplar[k-h] for h in anchors for k in range(h+1,h+width)}
    hits=sum(margin[k]==v for k,v in forecasts.items())
    rng=random.Random(57050)
    indices=[k for k in range(14,26) if k not in anchors]
    pool=[margin[k] for k in indices]
    scores=[]
    for _ in range(10000):
        rng.shuffle(pool)
        table=dict(zip(indices,pool))
        scores.append(sum(table.get(k,margin[k])==v for k,v in forecasts.items()))
    output["contextual_motif"]={
        "training_width":width,"training_pair_positions_1based":[i+1,j+1],
        "training_pair_mismatches":-negative_errors,
        "holdout_anchor_positions_1based":[k+1 for k in anchors],
        "forecasted_positions_1based":[k+1 for k in sorted(forecasts)],
        "correct":hits,"forecast_total":len(forecasts),
        "conditional_shuffle_mean":sum(scores)/len(scores),
        "conditional_shuffle_max":max(scores),
        "conditional_shuffle_exceedances":sum(x>=hits for x in scores),
        "conditional_shuffle_p":(1+sum(x>=hits for x in scores))/(len(scores)+1),
        "caveat":"anchor observed, not forecast; retrospective motif selection",
    }
    # Deliberately easier sequential baseline uses true predecessor in test.
    nexts=defaultdict(list)
    for a,b in zip(training[:-1],training[1:]):
        nexts[a].append(b)
    mapping={}
    for a,possibilities in nexts.items():
        freq=Counter(possibilities)
        maxf=max(freq.values())
        mapping[a]=next(v for v in reversed(possibilities) if freq[v]==maxf)
    global_fallback=Counter(training).most_common(1)[0][0]
    control=[mapping.get(margin[k-1],global_fallback) for k in range(14,26)]
    output["sequential_one_step_baseline"]={
        "correct":sum(a==b for a,b in zip(control,target)),
        "total":len(target),"uses_observed_prior_test_symbol":True}
    result["f49v"]=output
    assert result["f57v"]["learned_lag"]==17
    assert result["f57v"]["test_hits"]==32
    assert result["f49v"]["learned_period"]==8
    assert result["f49v"]["test_hits"]==0
    assert result["f49v"]["contextual_motif"]["correct"]==4
    return result

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True,help="owner-held ZL3b-n v3b path")
    args=parser.parse_args()
    ring,margin=parse(args.input)
    print(json.dumps(evaluate(ring,margin),indent=2))

#!/usr/bin/env python3
"""EXP-0021: limited EVA q-initial line-start test; Python stdlib only.

Input: original ZL3b-n v3b IVTFF from https://www.voynich.nu/data/ZL3b-n.txt
No manuscript scans, fonts, or transcription bytes embedded in this script.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

LINE = re.compile(r"^<(?P<folio>f3r|f8r)\.(?P<num>\d+),(?P<tag>[^>]+)>\s+(?P<body>.*)$")
WORD = re.compile(r"[a-z]+\Z")


def tokenize(body):
    body = body.replace("<%>", "").replace("<$>", "").replace("<->", ".")
    body = re.sub(r"<!.*?>", "", body)
    pieces = body.split(".")
    if not WORD.fullmatch(pieces[0]):
        return None
    tokens = [t for t in pieces if WORD.fullmatch(t)]
    assert tokens and tokens[0] == pieces[0]
    return tokens


def poisson_binomial(probs):
    dist = [1.0]
    for p in probs:
        next_dist = [0.0] * (len(dist) + 1)
        for k, value in enumerate(dist):
            next_dist[k] += value * (1.0 - p)
            next_dist[k + 1] += value * p
        dist = next_dist
    assert abs(sum(dist) - 1.0) < 1e-10
    return dist


def contrast(rows, length_matched=False):
    probabilities = []
    observed = 0
    for _, _, tokens in rows:
        first = tokens[0]
        candidates = [t for t in tokens if len(t) == len(first)] if length_matched else tokens
        probabilities.append(sum(t.startswith("q") for t in candidates) / len(candidates))
        observed += first.startswith("q")
    distribution = poisson_binomial(probabilities)
    return {"observed": observed, "expected": sum(probabilities),
            "p_left_exact": sum(distribution[:observed + 1])}


def run(text):
    folios = {"f3r": [], "f8r": []}
    exclusions = {"f3r": [], "f8r": []}
    for line in text.splitlines():
        match = LINE.match(line)
        if match is None:
            continue
        folio, number, tag, body = (match.group(x) for x in ("folio", "num", "tag", "body"))
        if not tag.endswith("P0"):
            continue  # ignore labels and =Pt right-justified lines
        tokens = tokenize(body)
        if tokens is None:
            exclusions[folio].append(f"{folio}.{number}")
            continue
        folios[folio].append((f"{folio}.{number}", body, tokens))
    summary = {}
    for folio, rows in folios.items():
        assert rows, f"No eligible text rows found on {folio}"
        nonparagraph = [row for row in rows if not row[1].startswith("<%>")]
        summary[folio] = {
            "eligible_lines": len(rows),
            "excluded_ambiguous_initial": exclusions[folio],
            "retained_tokens": sum(len(row[2]) for row in rows),
            "primary": contrast(rows),
            "non_paragraph_sensitivity": {
                "eligible_lines": len(nonparagraph), **contrast(nonparagraph)},
            "length_matched_sensitivity": contrast(rows, length_matched=True),
        }
    assert poisson_binomial([0.5, 0.5]) == [0.25, 0.5, 0.25]
    summary["controls"] = {
        "negative_exact_toy_PMF": poisson_binomial([0.5, 0.5]),
        "positive_forced_q_depletion_p": poisson_binomial([0.5] * 50)[0],
    }
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("ivtff", type=Path, help="local original ZL3b-n v3b input")
    args = parser.parse_args()
    content = args.ivtff.read_bytes()
    print("input_sha256:", hashlib.sha256(content).hexdigest())
    print(json.dumps(run(content.decode("utf-8-sig")), indent=2))

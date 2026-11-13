#!/usr/bin/env python3
"""Read only IVTFF original page headers; reproduce 2026-11-10 eight-P0 audit.

Input: a locally obtained, rights-reviewed ZL3b-n v3b source file.
Output: SHA-256 and ONLY editorial page-label/hand counts (no text).
Does not read or adjudicate original handwriting images; Python stdlib only.
"""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
import re
from pathlib import Path

SAMPLE = ("f5v", "f24v", "f29r", "f43r", "f57r", "f76v", "f104v", "f113v")
EXPECT = {
    "f5v":   ("A", "1", "1", "H"),
    "f24v":  ("A", "1", "1", "H"),
    "f29r":  ("A", "1", "1", "H"),
    "f43r":  ("B", "2", "2", "H"),
    "f57r":  ("B", "5", "2", "H"),
    "f76v":  ("B", "2", "2", "B"),
    "f104v": ("B", "3", "X", "S"),
    "f113v": ("B", "3", None, "S"),
}
HEADER = re.compile(r"^<(?P<page>f[a-zA-Z0-9]+)>\s*<!\s*(?P<meta>[^>]*)>\s*$")
VAR = re.compile(r"\$([A-Z])=([^\s>]+)")

def audit(s):
    found = {}
    for line in s.splitlines():
        m = HEADER.fullmatch(line.strip())
        if m is None or m.group("page") not in EXPECT:
            continue
        p = m.group("page")
        if p in found:
            raise ValueError(f"duplicate page header {p}")
        v = dict(VAR.findall(m.group("meta")))
        found[p] = (v.get("L"), v.get("H"), v.get("C"), v.get("I"))
    missing = set(SAMPLE).difference(found)
    if missing:
        raise ValueError(f"missing requested folio headers: {sorted(missing)}")
    mismatch = {p: {"expected": EXPECT[p], "actual": found[p]}
                for p in SAMPLE if found[p] != EXPECT[p]}
    language_by_davis_hand = defaultdict(set)
    for p in SAMPLE:
        lang, h, _, _ = found[p]
        if lang is not None and h is not None:
            language_by_davis_hand[h].add(lang)
    tally = Counter((found[p][0], found[p][1]) for p in SAMPLE)
    differing_hands = [p for p in SAMPLE if found[p][2] is not None
                       and found[p][1] != found[p][2]]
    return {
        "page_count": len(found),
        "fixed_sample": list(SAMPLE),
        "source_header_tuple_mismatch": mismatch,
        "L_by_H": {h: sorted(vals) for h, vals in sorted(language_by_davis_hand.items())},
        "L_H_counts": [{"L": l, "H": h, "pages": n} for (l, h), n in sorted(tally.items())],
        "different_H_and_C": differing_hands,
        "warning": "Source-annotation metadata only, convenience sample, no image or manuscript-causality inference",
    }

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("ivtff", type=Path)
    arg = ap.parse_args()
    raw = arg.ivtff.read_bytes()
    result = audit(raw.decode("utf-8-sig"))
    result["input_sha256"] = sha256(raw).hexdigest()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["source_header_tuple_mismatch"]:
        raise SystemExit("Original-source metadata differs from the recorded v3b eight-page audit")

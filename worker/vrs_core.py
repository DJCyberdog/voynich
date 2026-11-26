"""Lightweight shared data contracts for local review; no compute or network dependencies.

The six legacy helpers retain v0.8.1 semantics. The legacy worker is left
unchanged because existing checkpoints and evidence may bind its source hash.
"""
import hashlib
import json
import os
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    temp = p.with_name(p.name + ".tmp")
    temp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temp, p)


def within(root, name):
    p = (Path(root) / name).resolve()
    require(p.is_relative_to(Path(root).resolve()), "Path escapes workspace")
    return p


def dataset(path):
    p = Path(path)
    m = read(p)
    regions = m["regions"]
    require(regions and len({r["id"] for r in regions}) == len(regions), "Duplicate/empty regions")
    for r in regions:
        require(isinstance(r["group"], str) and r["group"].strip(), "Missing group")
        require(sha(within(p.parent, r["file"])) == r["sha256"], "Crop hash mismatch: " + r["id"])
    return m

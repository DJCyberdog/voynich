"""v0.3.0: opt-in GitHub transport for approved jobs and aggregate-only PRs."""
import argparse
import base64
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
import pipeline as p
import worker as w

VERSION = "0.3.0"
REPO = "DJCyberdog/voynich"
HEX = re.compile(r"[0-9a-f]{64}")
GIT = re.compile(r"[0-9a-f]{40}")
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class API:
    def __init__(self, token):
        w.require(bool(token), "Set VOYNICH_GITHUB_TOKEN locally")
        self.token = token
        self.opener = build_opener(NoRedirect())

    def call(self, method, path, data=None, missing=False):
        url = "https://api.github.com/repos/" + REPO + "/" + path
        body = None if data is None else json.dumps(data).encode()
        req = Request(url, data=body, method=method, headers={
            "Authorization": "Bearer " + self.token, "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Voynich-Worker/0.3.0",
            "Content-Type": "application/json"})
        try:
            with self.opener.open(req, timeout=30) as response:
                raw = response.read(4_000_001)
                w.require(len(raw) <= 4_000_000, "API response too large")
                return json.loads(raw)
        except HTTPError as exc:
            if missing and exc.code == 404:
                return None
            raise RuntimeError(f"GitHub HTTP {exc.code}; retry later or inspect permissions") from None

    def blob(self, path, ref, missing=False):
        w.require(bool(GIT.fullmatch(ref)), "Full commit SHA required")
        item = self.call("GET", "contents/" + path + "?" + urlencode({"ref": ref}), missing=missing)
        if item is None:
            return None
        w.require(item["type"] == "file" and item["encoding"] == "base64" and item["size"] <= 65536, "Invalid or oversized blob")
        raw = base64.b64decode("".join(item["content"].split()), validate=True)
        w.require(len(raw) == item["size"], "Blob size mismatch")
        return raw


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(obj):
    return (json.dumps(obj, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def permit(root, job, policy):
    w.require(set(policy) == {"schema", "allowed_inputs", "actions", "publish"} and policy["schema"] == 1, "Invalid local policy")
    w.require(type(policy["publish"]) is bool and isinstance(policy["actions"], list), "Invalid policy flags")
    w.require(job["action"] in policy["actions"], "Action not locally approved")
    for v in job["inputs"].values():
        w.require(policy["allowed_inputs"].get(v["path"]) == v["sha256"], "Input not locally approved")
    p.validate(root, job)
    o = job["options"]
    for name, limit in (("epochs", 50), ("batch", 64)):
        if name in o:
            w.require(type(o[name]) is int and 1 <= o[name] <= limit, "Resource limit exceeded")
    if "pages" in o:
        w.require(isinstance(o["pages"], list) and 0 < len(o["pages"]) <= 213, "Page limit exceeded")


def pull(root, api, policy, main):
    raw = api.blob("worker/jobs/approved.json", main, missing=True)
    if raw is None:
        return []
    index = json.loads(raw)
    w.require(set(index) == {"schema", "jobs"} and index["schema"] == 1 and isinstance(index["jobs"], list) and len(index["jobs"]) <= 100, "Invalid approval index")
    entries = index["jobs"]
    w.require(all(set(e) == {"id", "sha256"} and ID.fullmatch(e["id"]) and HEX.fullmatch(e["sha256"]) and e["id"] != "approved" for e in entries), "Invalid approval entry")
    w.require(len({e["id"].casefold() for e in entries}) == len(entries), "Duplicate approved ID")
    accepted = []
    for e in entries:
        jid = e["id"]
        raw = api.blob(f"worker/jobs/{jid}.json", main)
        w.require(digest(raw) == e["sha256"], "Approved job hash mismatch")
        job = json.loads(raw)
        w.require(job["id"] == jid, "Approved ID mismatch")
        permit(root, job, policy)
        local = w.within(root, f"jobs/{jid}.json")
        receipt = w.within(root, f"bridge/imports/{jid}.json")
        binding = {"id": jid, "remote_sha256": e["sha256"]}
        if receipt.exists():
            w.require(w.read(receipt) == binding, "Remote job ID reused")
        if local.exists():
            w.require(w.read(local) == job, "Local job ID collision")
        else:
            with tempfile.TemporaryDirectory() as temp:
                src = Path(temp) / "job.json"; src.write_bytes(raw)
                p.submit(root, src)
        w.write(receipt, binding)
        accepted.append(binding)
    return accepted


def safe_export(root, jid):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "export.json"
        p.export(root, jid, path); data = w.read(path)
    metrics = data["metrics"]
    counts = {"tp", "tn", "fp", "fn", "unknown_script", "unknown_non_script"} if data["action"] == "train" else {"script", "non_script", "unknown"}
    w.require(data["action"] in ("train", "predict") and data["scientific_status"] == "UNADJUDICATED", "Invalid export")
    for key, value in metrics.items():
        if key in ("counts", "excluded"):
            keys = counts if key == "counts" else {"train", "test"}
            w.require(isinstance(value, dict) and set(value) <= keys and all(type(n) is int and 0 <= n <= 10**8 for n in value.values()), "Invalid aggregate counts")
        elif key.endswith("_sha256"):
            w.require(isinstance(value, str) and HEX.fullmatch(value), "Invalid digest")
        elif key in ("train_n", "test_n"):
            w.require(type(value) is int and 0 <= value <= 10**8, "Invalid sample count")
        else:
            w.require(key in {"coverage", "accuracy_including_unknown", "sensitivity_including_unknown", "specificity_including_unknown"} and type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1, "Invalid aggregate metric")
    for key in ("job_sha256", "artifact_sha256"):
        w.require(HEX.fullmatch(data[key]), "Invalid export digest")
    return data


def publish(root, api, entry, main):
    jid = entry["id"]
    data = safe_export(root, jid)
    data.update(bridge_version=VERSION, job_id=jid, approved_job_sha256=entry["remote_sha256"])
    raw = encoded(data)
    suffix = jid.lower() + "-" + entry["remote_sha256"][:12]
    branch = "worker-results/" + suffix
    path = "worker/results/" + suffix + ".json"
    existing = api.blob(path, main, missing=True)
    if existing is not None:
        w.require(existing == raw, "Conflicting result already on main")
        return {"id": jid, "state": "INTEGRATED"}
    intent_path = w.within(root, f"bridge/publish/{jid}.json")
    intent = {"base": main, "sha256": digest(raw), "branch": branch}
    if intent_path.exists():
        old = w.read(intent_path)
        w.require(old["sha256"] == intent["sha256"] and old["branch"] == branch, "Publication changed")
        intent = old
    else:
        w.write(intent_path, intent)
    ref = api.call("GET", "git/ref/heads/" + branch, missing=True)
    if ref is None:
        api.call("POST", "git/refs", {"ref": "refs/heads/" + branch, "sha": intent["base"]})
        ref = api.call("GET", "git/ref/heads/" + branch)
    tip = ref["object"]["sha"]
    existing = api.blob(path, tip, missing=True)
    if existing is None:
        w.require(tip == intent["base"], "Unexpected result branch head")
        api.call("PUT", "contents/" + path, {"message": "Worker aggregate " + jid, "content": base64.b64encode(raw).decode(), "branch": branch})
        tip = api.call("GET", "git/ref/heads/" + branch)["object"]["sha"]
    w.require(api.blob(path, tip) == raw, "Remote result differs")
    diff = api.call("GET", "compare/" + main + "..." + tip)
    w.require(diff["ahead_by"] == 1 and len(diff["files"]) == 1 and diff["files"][0]["filename"] == path and diff["files"][0]["status"] == "added", "Unexpected result PR scope")
    query = urlencode({"state": "all", "head": "DJCyberdog:" + branch, "base": "main", "per_page": 100})
    prs = api.call("GET", "pulls?" + query)
    if not prs:
        pr = api.call("POST", "pulls", {"title": "Worker aggregate: " + jid, "head": branch, "base": "main", "body": "Aggregate only; UNADJUDICATED. Owner review required."})
    else:
        w.require(len(prs) == 1, "Ambiguous result PR")
        pr = prs[0]
    w.require(pr["head"]["sha"] == tip and pr["head"]["ref"] == branch and pr["base"]["ref"] == "main", "Unexpected PR identity")
    return {"id": jid, "state": "PR_" + pr["state"].upper(), "number": pr["number"]}


def cycle(root, api, policy, upload=False):
    root = Path(root).resolve(); root.mkdir(parents=True, exist_ok=True)
    lock = w.within(root, "bridge.lock")
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.close(fd)
        main = api.call("GET", "git/ref/heads/main")["object"]["sha"]
        w.require(GIT.fullmatch(main), "Invalid main SHA")
        entries = pull(root, api, policy, main)
        processed = p.process(root, allowed_ids={e["id"] for e in entries})
        results = []
        if upload and policy["publish"]:
            for entry in entries:
                jid = entry["id"]
                status = w.within(root, f"status/{jid}.json")
                job = w.read(w.within(root, f"jobs/{jid}.json"))
                if status.exists() and w.read(status)["state"] == "COMPLETED" and job["action"] in ("train", "predict"):
                    results.append(publish(root, api, entry, main))
        return {"main": main, "approved": len(entries), "processed": [{"id": x["id"], "state": x["state"]} for x in processed], "published": results}
    finally:
        lock.unlink()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("root"); cli.add_argument("policy")
    cli.add_argument("--publish", action="store_true"); cli.add_argument("--watch", action="store_true")
    cli.add_argument("--interval", type=int, default=60)
    args = cli.parse_args(); w.require(30 <= args.interval <= 3600, "Interval outside 30..3600")
    api = API(os.environ.get("VOYNICH_GITHUB_TOKEN"))
    while True:
        try:
            print(json.dumps(cycle(args.root, api, w.read(args.policy), args.publish)), flush=True)
        except (RuntimeError, OSError, ValueError, KeyError, TypeError) as exc:
            print(f"Bridge stopped cycle: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            if not args.watch:
                return 1
        if not args.watch:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)

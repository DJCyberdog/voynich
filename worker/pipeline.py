"""Offline queue, region proposals, inference and safe aggregate export (0.2.0)."""
import argparse
import json
import os
import re
import sys
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path
import worker as w

VERSION = "0.2.0"
INPUTS = {"prepare": ("pdf", "review", "groups"), "propose": ("pdf", "groups"),
          "train": ("manifest", "left", "right", "split"), "predict": ("manifest", "checkpoint", "report")}
OPTIONS = {"prepare": set(), "propose": {"pages"}, "train": {"device", "epochs", "batch", "seed"},
           "predict": {"device", "batch"}}


def propose(pdf, expected_sha, groups, out, pages=None):
    """Fixed grid ink-bearing proposals, not detected text; no ground truth."""
    import fitz
    from PIL import Image, ImageOps
    w.require(w.sha(pdf) == expected_sha, "PDF SHA256 mismatch")
    out = Path(out); groups_map = w.read(groups)
    w.require(not out.exists(), "Output directory already exists")
    with fitz.open(pdf) as doc:
        pages = sorted(int(p) for p in groups_map) if pages is None else pages
        w.require(isinstance(pages, list) and pages and len(set(pages)) == len(pages), "Invalid pages")
        w.require(all(type(p) is int and 1 <= p <= len(doc) and isinstance(groups_map.get(str(p)), str) and groups_map[str(p)].strip() for p in pages), "Missing verified group or invalid page")
        out.mkdir(parents=True); (out / "crops").mkdir()
        records = []; screened = 0
        for page in sorted(pages):
            pix = doc[page-1].get_pixmap(dpi=200, colorspace=fitz.csRGB, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            gray = ImageOps.grayscale(img); width, height = img.size
            # Same nominal crop size as guided EXP-0038g, half-overlapping grid.
            for row in range(55):
                y = .018 + row * .0175
                for col in range(21):
                    x = .045 + col * .045
                    box = [x-.045, y-.018, x+.045, y+.018]
                    if box[2] > 1 or box[3] > 1: continue
                    bounds = [round(box[0]*width), round(box[1]*height), round(box[2]*width), round(box[3]*height)]
                    patch = gray.crop(bounds); hist = patch.histogram(); screened += 1
                    fraction = sum(hist[:160]) / (patch.width*patch.height)
                    if not .015 <= fraction <= .35: continue
                    rid = f"P{page:04d}-{row:02d}-{col:02d}"; name = f"crops/{rid}.png"
                    img.crop(bounds).save(out/name)
                    records.append(dict(id=rid,page=page,group=groups_map[str(page)],box=box,pixel_box=bounds,file=name,sha256=w.sha(out/name)))
    w.write(out/"manifest.json", dict(version=VERSION, source_sha256=expected_sha, groups_sha256=w.sha(groups), dpi=200,
        renderer=fitz.VersionBind, proposal_method="fixed-grid-dark-pixel-v1", screened=screened, regions=records))
    return {"screened":screened,"proposals":len(records),"status":"UNADJUDICATED"}


def predict(manifest, checkpoint, report, out, device="auto", batch=16):
    import torch
    from torch import nn
    from PIL import Image, ImageOps
    w.require(type(batch) is int and 1 <= batch <= 256, "Invalid batch")
    m = w.dataset(manifest); provenance = w.read(report)
    w.require(provenance["checkpoint_sha256"] == w.sha(checkpoint), "Checkpoint hash mismatch")
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    cfg = state["config"]
    w.require(cfg == provenance["config"] and cfg["worker_sha256"] == w.sha(w.__file__) and state["epoch"] == cfg["epochs"], "Incompatible or incomplete checkpoint")
    w.require(cfg["thresholds"] == [.2,.8], "Unexpected thresholds")
    info = w.device_info(device); dev = info["device"]
    model = nn.Sequential(nn.Conv2d(1,16,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),
        nn.Conv2d(16,32,3,padding=1),nn.ReLU(),nn.AdaptiveAvgPool2d((4,8)),nn.Flatten(),nn.Linear(1024,2)).to(dev)
    model.load_state_dict(state["model"]); model.eval(); rows=[]
    out = Path(out); w.require(not out.exists(), "Output directory already exists")
    with torch.inference_mode():
        for i in range(0,len(m["regions"]),batch):
            chunk=m["regions"][i:i+batch]; xs=[]
            for r in chunk:
                with Image.open(w.within(Path(manifest).parent,r["file"])) as im:
                    im=ImageOps.pad(im.convert("L"),(128,64),color=255)
                    xs.append(torch.tensor(list(im.tobytes()),dtype=torch.float32).reshape(1,64,128)/255)
            probs=model(torch.stack(xs).to(dev)).softmax(1)[:,1].tolist()
            for r,p in zip(chunk,probs):
                rows.append(dict(id=r["id"],page=r["page"],label="script" if p>=.8 else "non_script" if p<=.2 else "unknown",score=p))
    counts=dict(Counter(r["label"] for r in rows)); out.mkdir(parents=True)
    w.write(out/"predictions.json",dict(version=VERSION,manifest_sha256=w.sha(manifest),checkpoint_sha256=w.sha(checkpoint),environment=info,counts=counts,rows=rows,scientific_status="UNADJUDICATED",note="Uncalibrated scores; inference, not independent evaluation."))
    return counts


def validate(root, job):
    w.require(set(job)=={"schema","id","action","inputs","options"} and job["schema"]==1,"Invalid job schema")
    jid=job["id"]; action=job["action"]
    w.require(isinstance(jid,str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}",jid),"Invalid job ID")
    w.require(action in INPUTS and set(job["inputs"])==set(INPUTS[action]) and set(job["options"])<=OPTIONS[action],"Unsupported action or parameters")
    args={}
    for name,value in job["inputs"].items():
        w.require(set(value)=={"path","sha256"} and isinstance(value["path"],str) and not Path(value["path"]).is_absolute(),"Input must be a relative pinned file")
        path=w.within(root,value["path"])
        w.require(path.is_file() and w.sha(path)==value["sha256"],"Input hash mismatch: "+name)
        args[name]=str(path)
    args.update(job["options"])
    args["out"]=str(w.within(root,"outputs/"+jid))
    if action in ("prepare","propose"): args["expected_sha"]=job["inputs"]["pdf"]["sha256"]
    return args


def submit(root, source):
    root=Path(root).resolve(); job=w.read(source); validate(root,job)
    inbox=w.within(root,"jobs"); inbox.mkdir(parents=True,exist_ok=True)
    path=w.within(inbox,job["id"]+".json")
    # Publish only a complete job, and never replace an existing ID.
    fd, tmp = tempfile.mkstemp(prefix=".submit-", dir=inbox)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(job,f,sort_keys=True,indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.link(tmp,path)
    finally:
        Path(tmp).unlink()
    return job["id"]


def import_git(root, repo, commit, path, expected_sha):
    """Import an explicitly approved JSON blob from a local Git clone, never execute code."""
    w.require(re.fullmatch(r"[0-9a-f]{40}",commit),"Full Git commit SHA required")
    w.require(re.fullmatch(r"worker/jobs/[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.json",path),"Only worker/jobs/*.json allowed")
    w.require(re.fullmatch(r"[0-9a-f]{64}",expected_sha),"Expected SHA256 required")
    blob=subprocess.run(["git","-C",str(Path(repo).resolve()),"show",commit+":"+path],check=True,capture_output=True).stdout
    import hashlib
    w.require(len(blob)<=65536 and hashlib.sha256(blob).hexdigest()==expected_sha,"Git job blob hash/size mismatch")
    with tempfile.TemporaryDirectory() as temp:
        source=Path(temp)/"job.json"; source.write_bytes(blob)
        return submit(root,source)


def process(root, retry=None):
    root=Path(root).resolve(); root.mkdir(parents=True,exist_ok=True)
    lock=w.within(root,"worker.lock"); fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    try:
        os.write(fd,str(os.getpid()).encode()); os.close(fd)
        inbox=w.within(root,"jobs"); results=[]
        for path in sorted(inbox.glob("*.json")):
            jid=path.stem
            if retry is not None and retry!=jid: continue
            journal=w.within(root,"status/"+jid+".json"); old=w.read(journal) if journal.exists() else None
            digest=w.sha(path)
            if old and old["job_sha256"]!=digest: raise ValueError("Job changed after processing: "+jid)
            if old and (old["state"]=="COMPLETED" or retry is None): continue
            if retry is not None: w.require(old is not None,"Retry requires an existing journal")
            status=dict(id=jid,job_sha256=digest,state="RUNNING",version=VERSION)
            w.write(journal,status)
            try:
                job=w.read(path); args=validate(root,job); w.require(job["id"]==jid,"Job ID/file mismatch")
                action=job["action"]
                if action=="train" and (Path(args["out"])/"checkpoint.pt").exists():
                    w.require(retry is not None,"Checkpoint requires explicit retry")
                    args["resume"]=True
                if action=="train" and (Path(args["out"])/"report.json").exists():
                    raise ValueError("Completed report exists: reconcile manually; no rescore")
                {"prepare":w.prepare,"train":w.train,"propose":propose,"predict":predict}[action](**args)
                artifact=Path(args["out"])/{"prepare":"manifest.json","propose":"manifest.json","train":"report.json","predict":"predictions.json"}[action]
                status.update(state="COMPLETED",artifact_sha256=w.sha(artifact))
            except Exception as exc:
                status.update(state="FAILED",error=type(exc).__name__+": "+str(exc))
            w.write(journal,status); results.append(status)
        return results
    finally:
        lock.unlink()


def watch(root, interval=15):
    """Foreground poller for locally approved jobs; Ctrl+C stops it."""
    w.require(type(interval) is int and 1 <= interval <= 3600,"Invalid poll interval")
    while True:
        for result in process(root): print(json.dumps(result,sort_keys=True),flush=True)
        time.sleep(interval)


def export(root, jid, out):
    """Only fixed aggregate metrics, no images, paths, model or per-region predictions."""
    root=Path(root); w.require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}",jid),"Invalid job ID")
    jobpath=w.within(root,"jobs/"+jid+".json"); job=w.read(jobpath)
    status=w.read(w.within(root,"status/"+jid+".json"))
    w.require(status["state"]=="COMPLETED" and status["job_sha256"]==w.sha(jobpath),"Job not completed or changed")
    action=job["action"]; w.require(action in ("train","predict"),"Only training/inference aggregates may be exported")
    artifact=w.within(root,"outputs/"+jid+"/"+("report.json" if action=="train" else "predictions.json"))
    w.require(w.sha(artifact)==status["artifact_sha256"],"Report changed")
    report=w.read(artifact); allowed=("counts","excluded","train_n","test_n","coverage","accuracy_including_unknown","sensitivity_including_unknown","specificity_including_unknown","checkpoint_sha256","manifest_sha256")
    data={k:report[k] for k in allowed if k in report}
    w.write(out,dict(version=VERSION,action=action,job_sha256=status["job_sha256"],artifact_sha256=status["artifact_sha256"],scientific_status="UNADJUDICATED",metrics=data))


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest="cmd",required=True)
    q=sub.add_parser("submit"); q.add_argument("root"); q.add_argument("source")
    q=sub.add_parser("import-git"); q.add_argument("root"); q.add_argument("repo"); q.add_argument("commit"); q.add_argument("path"); q.add_argument("expected_sha")
    q=sub.add_parser("process"); q.add_argument("root"); q.add_argument("--retry")
    q=sub.add_parser("watch"); q.add_argument("root"); q.add_argument("--interval",type=int,default=15)
    q=sub.add_parser("export"); q.add_argument("root"); q.add_argument("jid"); q.add_argument("out")
    args=vars(p.parse_args()); cmd=args.pop("cmd"); print(json.dumps({"submit":submit,"import-git":import_git,"process":process,"watch":watch,"export":export}[cmd](**args),indent=2))

if __name__=="__main__":
    try: main()
    except KeyboardInterrupt: sys.exit(130)
    except (ValueError,RuntimeError,OSError,KeyError,TypeError,ImportError,subprocess.CalledProcessError) as e:
        print(f"Pipeline error: {e}",file=sys.stderr); sys.exit(1)

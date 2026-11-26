"""Local, offline Voynich image worker. No automatic installation or network I/O."""
import argparse
import csv
import hashlib
import json
import os
import random
import re
import sys
from pathlib import Path

VERSION = "0.1.0"
LABELS = {"script": 1, "non_script": 0, "unknown": None}


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


def device_info(request="auto"):
    import torch
    require(request in ("auto", "cpu", "cuda"), "Invalid device")
    info = {"worker": VERSION, "torch": torch.__version__, "cuda_build": torch.version.cuda,
            "device": "cpu", "gpu": None, "vram_bytes": None, "fallback_reason": None}
    if request != "cpu":
        try:
            require(torch.cuda.is_available(), "CUDA unavailable")
            x = torch.ones((16, 16), device="cuda")
            require(float((x @ x)[0, 0].item()) == 16, "CUDA compute probe failed")
            p = torch.cuda.get_device_properties(0)
            info.update(device="cuda", gpu=p.name, vram_bytes=p.total_memory,
                        capability=list(torch.cuda.get_device_capability(0)))
        except (RuntimeError, ValueError, AssertionError) as e:
            if request == "cuda":
                raise RuntimeError(f"CUDA required: {e}") from e
            info["fallback_reason"] = str(e)
    return info


def prepare(pdf, expected_sha, review, groups, out):
    import fitz
    from PIL import Image
    require(sha(pdf) == expected_sha.lower(), "PDF SHA256 mismatch")
    with Path(review).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    page_groups = read(groups)
    out = Path(out)
    require(not out.exists(), "Output directory already exists; use a new dataset directory")
    require(rows and len({r["review_id"] for r in rows}) == len(rows), "Empty or duplicate review IDs")
    entries = []
    with fitz.open(pdf) as doc:
        for r in rows:
            rid = r["review_id"]
            require(re.fullmatch(r"[A-Za-z0-9_-]+", rid), "Unsafe ID")
            page = int(r["page"])
            require(1 <= page <= len(doc), "Invalid page")
            group = page_groups.get(str(page))
            require(isinstance(group, str) and group.strip(), "Missing explicit physical-leaf group")
            x, y = float(r["text_x"]), float(r["text_y"])
            box = [x-.045, y-.018, x+.045, y+.018]
            require(0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1, "Crop out of bounds")
            entries.append((rid, page, group, box))
        out.mkdir(parents=True)
        (out / "crops").mkdir()
        records = []
        cached_page = None
        for rid, page, group, box in sorted(entries, key=lambda e: (e[1], e[0])):
            if page != cached_page:
                pix = doc[page-1].get_pixmap(dpi=200, colorspace=fitz.csRGB, alpha=False)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                cached_page = page
            w, h = img.size
            bounds = [round(box[0]*w), round(box[1]*h), round(box[2]*w), round(box[3]*h)]
            require(bounds[0] < bounds[2] and bounds[1] < bounds[3], "Empty crop")
            name = f"crops/{rid}.png"
            img.crop(bounds).save(out / name)
            records.append(dict(id=rid, page=page, group=group, box=box, pixel_box=bounds,
                                file=name, sha256=sha(out / name)))
    write(out / "manifest.json", dict(version=VERSION, source_sha256=expected_sha.lower(),
          review_sha256=sha(review), groups_sha256=sha(groups), dpi=200,
          renderer=fitz.VersionBind, regions=sorted(records, key=lambda r:r["id"])))
    return len(records)


def dataset(path):
    p = Path(path)
    m = read(p)
    regions = m["regions"]
    require(regions and len({r["id"] for r in regions}) == len(regions), "Duplicate/empty regions")
    for r in regions:
        require(isinstance(r["group"], str) and r["group"].strip(), "Missing group")
        require(sha(within(p.parent, r["file"])) == r["sha256"], "Crop hash mismatch: " + r["id"])
    return m


def annotations(path, manifest):
    a = read(path)
    require(isinstance(a["reviewer"], str) and a["reviewer"].strip(), "Reviewer ID required")
    require(a["manifest_sha256"] == sha(manifest), "Annotation manifest mismatch")
    require(all(v in LABELS for v in a["labels"].values()), "Invalid annotation label")
    return a


def cohorts(manifest, left, right, split):
    m = dataset(manifest)
    a, b = annotations(left, manifest), annotations(right, manifest)
    require(a["reviewer"] != b["reviewer"], "Two distinct reviewer IDs required")
    groups = read(split)
    train, test = groups["train"], groups["test"]
    require(all(isinstance(x, list) and x and all(isinstance(g,str) and g for g in x) for x in (train,test)), "Invalid split")
    require(len(set(train)) == len(train) and len(set(test)) == len(test), "Duplicate split group")
    require(not set(train) & set(test), "Physical-leaf leakage")
    require(set(train) | set(test) == {r["group"] for r in m["regions"]}, "Split must cover all groups")
    ids = {r["id"] for r in m["regions"]}
    require(set(a["labels"]) <= ids and set(b["labels"]) <= ids, "Unknown annotation ID")
    sets = {"train": [], "test": []}
    excluded = {"train": 0, "test": 0}
    hashes = {"train": set(), "test": set()}
    for r in m["regions"]:
        side = "train" if r["group"] in train else "test"
        hashes[side].add(r["sha256"])
        label = a["labels"].get(r["id"], "unknown")
        if label == b["labels"].get(r["id"], "unknown") and LABELS[label] is not None:
            sets[side].append((r, LABELS[label]))
        else:
            excluded[side] += 1
    require(not hashes["train"] & hashes["test"], "Exact duplicate image across split")
    for side, items in sets.items():
        require({y for _, y in items} == {0, 1}, f"Both classes required in {side}")
    return sets, excluded


def annotate(manifest, output, reviewer):
    import tkinter as tk
    from PIL import Image, ImageTk
    m = dataset(manifest)
    p = Path(output)
    require(reviewer.strip(), "Reviewer ID required")
    a = annotations(p, manifest) if p.exists() else dict(reviewer=reviewer, manifest_sha256=sha(manifest), labels={})
    require(a["reviewer"] == reviewer, "Reviewer output belongs to someone else")
    root = tk.Tk(); root.title("Voynich Worker | Blind annotation")
    info = tk.Label(root, font=("Arial", 14)); info.pack(padx=12, pady=12)
    view = tk.Label(root, bg="white"); view.pack(padx=12, pady=12)
    items = m["regions"]; index = [0]
    for i,r in enumerate(items):
        if r["id"] not in a["labels"]:
            index[0] = i; break
    def show():
        r = items[index[0]]
        image = Image.open(within(Path(manifest).parent, r["file"])).convert("RGB")
        image.thumbnail((1000, 450))
        view.image = ImageTk.PhotoImage(image); view.configure(image=view.image)
        info.configure(text=f'{index[0]+1}/{len(items)} | {r["id"]} | {a["labels"].get(r["id"], "unreviewed")} | {len(a["labels"])} saved')
    def move(delta):
        index[0] = max(0,min(len(items)-1,index[0]+delta)); show()
    def label(value):
        a["labels"][items[index[0]]["id"]] = value; write(p,a); move(1)
    bar = tk.Frame(root); bar.pack(pady=12)
    for key, title, value in [("1","1 Script","script"),("2","2 Non-script","non_script"),("3","3 Unknown / mixed","unknown")]:
        tk.Button(bar,text=title,command=lambda v=value:label(v)).pack(side="left",padx=4)
        root.bind(key,lambda e,v=value:label(v))
    for key,delta in [("Left",-1),("Right",1)]:
        tk.Button(bar,text=key,command=lambda d=delta:move(d)).pack(side="left",padx=4)
        root.bind(f"<{key}>",lambda e,d=delta:move(d))
    show(); root.mainloop()


def train(manifest, left, right, split, out, device="auto", epochs=8, batch=16, seed=42, resume=False):
    import torch
    from PIL import Image, ImageOps
    from torch import nn
    require(type(epochs) is int and 1 <= epochs <= 1000 and type(batch) is int and 1 <= batch <= 256, "Invalid epochs/batch")
    require(type(seed) is int and 0 <= seed < 2**32, "Invalid seed")
    sets, excluded = cohorts(manifest,left,right,split)
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    info = device_info(device); dev = info["device"]
    torch.set_num_threads(2)
    torch.manual_seed(seed); torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    model = nn.Sequential(nn.Conv2d(1,16,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),
        nn.Conv2d(16,32,3,padding=1),nn.ReLU(),nn.AdaptiveAvgPool2d((4,8)),nn.Flatten(),nn.Linear(1024,2)).to(dev)
    opt = torch.optim.Adam(model.parameters(),lr=.001)
    out = Path(out); out.mkdir(parents=True,exist_ok=True); ck = out / "checkpoint.pt"
    config = dict(version=VERSION, worker_sha256=sha(__file__), manifest=sha(manifest), left=sha(left), right=sha(right), split=sha(split),
                  epochs=epochs,batch=batch,seed=seed,device=dev,torch=str(torch.__version__),
                  hardware=info["gpu"],cuda_build=info["cuda_build"],thresholds=[.2,.8])
    require(not (out / "report.json").exists(), "Completed output exists; do not rescore heldout")
    require(resume == ck.exists(), "Use --resume only for an existing checkpoint")
    start=0; losses=[]
    if resume:
        saved=torch.load(ck,map_location=dev,weights_only=True)
        require(saved["config"]==config,"Checkpoint provenance/config mismatch")
        model.load_state_dict(saved["model"]); opt.load_state_dict(saved["optimizer"])
        start=saved["epoch"]; losses=saved["losses"]
        require(0 <= start <= epochs and len(losses)==start,"Invalid checkpoint epoch")
    def load(items):
        xs=[]; ys=[]
        for r,y in items:
            with Image.open(within(Path(manifest).parent,r["file"])) as im:
                im=ImageOps.pad(im.convert("L"),(128,64),color=255)
                xs.append(torch.tensor(list(im.tobytes()),dtype=torch.float32).reshape(1,64,128)/255)
            ys.append(y)
        return torch.stack(xs).to(dev),torch.tensor(ys,dtype=torch.long,device=dev)
    for epoch in range(start,epochs):
        model.train(); order=list(sets["train"]); random.Random(seed+epoch).shuffle(order); total=0.
        for i in range(0,len(order),batch):
            x,y=load(order[i:i+batch]); opt.zero_grad(); loss=nn.functional.cross_entropy(model(x),y)
            loss.backward(); opt.step(); total+=loss.item()*len(y)
        losses.append(total/len(order))
        temp=ck.with_suffix(".tmp"); torch.save(dict(config=config,epoch=epoch+1,losses=losses,model=model.state_dict(),optimizer=opt.state_dict()),temp); os.replace(temp,ck)
        print(f"Epoch {epoch+1}/{epochs}: loss={losses[-1]:.5f}",flush=True)
    model.eval(); counts={k:0 for k in ("tp","tn","fp","fn","unknown_script","unknown_non_script")}
    with torch.no_grad():
        for i in range(0,len(sets["test"]),batch):
            x,y=load(sets["test"][i:i+batch]); probs=model(x).softmax(1)[:,1].tolist()
            for p,t in zip(probs,y.tolist()):
                key=("tp" if t else "fp") if p>=.8 else ("fn" if t else "tn") if p<=.2 else ("unknown_script" if t else "unknown_non_script")
                counts[key]+=1
    n=sum(counts.values()); accepted=counts["tp"]+counts["tn"]+counts["fp"]+counts["fn"]
    report=dict(config=config,environment=info,counts=counts,excluded=excluded,train_n=len(sets["train"]),test_n=n,
        coverage=accepted/n,accuracy_including_unknown=(counts["tp"]+counts["tn"])/n,
        sensitivity_including_unknown=counts["tp"]/(counts["tp"]+counts["fn"]+counts["unknown_script"]),
        specificity_including_unknown=counts["tn"]/(counts["tn"]+counts["fp"]+counts["unknown_non_script"]),
        losses=losses,checkpoint_sha256=sha(ck),scientific_status="UNADJUDICATED",note="Reviewer IDs do not establish independence; no glyph or semantic claim.")
    write(out/"report.json",report); return report


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest="action",required=True)
    q=sub.add_parser("doctor"); q.add_argument("--device",choices=["auto","cpu","cuda"],default="auto")
    q=sub.add_parser("prepare"); q.add_argument("pdf"); q.add_argument("expected_sha"); q.add_argument("review"); q.add_argument("groups"); q.add_argument("out")
    q=sub.add_parser("annotate"); q.add_argument("manifest"); q.add_argument("output"); q.add_argument("reviewer")
    q=sub.add_parser("train")
    for name in ("manifest","left","right","split","out"): q.add_argument(name)
    q.add_argument("--device",choices=["auto","cpu","cuda"],default="auto"); q.add_argument("--epochs",type=int,default=8); q.add_argument("--batch",type=int,default=16); q.add_argument("--seed",type=int,default=42); q.add_argument("--resume",action="store_true")
    q=sub.add_parser("run"); q.add_argument("job")
    args=vars(p.parse_args()); action=args.pop("action")
    if action=="run":
        job=read(args["job"]); action=job["action"]; args=job["args"]
        require(action in ("prepare","train"), "Unsupported job action")
    funcs={"doctor":lambda device:device_info(device),"prepare":prepare,"annotate":annotate,"train":train}
    result=funcs[action](**args)
    if result is not None: print(json.dumps(result,indent=2,default=str))


if __name__=="__main__":
    try: main()
    except (ValueError,RuntimeError,OSError,KeyError,TypeError,ImportError) as e:
        print(f"Worker error: {e}",file=sys.stderr); sys.exit(1)

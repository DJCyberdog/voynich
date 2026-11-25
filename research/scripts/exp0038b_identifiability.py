import json, math, collections, pathlib
p=pathlib.Path(__file__).resolve().parents[1]/"results"/"2026-11-24_EXP-0038a_inventory.json"
d=json.loads(p.read_text())
def audit(rows,key):
    groups=collections.defaultdict(collections.Counter)
    for x in rows: groups[key(x)][x["shape"]]+=1
    return {"groups":dict(groups),"mixed":sum(len(c)>1 for c in groups.values()),"assignments":math.prod(math.comb(sum(c.values()),c.get("pedestal",0)) for c in groups.values())}
assert audit([{"shape":s} for s in ["pedestal","pedestal","broad_body","broad_body"]],lambda x:0)["assignments"]==6
assert audit([{"shape":s} for s in ["pedestal","broad_body"]],lambda x:x["shape"])["assignments"]==1
out={}
for name,rows in [("all",d["objects"]),("candidate",[x for x in d["objects"] if x["writing_box"]]),("strict",[x for x in d["objects"] if x["attachment"]=="inside_object"])]:
    out[name]={"n":len(rows),"root":audit(rows,lambda x:d["pages"][str(x["page"])]["root"]),"page":audit(rows,lambda x:str(x["page"]))}
print(json.dumps(out,sort_keys=True,indent=2))

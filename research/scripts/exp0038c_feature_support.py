import json, math
from pathlib import Path
from collections import defaultdict
p=Path(__file__).resolve().parents[1]/"results"/"2026-11-25_EXP-0038c_inventory.json"
rows=json.loads(p.read_text())["rows"]
def yn(v): return None if v=="?" else v=="Y"
features={"pedestal":lambda r:None if r["silhouette"]=="?" else r["silhouette"]=="P","blue_top":lambda r:None if r["top_color"] in ("?","mixed") else r["top_color"]=="blue","pointed":lambda r:yn(r["pointed"]),"feet":lambda r:yn(r["discrete_feet"]),"bands":lambda r:yn(r["bands"])}
def audit(rs,fn):
    groups=defaultdict(lambda:[0,0])
    for r in rs:
        v=fn(r)
        if r["root"]!="?" and v is not None: groups[r["root"]][int(v)]+=1
    mixed=[a for a in groups.values() if all(a)]
    counts=[sum(a[i] for a in mixed) for i in range(2)]
    assignments=math.prod(math.comb(sum(a),a[1]) for a in mixed)
    return {"groups":dict(groups),"mixed_roots":len(mixed),"mixed_class_counts":counts,"assignments":assignments,"pass":len(mixed)>=2 and min(counts)>=4 and assignments>=100}
assert math.comb(4,2)==6 and math.comb(3,0)==1
new=[r for r in rows if r["id"].startswith("C")]
enclosed=[r for r in rows if r["attachment"]=="I"]
result={k:{f:audit(rs,fn) for f,fn in features.items()} for k,rs in {"all":rows,"new":new,"enclosed":enclosed,"new_enclosed":[r for r in new if r["attachment"]=="I"]}.items()}
expected=json.loads(p.with_name("2026-11-25_EXP-0038c_results.json").read_text())["results"]
assert result==expected
print(json.dumps(result,indent=2,sort_keys=True))

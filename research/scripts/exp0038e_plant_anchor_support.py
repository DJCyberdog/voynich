import json, math
from pathlib import Path
from collections import defaultdict
p=Path(__file__).resolve().parents[1]/"results"
def load(n): return json.loads((p/n).read_text())
rows=load("2026-11-25_EXP-0038e_inventory.json")["rows"]
u=[r for r in rows if r["attachment"]=="U"]
assert len(rows)==101 and len(u)==74
assert len({r["id"] for r in rows})==len(rows)
assert len({(r["page"],tuple(r["text_center"])) for r in u})==len(u)
assert math.comb(4,2)==6 and math.comb(3,0)==1
features={"root_only":("morphology","R"),"swelling":("swelling","Y"),"branching":("branching","Y")}
def audit(rs,f,key):
    field,positive=f
    groups=defaultdict(lambda:[0,0])
    for r in rs:
        if r[field]!="?": groups[str(r[key])][int(r[field]==positive)]+=1
    m=[a for a in groups.values() if all(a)]
    counts=[sum(a[i] for a in m) for i in (0,1)]
    permutations=math.prod(math.comb(sum(a),a[1]) for a in m)
    return {"groups":dict(groups),"mixed_strata":len(m),"mixed_class_counts":counts,"assignments":str(permutations),"pass":len(m)>=2 and min(counts)>=4 and permutations>=100}
out={k:{f:{key:audit(rs,feature,key) for key in ("root","page")} for f,feature in features.items()} for k,rs in {"all":rows,"unique":u}.items()}
assert out==load("2026-11-25_EXP-0038e_results.json")["results"]
print(json.dumps(out,sort_keys=True,indent=2))

import json, math
from collections import defaultdict
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"results"
def load(n): return json.loads((p/n).read_text())
parent=load("2026-11-25_EXP-0038c_inventory.json")
delta=load("2026-11-25_EXP-0038d_attachment_delta.json")
rows=parent["rows"]+delta["new_objects"]
def audit(rs):
    groups=defaultdict(lambda:[0,0])
    for r in rs:
        if r["root"]!="?" and r["discrete_feet"] in ("Y","N"):
            groups[r["root"]][int(r["discrete_feet"]=="Y")]+=1
    m=[a for a in groups.values() if all(a)]
    counts=[sum(a[i] for a in m) for i in (0,1)]
    assignments=math.prod(math.comb(sum(a),a[1]) for a in m)
    return {"groups":dict(groups),"mixed_roots":len(m),"mixed_class_counts":counts,"assignments":assignments,"pass":len(m)>=2 and min(counts)>=4 and assignments>=100}
strict=[r for r in rows if r["attachment"]=="I"]
assert math.comb(4,2)==6 and math.comb(3,0)==1
assert len(rows)==45 and len(strict)==10 and len(delta["nearby_review"])==20
assert all(r["status"]=="ambiguous" for r in delta["nearby_review"])
out={"all":audit(rows),"strict":audit(strict),"expanded":audit(strict),"exclude_uncertain_white_marks":audit([r for r in strict if r["id"] not in ("V05","V06")]),"relaxed_all_nearby_diagnostic_only":audit([r for r in rows if r["attachment"] in ("A","I")]),"strict_exclude_f102":audit([r for r in strict if r["root"]!="f102"])}
assert out==load("2026-11-25_EXP-0038d_results.json")["results"]
print(json.dumps(out,sort_keys=True,indent=2))

import re, hashlib, json, sys
from pathlib import Path
PIN=['8438ba1c45f47fe1d06b5262cbcdf60ce69158a0edbd4dd802612896f3217e2a','0c0d1eea4b5ab87f8a65fb7f4346864cd90758ad993812b4f2122b3899d4ac88']
def parse(file,sha):
 raw=Path(file).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha
 d={}
 for l in raw.decode('ascii').splitlines():
  m=re.match(r'^<(f(?:99|100|101|102)[rv]\d?)\.(\d+),([^>]*)>\s*(.*)$',l)
  if not m:continue
  loc=m[1]+'.'+m[2];assert loc not in d
  s=re.sub(r'<![^>]*>','',m[4]).strip();d[loc]=(m[1],m[3][-2:],s)
 return d
z,g=[parse(f,h) for f,h in zip(sys.argv[1:3],PIN)]
assert z.keys()==g.keys();assert all(z[k][:2]==g[k][:2] for k in z)
sets={176:['f99r'],177:['f99v'],178:['f100r'],180:['f101v'],182:['f102v1','f102v2'],183:['f102v1','f102v2']}
result={}
for page,fols in sets.items():
 labels=[k for k,(f,t,s) in z.items() if f in fols and t=='Lf'];lc=[k for k,(f,t,s) in z.items() if f in fols and t=='Lc'];strict=[k for k in labels if all(re.fullmatch(r'(?:[A-Z][0-9a-z]){2,}',d[k][2]) for d in (z,g))];agree=[k for k in strict if z[k][2]==g[k][2]]
 result[page]={'folio_candidates':fols,'Lf':len(labels),'Lc':len(lc),'dual_strict':len(strict),'dual_exact_agreement':len(agree),'candidate_loci':labels}
print(json.dumps(result,indent=2));print('all unique candidate Lf',len(set(k for a in result.values() for k in a['candidate_loci'])))

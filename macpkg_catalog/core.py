import json, re, sqlite3
from dataclasses import dataclass, field
MANAGERS={"homebrew","macports","fink"}; NAME=re.compile(r"^[A-Za-z0-9][A-Za-z0-9+@._-]*$")
@dataclass
class Package:
    manager:str; package_type:str; native_name:str; aliases:list=field(default_factory=list); historical_names:list=field(default_factory=list); description:str=""; homepage:str=""; upstream:str=""; version:str=""; revision:str=""; provides:list=field(default_factory=list); conflicts:list=field(default_factory=list); replaces:list=field(default_factory=list); renamed_by:list=field(default_factory=list); source_url:str=""; source_revision:str=""; last_seen:str=""
    @property
    def identity(self): return {"manager":self.manager,"package_type":self.package_type,"native_name":self.native_name}
def key(i): return (i["manager"],i["package_type"],i["native_name"])
def normalize_name(s): return re.sub(r"[^a-z0-9]+","-",s.lower()).strip("-")
def validate(packages,relations):
    errors=[]; ids=set()
    for p in packages:
        i=p.identity if hasattr(p,"identity") else p; k=key(i)
        if k in ids: errors.append(f"duplicate package identity: {k}")
        ids.add(k)
        if i["manager"] not in MANAGERS or not NAME.match(i["native_name"]): errors.append(f"invalid package identity: {k}")
    for r in relations:
        for side in ("source","target"):
            if key(r[side]) not in ids: errors.append(f"missing {side}: {key(r[side])}")
        if r.get("review_status")=="automatic" and (r.get("confidence",0)<0.9 or r.get("matching_method") not in {"curated","upstream-identity"} or not r.get("evidence")): errors.append("weak automatic mapping")
        if {r['source']['native_name'],r['target']['native_name']} == {'macs-fan-control','qmail-spamcontrol'} and r.get('review_status')=='automatic' and r.get('type')!='no-equivalent': errors.append('known negative match')
    return errors
def write_sqlite(packages,relations,path):
    from pathlib import Path
    if Path(path).exists(): raise FileExistsError(f'Refusing to overwrite {path}')
    c=sqlite3.connect(path); c.executescript("CREATE TABLE IF NOT EXISTS packages(manager,type,native_name,json,PRIMARY KEY(manager,type,native_name)); CREATE TABLE IF NOT EXISTS relations(source_manager,source_type,source_name,target_manager,target_type,target_name,confidence,review_status,json);")
    for p in packages: c.execute("INSERT OR REPLACE INTO packages VALUES(?,?,?,?)",(p["manager"],p["package_type"],p["native_name"],json.dumps(p,sort_keys=True)))
    for r in relations:
        c.execute('INSERT INTO relations VALUES(?,?,?,?,?,?,?,?,?)', (*key(r['source']),*key(r['target']),r['confidence'],r['review_status'],json.dumps(r,sort_keys=True)))
    c.commit(); c.close()

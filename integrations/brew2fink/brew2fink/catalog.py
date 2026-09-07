import json
import urllib.request
from pathlib import Path

DEFAULT_URL="https://tomck.github.io/macpkg-catalog/relations.json"
DEFAULT_CACHE="~/.cache/brew2fink/macpkg-catalog-relations.json"

def load(path):
    data=json.loads(Path(path).expanduser().read_text())
    rows=data.get("relations",[]) if isinstance(data,dict) else data
    table={}
    for row in rows:
        source=row.get("source",{}); target=row.get("target",{})
        if source.get("manager")!="homebrew" or target.get("manager")!="fink": continue
        kind="formula" if source.get("package_type")=="formula" else "cask"
        name=source.get("native_name")
        if not name: continue
        table.setdefault((kind,name),[]).append({"package":target.get("native_name"),"confidence":row.get("confidence",0),"reason":row.get("matching_method","catalog"),"status":row.get("review_status","needs-review")})
    for choices in table.values(): choices.sort(key=lambda x:x["confidence"],reverse=True)
    return table

def fetch(cache=DEFAULT_CACHE,refresh=False,url=DEFAULT_URL,progress=None):
    path=Path(cache).expanduser()
    if path.exists() and not refresh: return load(path)
    if progress: progress("Downloading the published macpkg-catalog relationships...")
    request=urllib.request.Request(url,headers={"User-Agent":"brew2fink"})
    with urllib.request.urlopen(request,timeout=120) as response: data=response.read()
    path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
    return load(path)

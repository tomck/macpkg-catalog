"""Consumer for the published macpkg-catalog relationship artifact."""
import json
import urllib.request
from pathlib import Path

DEFAULT_CATALOG_URL = "https://tomck.github.io/macpkg-catalog/relations.json"
DEFAULT_CATALOG_CACHE = "~/.cache/brew2port/macpkg-catalog-relations.json"

def _fetch(url):
    request=urllib.request.Request(url,headers={"User-Agent":"brew2port"})
    with urllib.request.urlopen(request,timeout=120) as response:
        return json.loads(response.read().decode())

def load_catalog(path):
    data=json.loads(Path(path).expanduser().read_text())
    rows=data.get("relations",[]) if isinstance(data,dict) else data
    table={}
    for relation in rows:
        source=relation.get("source",{}); target=relation.get("target",{})
        if source.get("manager") != "homebrew" or target.get("manager") != "macports": continue
        kind="formula" if source.get("package_type") == "formula" else "cask"
        key=(kind,source.get("native_name"))
        if not key[1]: continue
        candidate={"port":target.get("native_name"),"confidence":relation.get("confidence",0),"reason":relation.get("matching_method","catalog"),"catalog_status":relation.get("review_status","needs-review")}
        table.setdefault(key,{"candidates":[],"catalog_status":relation.get("review_status","needs-review")})["candidates"].append(candidate)
    for value in table.values():
        value["candidates"].sort(key=lambda item:item.get("confidence",0),reverse=True)
    return table

def fetch_catalog(cache=DEFAULT_CATALOG_CACHE, refresh=False, url=DEFAULT_CATALOG_URL, progress=None):
    path=Path(cache).expanduser()
    if path.exists() and not refresh:
        if progress: progress(f"Using cached macpkg-catalog relationships: {path}")
        return load_catalog(path)
    if progress: progress("Downloading the published macpkg-catalog relationships...")
    try: data=_fetch(url)
    except Exception as exc:
        if progress: progress(f"Published catalog unavailable ({exc}); continuing without it.")
        return {}
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(data,indent=2)+"\n")
    if progress: progress(f"Cached macpkg-catalog relationships at {path}")
    return load_catalog(path)

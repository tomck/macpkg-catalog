import json, urllib.request
import hashlib
from dataclasses import asdict
from datetime import datetime, timezone
from .core import Package
SOURCES={'formula':'https://formulae.brew.sh/api/formula.json','cask':'https://formulae.brew.sh/api/cask.json'}
ANALYTICS='https://formulae.brew.sh/api/analytics/{category}/{scope}/{period}.json'

def _get(url):
    request=urllib.request.Request(url,headers={"User-Agent":"macpkgmap/0.1"})
    with urllib.request.urlopen(request,timeout=60) as r: return json.load(r)

def fetch_analytics(category, period="365d", package_type="formula"):
    scope="homebrew-core" if package_type=="formula" else "homebrew-cask"
    data=_get(ANALYTICS.format(category=category,scope=scope,period=period))
    rows=[]
    items=data.get("items") or []
    if items:
        rows=[(x.get("formula") or x.get("cask"),x) for x in items]
    else:
        for name, values in (data.get("formulae") or {}).items():
            rows.extend((item.get("formula") or item.get("cask") or name,item) for item in values)
    return {name:{"count":int(str(item.get("count",0)).replace(",","")),"rank":item.get("number"),"percent":float(str(item["percent"]).replace("%","")) if item.get("percent") is not None else None} for name,item in rows if name}
def fetch(kind):
    with urllib.request.urlopen(SOURCES[kind],timeout=60) as r: data=json.load(r)
    out=[]
    for x in data:
        out.append({'manager':'homebrew','package_type':kind,'native_name':x.get('name',''),'aliases':x.get('aliases',[]),'description':x.get('desc',''),'homepage':x.get('homepage',''),'upstream':x.get('head',{}).get('url','') if isinstance(x.get('head'),dict) else '','version':(x.get('versions') or {}).get('stable',''),'revision':'','provides':[],'conflicts':[],'replaces':[],'renamed_by':[],'source_url':SOURCES[kind],'source_revision':'','last_seen':''})
    return out

def normalize_homebrew(rows, kind, revision, seen):
    """Cask token is the native identity; display names are not aliases."""
    records=[]
    for row in rows:
        name=row["token"] if kind=="cask" else row["name"]
        urls=row.get("urls") or {}
        upstream=(urls.get("head") or urls.get("stable") or {}).get("url","") if kind=="formula" else row.get("url","")
        package=Package("homebrew",kind,name,
            aliases=row.get("aliases",[]),
            historical_names=row.get("old_tokens",[]) if kind=="cask" else row.get("oldnames",[]),
            description=row.get("desc") or "",homepage=row.get("homepage") or "",
            upstream=upstream,version=str(row.get("version","")) if kind=="cask" else str((row.get("versions") or {}).get("stable") or ""),
            revision=str(row.get("revision",0)),source_url=SOURCES[kind],
            source_revision=revision,last_seen=seen)
        records.append(asdict(package))
    return records

def normalize_macports(rows, revision, seen):
    records=[]
    for row in rows:
        records.append(asdict(Package("macports","port",row["name"],
            description=row.get("description") or "",homepage=row.get("homepage") or "",
            version=str(row.get("version") or ""),revision=str(row.get("revision") or ""),
            renamed_by=[row["replaced_by"]] if row.get("replaced_by") else [],
            source_url="https://ports.macports.org/api/v1/ports/",
            source_revision=revision,last_seen=seen)))
    return records

def parse_fink_index(text, source_url, revision, seen):
    """Parse Debian-control style Fink Packages metadata without executing recipes."""
    records=[]
    for paragraph in text.strip().split("\n\n"):
        fields={}
        current=None
        for line in paragraph.splitlines():
            if line.startswith((" ","\t")) and current:
                fields[current]+="\n"+line.strip()
            elif ":" in line:
                current,value=line.split(":",1)
                fields[current]=value.strip()
        if "Package" not in fields:
            continue
        version=fields.get("Version","")
        upstream_version,sep,revision_number=version.rpartition("-")
        def names(field):
            import re
            return [part.strip().split()[0] for part in re.split("[,|]",fields.get(field,"")) if part.strip()]
        records.append(asdict(Package("fink","package",fields["Package"],
            description=fields.get("Description",""),homepage=fields.get("Homepage",""),
            upstream=fields.get("Source",""),version=upstream_version if sep else version,
            revision=revision_number if sep else "",provides=names("Provides"),
            conflicts=names("Conflicts"),replaces=names("Replaces"),
            source_url=source_url,source_revision=revision,last_seen=seen)))
    return records

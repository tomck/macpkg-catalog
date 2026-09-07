import json, urllib.request
import hashlib
import time
import os
import gzip, io, tarfile
from dataclasses import asdict
from datetime import datetime, timezone
from .core import Package, NAME
SOURCES={'formula':'https://formulae.brew.sh/api/formula.json','cask':'https://formulae.brew.sh/api/cask.json'}
ANALYTICS='https://formulae.brew.sh/api/analytics/{category}/{scope}/{period}.json'
FINK_SNAPSHOT='https://github.com/fink/fink-distributions/archive/refs/heads/master.tar.gz'
MACPORTS_PORTINDEX='https://ftp.fau.de/macports/release/tarballs/PortIndex_darwin_25_i386/PortIndex'

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

def fetch_macports(page_size=50, progress=None):
    """Fetch every active MacPorts API record with count validation."""
    url="https://ports.macports.org/api/v1/ports/?page=1"
    rows=[]; expected=None
    while url:
        data=_get(url)
        if expected is None: expected=data.get("count")
        rows.extend(data.get("results",[]))
        if progress: progress(len(rows),expected)
        url=data.get("next")
        time.sleep(0.01)
    if expected is None or len(rows) < expected:
        raise RuntimeError(f"MacPorts fetch incomplete: received {len(rows)}, expected {expected}")
    return normalize_macports(rows,"macports-api",datetime.now(timezone.utc).isoformat())

def parse_portindex(text, source_url, revision, seen):
    """Parse MacPorts' local pre-generated PortIndex without contacting its API."""
    records=[]
    lines=text.splitlines(); index=0
    while index < len(lines):
        line=lines[index]; index+=1
        line=line.strip()
        if not line or line.startswith("#"): continue
        parts=line.split(None,2)
        if len(parts)==2 and index < len(lines):
            line += " " + lines[index].strip(); index+=1
        fields={}; pos=0; parts=line.split(None,2)
        if len(parts)<3: continue
        fields["name"]=parts[0]
        pos=len(parts[0])+len(parts[1])+2
        body=line[pos:]
        i=0
        while i<len(body):
            while i<len(body) and body[i].isspace(): i+=1
            start=i
            while i<len(body) and not body[i].isspace(): i+=1
            field=body[start:i]
            while i<len(body) and body[i].isspace(): i+=1
            if i>=len(body): break
            if body[i]=='{':
                depth=1; i+=1; start=i
                while i<len(body) and depth:
                    if body[i]=='{': depth+=1
                    elif body[i]=='}': depth-=1
                    i+=1
                value=body[start:i-1]
            else:
                start=i
                while i<len(body) and not body[i].isspace(): i+=1
                value=body[start:i]
            if field != "name":
                fields[field]=value
        if fields.get("name"):
            records.append(asdict(Package("macports","port",fields["name"],description=fields.get("description","") or fields.get("long_description","") ,homepage=fields.get("homepage",""),version=fields.get("version",""),revision=fields.get("revision",""),renamed_by=[fields["replaced_by"]] if fields.get("replaced_by") else [],source_url=source_url,source_revision=revision,last_seen=seen)))
    return records

def fetch_macports_local():
    candidates=("/opt/local/var/macports/sources/rsync.macports.org/macports/release/tarballs/ports/PortIndex","/opt/local/var/macports/sources/rsync.macports.org/macports/release/tarballs/remote/PortIndex")
    for filename in candidates:
        if os.path.isfile(filename):
            stat=os.stat(filename)
            with open(filename,encoding="utf-8",errors="replace") as stream: text=stream.read()
            return parse_portindex(text,filename,str(stat.st_mtime_ns),datetime.now(timezone.utc).isoformat())
    return None

def fetch_macports_portindex():
    request=urllib.request.Request(MACPORTS_PORTINDEX,headers={"User-Agent":"macpkgmap/0.1"})
    with urllib.request.urlopen(request,timeout=180) as response: payload=response.read()
    return parse_portindex(payload.decode("utf-8","replace"),MACPORTS_PORTINDEX,hashlib.sha256(payload).hexdigest(),datetime.now(timezone.utc).isoformat())

def fetch_live_snapshot():
    """Build a normalized Homebrew + MacPorts snapshot and analytics records."""
    seen=datetime.now(timezone.utc).isoformat()
    packages=[]
    for kind in ("formula","cask"):
        rows=_get(SOURCES[kind])
        packages.extend(normalize_homebrew(rows,kind,"homebrew-api",seen))
    local_ports=fetch_macports_local()
    if local_ports is None:
        local_ports=fetch_macports_portindex()
    packages.extend(local_ports)
    packages.extend(fetch_fink_snapshot())
    # Fink's source tree contains multiple release/architecture descriptions;
    # keep one deterministic record per published identity and discard
    # unresolved type-template names that are not installable package names.
    unique={}
    for package in packages:
        name=package["native_name"]
        if not NAME.match(name):
            continue
        unique[(package["manager"],package["package_type"],name)]=package
    packages=list(unique.values())
    popularity=[]
    for kind in ("formula","cask"):
        for period in ("30d","90d","365d"):
            installs=fetch_analytics("install" if kind=="formula" else "cask-install",period,kind)
            requested=fetch_analytics("install-on-request",period,kind) if kind=="formula" else {}
            for name,value in installs.items():
                popularity.append({"manager":"homebrew","package_type":kind,"native_name":name,"period":period,"install_count":value["count"],"install_on_request_count":requested.get(name,{}).get("count",0),"rank":value["rank"],"percent":value["percent"],"source_url":ANALYTICS,"intel_status":"unknown","last_seen":seen})
    return {"schema_version":1,"catalog_version":"source-snapshot","generated_at":seen,"sources":{"homebrew":"homebrew-api","macports":"macports-portindex","fink":FINK_SNAPSHOT},"packages":packages,"relations":[],"popularity":popularity}
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

def parse_fink_info(text, source_url, revision, seen):
    """Parse one Fink .info description, including relationship metadata."""
    fields={}; current=None
    for line in text.splitlines():
        if line.startswith((" ","\t")) and current:
            fields[current]+="\n"+line.strip()
        elif ":" in line:
            current,value=line.split(":",1); fields[current]=value.strip()
    if not fields.get("Package") or not NAME.match(fields["Package"]): return None
    def names(field):
        import re
        return [part.strip().split()[0] for part in re.split(r"[,|]",fields.get(field,"")) if part.strip()]
    return asdict(Package("fink","package",fields["Package"],description=fields.get("Description","") or fields.get("DescDetail",""),homepage=fields.get("Homepage",""),upstream=fields.get("Source","").split()[0] if fields.get("Source") else "",version=fields.get("Version",""),revision=fields.get("Revision",""),provides=names("Provides"),conflicts=names("Conflicts"),replaces=names("Replaces"),source_url=source_url,source_revision=revision,last_seen=seen))

def fetch_fink_local():
    candidates=("/opt/sw/fink/dists/stable/main/binary-darwin-i386/Packages.gz","/opt/sw/fink/dists/stable/main/binary-darwin-arm64/Packages.gz","/opt/sw/fink/dists/stable/main/binary-darwin-i386/Packages","/opt/sw/fink/dists/stable/main/binary-darwin-arm64/Packages")
    for filename in candidates:
        if os.path.isfile(filename):
            raw=open(filename,"rb").read()
            text=gzip.decompress(raw).decode("utf-8","replace") if filename.endswith(".gz") else raw.decode("utf-8","replace")
            return parse_fink_index(text,filename,str(os.stat(filename).st_mtime_ns),datetime.now(timezone.utc).isoformat())
    return None

def fetch_fink_snapshot():
    local=fetch_fink_local()
    if local is not None: return local
    request=urllib.request.Request(FINK_SNAPSHOT,headers={"User-Agent":"macpkgmap/0.1"})
    with urllib.request.urlopen(request,timeout=180) as response: payload=response.read()
    revision=hashlib.sha256(payload).hexdigest(); records=[]; seen=datetime.now(timezone.utc).isoformat()
    with tarfile.open(fileobj=io.BytesIO(payload),mode="r:gz") as archive:
        for member in archive.getmembers():
            if member.isfile() and member.name.endswith(".info"):
                record=parse_fink_info(archive.extractfile(member).read().decode("utf-8","replace"),FINK_SNAPSHOT,revision,seen)
                if record is not None: records.append(record)
    if not records: raise RuntimeError("Fink snapshot contained no parseable package descriptions")
    return records

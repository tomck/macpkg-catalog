"""Conservative indexed matching; string matches remain review suggestions."""
from collections import defaultdict
from urllib.parse import urlsplit
from .core import key, normalize_name

def identity(package):
    return dict(zip(("manager","package_type","native_name"),key(package)))

def upstream_identity(url):
    parsed=urlsplit(url)
    host=(parsed.hostname or "").lower().removeprefix("www.")
    path=parsed.path.rstrip("/").removesuffix(".git")
    if not host or not path:
        return None
    if host in {"github.com","gitlab.com","bitbucket.org"} and len(path.strip("/").split("/"))!=2:
        return None
    return host+path

def match(packages, versions, curated=()):
    result=[]
    blocked=set()
    for entry in curated:
        relation=dict(entry,matching_method="curated",source_catalog_versions=versions)
        result.append(relation)
        pair=key(entry["source"]),key(entry["target"])
        blocked.update((pair,pair[::-1]))
    names,normalized,aliases,upstreams=[defaultdict(list) for _ in range(4)]
    for package in packages:
        names[package["native_name"]].append(package)
        normalized[normalize_name(package["native_name"])].append(package)
        for alias in package.get("aliases",[])+package.get("historical_names",[]):
            aliases[alias].append(package)
        for url in {package.get("homepage",""),package.get("upstream","")}:
            token=upstream_identity(url)
            if token:
                upstreams[token].append(package)
    for package in packages:
        candidates={}
        tiers=[("exact-name",names,package["native_name"]),("normalized-name",normalized,normalize_name(package["native_name"])),("official-alias",aliases,package["native_name"])]
        tiers.extend(("upstream-identity",upstreams,upstream_identity(package.get(field,""))) for field in ("homepage","upstream"))
        for method,index,token in tiers:
            if not token:
                continue
            for target in index.get(token,[]):
                pair=key(package),key(target)
                if package["manager"]==target["manager"] or pair in blocked:
                    continue
                if {package["native_name"],target["native_name"]}=={"macs-fan-control","qmail-spamcontrol"}:
                    continue
                relation=candidates.setdefault(key(target),{"source":identity(package),"target":identity(target),"type":"equivalent","confidence":.65,"matching_method":method,"evidence":[],"review_status":"needs-review","source_catalog_versions":versions})
                evidence={"kind":method,"value":token}
                if evidence not in relation["evidence"]:
                    relation["evidence"].append(evidence)
                if method=="upstream-identity":
                    relation.update(confidence=.97,matching_method=method)
        strong=defaultdict(list)
        for relation in candidates.values():
            if relation["matching_method"]=="upstream-identity":
                strong[relation["target"]["manager"]].append(relation)
        for group in strong.values():
            if len(group)==1:
                group[0]["review_status"]="automatic"
        result.extend(candidates.values())
    return sorted(result,key=lambda r:(key(r["source"]),key(r["target"])))

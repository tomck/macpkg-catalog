"""Conservative indexed matching; string matches remain review suggestions."""
from collections import defaultdict
import re
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

def near_hit(source, target, evidence, source_version="", target_version=""):
    """Return a review-only version-family relationship, or None."""
    def family(name):
        value=normalize_name(name)
        value=re.sub(r"(^|-)py\d+(?=-|$)", r"\1", value)
        return re.sub(r"(?:@|-)?\d+(?:\.\d+)*$", "", value).strip("-")
    if not family(source["native_name"]) or family(source["native_name"]) != family(target["native_name"]):
        return None
    return {"source":identity(source),"target":identity(target),"type":"equivalent","confidence":0.78,
            "matching_method":"version-family","evidence":evidence,"review_status":"needs-review",
            "version_relation":"nearest-compatible-version","source_version":source_version,
            "target_version":target_version,"source_catalog_versions":{}}

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
    # Version-family matches are deliberately generated only when the name
    # carries version evidence. They remain review-only and are never used to
    # promote an otherwise unrelated fuzzy spelling match.
    families=defaultdict(list)
    for package in packages:
        family=normalize_name(package["native_name"])
        family=re.sub(r"(^|-)py\d+(?=-|$)", r"\1", family)
        family=re.sub(r"(?:@|-)?\d+(?:\.\d+)*$", "", family).strip("-")
        if family and re.search(r"(?:@|-|py)\d", normalize_name(package["native_name"])):
            families[(package["manager"],family)].append(package)
    seen={(key(r["source"]),key(r["target"])) for r in result}
    for package in packages:
        family=normalize_name(package["native_name"])
        family=re.sub(r"(^|-)py\d+(?=-|$)", r"\1", family)
        family=re.sub(r"(?:@|-)?\d+(?:\.\d+)*$", "", family).strip("-")
        if not family: continue
        for (manager,target_family), targets in families.items():
            if manager==package["manager"] or target_family!=family: continue
            for target in targets:
                relation=near_hit(identity(package),identity(target),[{"kind":"version-family","value":family}],package.get("version",""),target.get("version",""))
                pair=(key(relation["source"]),key(relation["target"])) if relation else None
                if relation and pair not in seen:
                    relation["source_catalog_versions"]=versions
                    result.append(relation); seen.add(pair)
    return sorted(result,key=lambda r:(key(r["source"]),key(r["target"])))

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

def version_family(name):
    """Return a conservative family key for explicitly versioned names."""
    value=normalize_name(name)
    if re.fullmatch(r"python-\d+(?:-\d+)?",value) or re.fullmatch(r"python\d{2,3}",value):
        return "python"
    if re.search(r"(?:@|-|py)\d", value):
        family=re.sub(r"(^|-)py\d+(?=-|$)", r"\1", value)
        family=re.sub(r"(?:@|-)?\d+(?:\.\d+)*$", "", family).strip("-")
        return family or None
    return None

def version_signature(name):
    """Return a version tuple where the manager naming is unambiguous."""
    value=normalize_name(name)
    match=re.fullmatch(r"python-(\d+)(?:-(\d+))?",value)
    if match:
        return (int(match.group(1)),int(match.group(2) or 0))
    match=re.fullmatch(r"python(\d{2,3})",value)
    if match:
        digits=match.group(1)
        return (int(digits[0]),int(digits[1:]))
    return None

def description_mentions_version(package, signature):
    if not signature:
        return False
    major,minor=signature
    description=(package.get("description") or "").lower()
    return (f"{major}.{minor}" in description or
            re.search(r"\b%d\s*%02d\b" % (major,minor), description) is not None)

def near_hit(source, target, evidence, source_version="", target_version=""):
    """Return a review-only version-family relationship, or None."""
    if not version_family(source["native_name"]) or version_family(source["native_name"]) != version_family(target["native_name"]):
        return None
    confidence=0.78
    source_version_signature=version_signature(source["native_name"])
    target_version_signature=version_signature(target["native_name"])
    if source_version_signature and source_version_signature == target_version_signature:
        confidence=0.94
    return {"source":identity(source),"target":identity(target),"type":"equivalent","confidence":confidence,
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
        family=version_family(package["native_name"])
        if family:
            families[(package["manager"],family)].append(package)
    seen={(key(r["source"]),key(r["target"])) for r in result}
    for package in packages:
        family=version_family(package["native_name"])
        if not family: continue
        for manager in ("homebrew", "macports", "fink"):
            if manager == package["manager"]: continue
            for target in families.get((manager, family), []):
                source_signature=version_signature(package["native_name"])
                target_signature=version_signature(target["native_name"])
                if family == "python" and source_signature != target_signature:
                    continue
                evidence=[{"kind":"version-family","value":family}]
                if source_signature and source_signature == target_signature:
                    evidence.append({"kind":"version-semantic","value":"%d.%d" % source_signature})
                relation=near_hit(identity(package),identity(target),evidence,package.get("version",""),target.get("version",""))
                if (relation and source_signature and
                    description_mentions_version(package,source_signature) and
                    description_mentions_version(target,target_signature)):
                    relation["confidence"]=0.97
                    relation["evidence"].append({"kind":"description-version","value":"%d.%d" % source_signature})
                pair=(key(relation["source"]),key(relation["target"])) if relation else None
                if relation and pair not in seen:
                    relation["source_catalog_versions"]=versions
                    result.append(relation); seen.add(pair)
    return sorted(result,key=lambda r:(key(r["source"]),key(r["target"])))

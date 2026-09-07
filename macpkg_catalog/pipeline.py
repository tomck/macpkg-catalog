"""Offline artifact generation from normalized, provenance-bearing snapshots."""
import hashlib
import json
from pathlib import Path
from .core import validate, write_sqlite, key

def generate(snapshot, output):
    data = json.loads(Path(snapshot).read_text())
    packages = data["packages"]
    data.setdefault("popularity", [])
    data.setdefault("analytics_policy", "install-on-request is the primary demand signal; Intel package-level data is unknown unless explicitly reported")
    from .mapping import match
    relations = data.get("relations")
    if relations is None:
        relations = match(packages,data.get("sources",{}))
        data["relations"] = relations
    errors = validate(packages, relations)
    if errors:
        raise ValueError("\n".join(errors))
    root = Path(output)
    if root.exists() and any(root.iterdir()):
        raise ValueError("Output directory must be empty")
    root.mkdir(parents=True, exist_ok=True)
    data.pop("catalog_version", None)
    data["schema_version"] = 1
    data["catalog_version"] = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    def put(name, value):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    put("catalog.json", data)
    put("packages.json", packages)
    put("relations.json", relations)
    put("popularity.json", data["popularity"])
    write_sqlite(packages, relations, root / "catalog.sqlite")
    import sqlite3
    with sqlite3.connect(root / "catalog.sqlite") as connection:
        connection.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT)")
        connection.executemany("INSERT INTO metadata VALUES(?,?)", [(k,json.dumps(v)) for k,v in data.items() if k not in {"packages","relations"}])
    grouped = {}
    for relation in relations:
        grouped.setdefault(key(relation["source"]), []).append(relation)
    for package in packages:
        suffix = "/".join(key(package)) + ".json"
        envelope = {"catalog_version":data["catalog_version"],"package":package}
        put("v1/package/" + suffix, envelope)
        put("v1/lookup/" + suffix, envelope)
        put("v1/relations/" + suffix, {"catalog_version":data["catalog_version"],"relations":grouped.get(key(package),[])})
    automatic = sum(r.get("review_status") == "automatic" for r in relations)
    near = sum(r.get("review_status") == "needs-review" and r.get("matching_method") == "version-family" for r in relations)
    (root / "mapping-report.md").write_text(f"# Mapping report\n\nVersion: {data['catalog_version']}\n\nPackages: {len(packages)}\n\nRelationships: {len(relations)}\n\nAutomatic: {automatic}\n\nNear-hits: {near}\n\nPopularity is contextual evidence only; it never establishes equivalence.\n")
    (root / "checksums.txt").write_text("\n".join(hashlib.sha256(p.read_bytes()).hexdigest()+"  "+p.relative_to(root).as_posix() for p in sorted(root.rglob("*")) if p.is_file() and p.name != "checksums.txt")+"\n")
    return data

def load_snapshot(path):
    path = Path(path).resolve()
    if path.suffix != ".sqlite":
        return json.loads(path.read_text())
    import sqlite3
    with sqlite3.connect(path.as_uri()+"?mode=ro", uri=True) as connection:
        data = {k:json.loads(v) for k,v in connection.execute("SELECT key,value FROM metadata")}
        for table in ("packages","relations"):
            data[table] = [json.loads(r[0]) for r in connection.execute("SELECT json FROM "+table)]
        return data

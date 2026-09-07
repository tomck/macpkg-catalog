"""Load the small, human-maintained YAML curation layer."""
from pathlib import Path
import yaml

def _read(path, key, default):
    if not path.exists():
        return default
    value=yaml.safe_load(path.read_text())
    if value is None:
        return default
    return value.get(key, default)

def load_curated(directory):
    root=Path(directory)
    relations=list(_read(root/"relations.yaml", "relations", []))
    for entry in _read(root/"no-equivalent.yaml", "no_equivalent", []):
        relations.append({
            "source":entry["source"], "target":entry["target"],
            "type":"no-equivalent", "confidence":1.0,
            "evidence":[{"kind":"curated-negative", "value":entry.get("reason", "explicitly curated") }],
            "review_status":"automatic",
        })
    aliases=_read(root/"aliases.yaml", "aliases", [])
    sources=_read(root/"sources.yaml", "sources", {})
    return relations, aliases, sources

def apply_aliases(packages, aliases):
    """Merge curated aliases without replacing source-provided metadata."""
    by_identity={(p["manager"],p["package_type"],p["native_name"]):p for p in packages}
    for entry in aliases:
        identity=entry.get("package", entry)
        package=by_identity.get((identity.get("manager"), identity.get("package_type"), identity.get("native_name")))
        if package is None:
            continue
        for field in ("aliases", "historical_names"):
            for value in entry.get(field, []):
                if value not in package[field]:
                    package[field].append(value)
    return packages

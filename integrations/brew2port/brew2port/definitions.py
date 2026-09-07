"""Published Homebrew-to-MacPorts definitions database support."""

import datetime
import json
import urllib.request
from pathlib import Path

from .core import make_plan


DEFAULT_DEFINITIONS_URL = (
    "https://raw.githubusercontent.com/tomck/brew2port/main/definitions/mappings.json"
)
DEFAULT_DEFINITIONS_CACHE = "~/.cache/brew2port/definitions.json"
HOMEBREW_FORMULAE_URL = "https://formulae.brew.sh/api/formula.json"
HOMEBREW_CASKS_URL = "https://formulae.brew.sh/api/cask.json"


def fetch_json(url, opener=urllib.request.urlopen, message=None):
    if message:
        print(message)
    request = urllib.request.Request(url, headers={"User-Agent": "brew2port"})
    with opener(request) as response:
        return json.loads(response.read().decode())


def load_definitions(path):
    """Load a definitions document and return its keyed mapping table."""
    data = json.loads(Path(path).expanduser().read_text())
    if isinstance(data, list):
        rows = data
    else:
        rows = data.get("mappings", [])
    table = {}
    for row in rows:
        if not isinstance(row, dict) or not row.get("homebrew"):
            continue
        key = (row.get("kind", "formula"), row["homebrew"])
        table[key] = row
        for alias in row.get("aliases", []):
            table[(row.get("kind", "formula"), alias)] = row
    return table


def fetch_definitions(cache_path=DEFAULT_DEFINITIONS_CACHE, refresh=False,
                      url=DEFAULT_DEFINITIONS_URL, opener=urllib.request.urlopen,
                      progress=None):
    path = Path(cache_path).expanduser()
    if path.exists() and not refresh:
        if progress:
            progress(f"Using cached definitions database: {path}")
        return load_definitions(path)
    if progress:
        progress("Downloading the published definitions database...")
    try:
        data = fetch_json(url, opener)
    except Exception as exc:
        if progress:
            progress(f"Definitions database unavailable ({exc}); continuing without it.")
        return {}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    if progress:
        progress(f"Cached definitions database at {path}")
    return load_definitions(path)


def _catalog_items(formulae, casks):
    items = []
    for formula in formulae:
        name = formula.get("name") or formula.get("full_name")
        if name:
            items.append({"kind": "formula", "name": name,
                          "aliases": formula.get("aliases", [])})
    for cask in casks:
        name = cask.get("token") or cask.get("name")
        if name:
            items.append({"kind": "cask", "name": name,
                          "aliases": cask.get("aliases", [])})
    return items


def build_definitions(formulae, casks, ports, overrides=None):
    """Build a compact table containing trusted mappings from source catalogs."""
    overrides = overrides or {}
    items = _catalog_items(formulae, casks)
    plans = make_plan(items, ports, overrides=overrides)
    mappings = []
    for item, plan in zip(items, plans):
        choices = plan.get("candidates", [])
        chosen = choices[0] if choices else None
        separated = bool(
            chosen
            and chosen.get("confidence", 0) >= 0.8
            and (len(choices) == 1 or
                 chosen.get("confidence", 0) - choices[1].get("confidence", 0) >= 0.08)
        )
        override = overrides.get(item["name"])
        curated_no_match = item["name"] in overrides and override is None
        if not separated and not curated_no_match:
            continue
        aliases = [alias for alias in item.get("aliases", []) if alias and alias != item["name"]]
        if curated_no_match:
            mappings.append({
                "kind": item["kind"], "homebrew": item["name"], "aliases": aliases,
                "status": "no-match", "candidates": [], "confidence": 1.0,
                "reason": "curated override",
            })
        else:
            mappings.append({
                "kind": item["kind"], "homebrew": item["name"], "aliases": aliases,
                "status": "matched", "candidates": choices,
                "confidence": chosen["confidence"], "reason": chosen["reason"],
            })
    return {
        "schema_version": 1,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sources": {
            "homebrew_formulae": HOMEBREW_FORMULAE_URL,
            "homebrew_casks": HOMEBREW_CASKS_URL,
            "macports": "https://ports.macports.org/api/v1/ports/",
        },
        "mapping_count": len(mappings),
        "mappings": mappings,
    }


def build_definitions_from_urls(formulae_url=HOMEBREW_FORMULAE_URL,
                                casks_url=HOMEBREW_CASKS_URL,
                                ports_url="https://ports.macports.org/api/v1/ports/",
                                ports_cache=None, refresh_ports=False,
                                overrides=None, opener=urllib.request.urlopen,
                                progress=None):
    from .core import cached_macports_ports

    formulae = fetch_json(formulae_url, opener)
    casks = fetch_json(casks_url, opener)
    ports = cached_macports_ports(
        ports_cache or "~/.cache/brew2port/macports-ports.json",
        refresh=refresh_ports, url=ports_url, progress=progress,
    )
    return build_definitions(formulae, casks, ports, overrides)

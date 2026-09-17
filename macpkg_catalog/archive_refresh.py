"""Weekly binary-availability orchestration: seed once, diffs thereafter.

Reads the previous published catalog for versions/binaries/generated_at,
takes the union of the PortIndex version diff and the DirectoryIndex
mtime backstop as the probe set, fetches per-port archive pages (with
checkpoints so the one-time seed survives interruption), merges over
previous state, adds Fink bindist tokens, and writes the state file that
`fetch-live --archive-state` consumes.

Tripwire: a suspiciously small probe set against a nonempty previous
state means listing-format rot — warn and probe everything that week.
"""
import argparse
import datetime
import json
import sys
import time
from pathlib import Path

from . import archives
from .core import NAME
from .sources import fetch_macports_portindex, parse_portindex

PREVIOUS_CATALOG_URL = "https://tomck.github.io/macpkg-catalog/catalog.json"


def state_key(manager, package_type, native_name):
    return f"{manager}/{package_type}/{native_name}"


def parse_state_key(key):
    manager, package_type, native_name = key.split("/", 2)
    return manager, package_type, native_name


def previous_from_catalog(catalog):
    """Split a published catalog into previous versions/binaries/generated_at."""
    versions = {}
    binaries = {}
    for package in catalog.get("packages", []):
        if package.get("manager") == "macports":
            versions[package["native_name"]] = (package.get("version", ""), package.get("revision", ""))
        tokens = package.get("binaries") or []
        if tokens:
            binaries[(package["manager"], package["package_type"], package["native_name"])] = sorted(tokens)
    return versions, binaries, catalog.get("generated_at")


def valid_names(names):
    """Keep only plausible package names, so a parser desync can never turn
    description words into thousands of doomed archive probes."""
    return {name for name in names if name and NAME.match(name)}


def changed_ports(records, previous_versions):
    """Ports added or version/revision-changed since previous versions."""
    changed = set()
    for record in records:
        name = record.get("native_name", record.get("name"))
        if not name or not NAME.match(name):
            continue
        if previous_versions.get(name) != (record.get("version", ""), record.get("revision", "")):
            changed.add(name)
    return changed


def _as_utc(value):
    """Listing stamps and ISO cutoffs compared at minute precision as UTC."""
    import datetime
    try:
        parsed = datetime.datetime.strptime(value.strip().replace("T", " ")[:16], "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    return parsed.replace(tzinfo=datetime.timezone.utc)


def backstop_ports(listing, cutoff):
    """Folders newer than the cutoff mtime (or all, when cutoff is None).

    Listing stamps ("2026-09-17 06:32") and ISO cutoffs are compared as
    datetimes, never strings. Unparseable stamps fail open (probe it).
    """
    if cutoff is None:
        return set(listing)
    cutoff_at = _as_utc(cutoff)
    selected = set()
    for name, modified in listing.items():
        stamped = _as_utc(modified)
        if stamped is None or cutoff_at is None or stamped > cutoff_at:
            selected.add(name)
    return selected


def select_probe_set(changed, backstop, had_previous):
    """Union the change sources; trip when a nonempty history yields nothing."""
    probe = set(changed) | set(backstop)
    tripped = had_previous and not probe
    return probe, tripped


def probe_ports(names, fetch=archives.fetch_archive_page, previous=None, progress=None, delay=0.05,
                checkpoint=None, checkpoint_every=500):
    """Fetch archive pages; previous maps name to token list (resume/merge).

    checkpoint, when given, is called with the running state every
    checkpoint_every probes so an interrupted seed resumes instead of
    restarting.
    """
    state = dict(previous or {})
    for count, name in enumerate(sorted(valid_names(names)), 1):
        if name in state:
            continue
        try:
            state[name] = archives.parse_archive_page(fetch(name))
        except Exception as exc:  # noqa: BLE001 - one bad port must not stop the run
            if progress:
                progress(f"Warning: archive probe for {name} failed ({exc}); skipped.")
        if delay:
            time.sleep(delay)
        if checkpoint is not None and count % checkpoint_every == 0:
            checkpoint(state)
    return state


def fetch_bindist_state(targets=archives.FINK_BINDIST_TARGETS, fetch=archives.fetch_bindist_packages,
                        progress=None):
    """{(fink, package, name): [tree/arch token]} across bindist targets.

    One dead tree (a 404ing Packages index, as 10.15 was) warns and skips
    instead of killing the whole weekly refresh.
    """
    state = {}
    for os_tree, arch in targets:
        try:
            packages = fetch(os_tree, arch)
        except Exception as exc:  # noqa: BLE001 - one dead tree skips, the refresh continues
            if progress:
                progress(f"Warning: fink bindist {os_tree}/{arch} unavailable ({exc}); skipped.")
            continue
        for name, token in archives.parse_bindist_packages(packages, os_tree, arch).items():
            state.setdefault(("fink", "package", name), []).append(token)
    return {key: sorted(tokens) for key, tokens in state.items()}


def load_state_file(path):
    data = json.loads(Path(path).read_text())
    return (
        {(m, t, n): tokens for k, tokens in data.get("binaries", {}).items() for m, t, n in [parse_state_key(k)]},
        data.get("generated_at"),
    )


def save_state_file(path, state, generated_at):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "generated_at": generated_at,
                "binaries": {state_key(m, t, n): sorted(tokens) for (m, t, n), tokens in state.items()},
            },
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )


def build_state(portindex_text=None, previous_catalog=None, seed=False, fetch=archives.fetch_archive_page,
                listing_fetch=archives.fetch_directory_listing, bindist=True, progress=None, delay=0.05,
                previous_state=None, checkpoint=None):
    """Compose the full refresh: diff, backstop, probe, merge, bindist."""
    if portindex_text is None:
        records = fetch_macports_portindex()
    else:
        records = parse_portindex(portindex_text, "portindex", "previous", "previous")
    previous_versions, previous_binaries, generated_at = {}, {}, None
    if previous_catalog is not None:
        previous_versions, previous_binaries, generated_at = previous_from_catalog(previous_catalog)
    if previous_state is not None:
        previous_binaries = dict(previous_state)
    macports_previous = {name: tokens for (manager, _, name), tokens in previous_binaries.items() if manager == "macports"}
    if seed:
        probe = valid_names({record.get("native_name", record.get("name")) for record in records})
        tripped = False
    else:
        changed = changed_ports(records, previous_versions)
        listing = archives.parse_directory_listing(listing_fetch())
        probe, tripped = select_probe_set(changed, backstop_ports(listing, generated_at), bool(previous_catalog or previous_state))
        if tripped:
            if progress:
                progress("Warning: empty probe set against nonempty history; probing everything (possible listing-format rot).")
            probe = valid_names({record.get("native_name", record.get("name")) for record in records})
    # Refresh mode re-probes the whole (already minimal) union; seed mode
    # skips checkpointed names so an interrupted seed resumes.
    probed = probe_ports(probe, fetch=fetch,
                         previous=macports_previous if seed else None,
                         progress=progress, delay=delay, checkpoint=checkpoint)
    state = dict(previous_binaries)
    for name, tokens in probed.items():
        state[("macports", "port", name)] = tokens
    if bindist:
        state.update(fetch_bindist_state(progress=progress))
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(prog="macpkg_catalog.archive_refresh")
    parser.add_argument("--output", required=True)
    parser.add_argument("--previous-catalog")
    parser.add_argument("--previous-state")
    parser.add_argument("--portindex-file")
    parser.add_argument("--seed", action="store_true")
    parser.add_argument("--no-bindist", action="store_true")
    parser.add_argument("--delay", type=float, default=0.05)
    args = parser.parse_args(argv)
    previous_catalog = None
    if args.previous_catalog:
        previous_catalog = json.loads(archives._get(args.previous_catalog, timeout=180))
    previous_state = None
    if args.previous_state and Path(args.previous_state).is_file():
        # Resume/merge: the output file doubles as the checkpoint.
        previous_state, _ = load_state_file(args.previous_state)
    portindex_text = Path(args.portindex_file).read_bytes() if args.portindex_file else None
    output = Path(args.output)
    resumed, _ = load_state_file(output) if output.is_file() else (None, None)
    if resumed:
        previous_state = {**(previous_state or {}), **resumed}

    def progress(message):
        print(message, file=sys.stderr)

    base = dict(previous_state or {})

    def checkpoint(running):
        merged = dict(base)
        for name, tokens in running.items():
            merged[("macports", "port", name)] = tokens
        save_state_file(output, merged, datetime.datetime.now(datetime.timezone.utc).isoformat())
        progress(f"Checkpoint: {len(merged)} identities")

    state = build_state(
        portindex_text=portindex_text,
        previous_catalog=previous_catalog,
        seed=args.seed,
        bindist=not args.no_bindist,
        progress=progress,
        delay=args.delay,
        previous_state=previous_state,
        checkpoint=checkpoint,
    )
    save_state_file(output, state, datetime.datetime.now(datetime.timezone.utc).isoformat())
    print(f"Wrote {output} ({len(state)} identities with binaries)")


if __name__ == "__main__":
    main()

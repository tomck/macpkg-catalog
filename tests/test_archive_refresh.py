"""Weekly orchestration: previous-state split, change selection, resume."""
import json

from macpkg_catalog.archive_refresh import (
    backstop_ports,
    build_state,
    changed_ports,
    load_state_file,
    parse_state_key,
    previous_from_catalog,
    save_state_file,
    select_probe_set,
    state_key,
)

CATALOG = {
    "generated_at": "2026-09-10T04:17:00+00:00",
    "packages": [
        {"manager": "macports", "package_type": "port", "native_name": "wget",
         "version": "1.24", "revision": "0", "binaries": ["darwin_23.x86_64"]},
        {"manager": "macports", "package_type": "port", "native_name": "node",
         "version": "24.0", "revision": "0", "binaries": []},
        {"manager": "homebrew", "package_type": "formula", "native_name": "wget",
         "version": "1.25", "binaries": ["sonoma"]},
    ],
}

RECORDS = [
    {"name": "wget", "version": "1.25", "revision": "0"},
    {"name": "node", "version": "24.0", "revision": "0"},
]


def test_previous_from_catalog_splits_versions_and_binaries():
    versions, binaries, generated_at = previous_from_catalog(CATALOG)
    assert versions == {"wget": ("1.24", "0"), "node": ("24.0", "0")}
    assert binaries == {
        ("macports", "port", "wget"): ["darwin_23.x86_64"],
        ("homebrew", "formula", "wget"): ["sonoma"],
    }
    assert generated_at == "2026-09-10T04:17:00+00:00"


def test_changed_ports_finds_bumped_and_added():
    records = RECORDS + [{"name": "ansible", "version": "12.0", "revision": "0"}]
    versions = {"wget": ("1.24", "0"), "node": ("24.0", "0")}
    assert changed_ports(records, versions) == {"wget", "ansible"}


def test_backstop_ports_uses_cutoff_or_everything():
    listing = {"wget": "2026-09-17 06:32", "node": "2026-09-10 11:05"}
    assert backstop_ports(listing, "2026-09-10T04:17:00+00:00") == {"wget", "node"}
    assert backstop_ports(listing, "2026-09-17T00:00:00+00:00") == {"wget"}
    assert backstop_ports(listing, None) == {"wget", "node"}


def test_select_probe_set_unions_and_trips_only_with_history():
    assert select_probe_set({"wget"}, {"node"}, True) == ({"wget", "node"}, False)
    assert select_probe_set(set(), set(), True) == (set(), True)
    assert select_probe_set(set(), set(), False) == (set(), False)


def test_state_key_round_trip():
    assert parse_state_key(state_key("macports", "port", "wget")) == ("macports", "port", "wget")


def test_probe_ports_checkpoints_periodically():
    from macpkg_catalog.archive_refresh import probe_ports
    saved = []
    state = probe_ports(
        ["b", "a"], fetch=lambda name: f'<a href="{name}-1.darwin_23.x86_64.tbz2">x</a>',
        delay=0, checkpoint=saved.append, checkpoint_every=2,
    )
    assert len(saved) == 1
    assert saved[0]["a"] == ["darwin_23.x86_64"]
    assert state["b"] == ["darwin_23.x86_64"]


def test_state_file_round_trip(tmp_path):
    path = tmp_path / "state.json"
    state = {("macports", "port", "wget"): ["darwin_23.x86_64"]}
    save_state_file(path, state, "2026-09-17T00:00:00+00:00")
    loaded, generated_at = load_state_file(path)
    assert loaded == state
    assert generated_at == "2026-09-17T00:00:00+00:00"


def test_build_state_probes_only_the_union_and_merges(tmp_path):
    portindex = (
        "wget 100 description {old} version 1.25 revision 0\n"
        "node 200 description {js} version 24.0 revision 0\n"
    )
    listing = "ignored"
    calls = []

    def fetch(name):
        calls.append(name)
        return f'<a href="wget-1.25_0.darwin_23.x86_64.tbz2">x</a>' if name == "wget" else "empty"

    def listing_fetch():
        return listing

    import macpkg_catalog.archives as archives_module
    real_listing = archives_module.parse_directory_listing
    archives_module.parse_directory_listing = lambda html: {"wget": "2026-09-17 06:32"}
    try:
        state = build_state(
            portindex_text=portindex,
            previous_catalog=CATALOG,
            fetch=fetch,
            listing_fetch=listing_fetch,
            bindist=False,
            delay=0,
        )
    finally:
        archives_module.parse_directory_listing = real_listing
    assert sorted(calls) == ["wget"]
    assert state[("macports", "port", "wget")] == ["darwin_23.x86_64"]


def test_build_state_tripwire_probes_everything(tmp_path):
    portindex = "wget 100 description {old} version 1.24 revision 0\n"
    calls = []

    def fetch(name):
        calls.append(name)
        return "empty"

    import macpkg_catalog.archives as archives_module
    real_listing = archives_module.parse_directory_listing
    archives_module.parse_directory_listing = lambda html: {}
    try:
        state = build_state(
            portindex_text=portindex,
            previous_catalog=CATALOG,
            fetch=fetch,
            listing_fetch=lambda: "ignored",
            bindist=False,
            delay=0,
        )
    finally:
        archives_module.parse_directory_listing = real_listing
    assert calls == ["wget"]
    assert state[("macports", "port", "wget")] == []

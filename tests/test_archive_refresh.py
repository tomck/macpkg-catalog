"""Weekly orchestration: previous-state split, change selection, resume."""
import json

from macpkg_catalog.archive_refresh import (
    backstop_ports,
    build_state,
    changed_ports,
    fetch_bindist_state,
    load_state_file,
    parse_state_key,
    previous_from_catalog,
    probe_ports,
    save_state_file,
    select_probe_set,
    state_key,
    valid_names,
)


def portindex_entry(name, body):
    return "%s %d\n%s\n" % (name, len(body) + 1, body)

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
    portindex = portindex_entry("wget", "description {old} version 1.25 revision 0") + portindex_entry(
        "node", "description {js} version 24.0 revision 0")
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
    portindex = portindex_entry("wget", "description {old} version 1.24 revision 0")
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


def test_changed_ports_and_probe_drop_implausible_names():
    # Valid-shaped words ("Also") are stopped by PortIndex framing (see
    # test_sources); this filter catches the punctuation-shaped fallout.
    records = RECORDS + [
        {"native_name": "DANGER:", "version": "1.0", "revision": "0"},
        {"native_name": "1.}", "version": "1.0", "revision": "0"},
        {"native_name": "*}", "version": "1.0", "revision": "0"},
    ]
    assert changed_ports(records, {}) == {"wget", "node"}
    assert valid_names({"wget", "DANGER:", "1.}", ""}) == {"wget"}
    calls = []
    probe_ports(["wget", "DANGER:", "1.}"], fetch=lambda name: calls.append(name) or "empty", delay=0)
    assert calls == ["wget"]


def test_fetch_bindist_state_skips_dead_tree_with_warning():
    warnings = []

    def fetch(os_tree, arch):
        if os_tree == "10.15":
            raise RuntimeError("HTTP Error 404: Not Found")
        return "Package: wget\nFilename: stable/main/binary-darwin-x86_64/wget.deb\n\n"

    state = fetch_bindist_state(
        targets=(("10.14", "x86_64"), ("10.15", "x86_64")),
        fetch=fetch,
        progress=warnings.append,
    )
    assert state == {("fink", "package", "wget"): ["10.14/binary-darwin-x86_64"]}
    assert len(warnings) == 1 and "10.15" in warnings[0]


def test_build_state_seed_uses_native_name():
    portindex = portindex_entry("wget", "description {old} version 1.25 revision 0")
    calls = []
    state = build_state(
        portindex_text=portindex,
        seed=True,
        fetch=lambda name: calls.append(name) or "empty",
        bindist=False,
        delay=0,
    )
    assert calls == ["wget"]
    assert state[("macports", "port", "wget")] == []

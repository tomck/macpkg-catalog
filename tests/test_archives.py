"""Binary-availability signals: parsers, diff/merge, schema round-trip."""
from macpkg_catalog.archives import (
    attach_archive_state,
    merge_archive_state,
    parse_archive_page,
    parse_bindist_packages,
    parse_directory_listing,
)
from macpkg_catalog.core import validate
from macpkg_catalog.sources import normalize_homebrew

ARCHIVE_HTML = """<html><body><table>
<tr><td><a href="wget-1.25.0_1+gnutls.darwin_19.x86_64.tbz2">wget-1.25.0_1+gnutls.darwin_19.x86_64.tbz2</a></td></tr>
<tr><td><a href="wget-1.25.0_1+gnutls.darwin_19.x86_64.tbz2">wget-1.25.0_1+gnutls.darwin_19.x86_64.tbz2</a></td></tr>
<tr><td><a href="wget-1.25.0_1+gnutls.darwin_23.arm64.tbz2">wget-1.25.0_1+gnutls.darwin_23.arm64.tbz2</a></td></tr>
<tr><td><a href="wget-1.25.0_1+gnutls.darwin_23.x86_64.tbz2">wget-1.25.0_1+gnutls.darwin_23.x86_64.tbz2</a></td></tr>
</table></body></html>"""

LISTING_HTML = """<html><body><table>
<tr><th><a href="?C=N;O=D">Name</a></th></tr>
<tr><td><a href="/">Parent Directory</a></td><td align="right">  - </td></tr>
<tr><td><a href="wget/">wget/</a></td><td align="right">2026-09-17 06:32  </td></tr>
<tr><td><a href="node/">node/</a></td><td align="right">2026-09-10 11:05  </td></tr>
</table></body></html>"""

BINDIST_TEXT = """Package: wget
Version: 1.25.0-1
Filename: stable/main/binary-darwin-x86_64/wget_1.25.0-1_darwin-x86_64.deb
Description: Internet file retriever
 continued line

Package: node
Version: 24.1-1
Filename: stable/main/binary-darwin-x86_64/node_24.1-1_darwin-x86_64.deb
"""



def test_parse_archive_page_extracts_platform_tokens():
    assert parse_archive_page(ARCHIVE_HTML) == [
        "darwin_19.x86_64",
        "darwin_23.arm64",
        "darwin_23.x86_64",
    ]


def test_parse_archive_page_empty_without_archives():
    assert parse_archive_page("<html><body>no builds</body></html>") == []


def test_parse_directory_listing_maps_folders_to_mtimes():
    assert parse_directory_listing(LISTING_HTML) == {
        "wget": "2026-09-17 06:32",
        "node": "2026-09-10 11:05",
    }


def test_parse_bindist_packages_maps_names_to_tree_token():
    assert parse_bindist_packages(BINDIST_TEXT, "10.14", "x86_64") == {
        "wget": "10.14/binary-darwin-x86_64",
        "node": "10.14/binary-darwin-x86_64",
    }


def test_merge_archive_state_probed_wins():
    previous = {("macports", "port", "wget"): ["darwin_19.x86_64"]}
    probed = {("macports", "port", "wget"): ["darwin_23.x86_64"]}
    assert merge_archive_state(previous, probed)[("macports", "port", "wget")] == ["darwin_23.x86_64"]


def test_attach_archive_state_sets_binaries_only_on_match():
    packages = [
        {"manager": "macports", "package_type": "port", "native_name": "wget", "binaries": []},
        {"manager": "macports", "package_type": "port", "native_name": "node", "binaries": []},
    ]
    state = {("macports", "port", "wget"): ["darwin_23.x86_64"]}
    attach_archive_state(packages, state)
    assert packages[0]["binaries"] == ["darwin_23.x86_64"]
    assert packages[1]["binaries"] == []


def test_formula_bottle_tags_become_binaries():
    row = {"name": "wget", "bottle": {"stable": {"files": {"sonoma": {}, "arm64_sonoma": {}}}}}
    package = normalize_homebrew([row], "formula", "sha", "date")[0]
    assert package["binaries"] == ["arm64_sonoma", "sonoma"]


def test_formula_without_bottles_has_empty_binaries():
    package = normalize_homebrew([{"name": "from-source-only"}], "formula", "sha", "date")[0]
    assert package["binaries"] == []


def test_cask_binaries_are_any():
    row = {"token": "docker-desktop", "name": ["Docker Desktop"], "version": "4.0"}
    package = normalize_homebrew([row], "cask", "sha", "date")[0]
    assert package["binaries"] == ["any"]


def test_identity_carries_binaries_when_present():
    from macpkg_catalog.mapping import identity
    package = {"manager": "macports", "package_type": "port", "native_name": "wget",
               "binaries": ["darwin_23.x86_64"]}
    assert identity(package)["binaries"] == ["darwin_23.x86_64"]


def test_identity_omits_empty_binaries():
    from macpkg_catalog.mapping import identity
    package = {"manager": "macports", "package_type": "port", "native_name": "wget"}
    assert "binaries" not in identity(package)


def test_binaries_field_validates_clean():
    packages = [
        {"manager": "homebrew", "package_type": "formula", "native_name": "wget",
         "binaries": ["sonoma", "arm64_sonoma"]},
        {"manager": "macports", "package_type": "port", "native_name": "wget",
         "binaries": ["darwin_23.x86_64"]},
    ]
    assert validate(packages, []) == []

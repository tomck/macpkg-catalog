"""Binary-availability signals: parse-only helpers plus thin network fetchers.

Vocabulary (documented in docs/SCHEMA.md, ranking-only, never confidence):
- homebrew formulae: raw bottle tags, e.g. sonoma (Intel), arm64_sonoma.
- homebrew casks: ["any"] — casks are inherently binaries.
- macports: darwin platform tokens from archive filenames,
  e.g. darwin_23.x86_64 (from packages.macports.org per-port pages).
- fink: "<os-tree>/<arch-dir>" tokens from bindist Packages indexes,
  e.g. 10.14/binary-darwin-x86_64.

Refresh strategy (orchestrated by the caller, not here): seed the full
port set once with checkpoints, then weekly take the union of the
PortIndex version diff and the DirectoryIndex mtime diff and probe only
those pages. A suspiciously small union means listing-format rot: warn
and re-probe fully that week.
"""
import gzip
import re
import urllib.request

USER_AGENT = "macpkgmap/0.5"
PACKAGES_BASE = "https://packages.macports.org"
BINDIST_BASE = "http://bindist.finkmirrors.net"
# OS trees x architectures probed for Fink binaries. Trees publish only a
# gzipped Packages index; 10.15 currently has a Release but no Packages file,
# so it stays out until its bindist appears.
FINK_BINDIST_TARGETS = (("10.13", "x86_64"), ("10.14", "x86_64"))

ARCHIVE_FILENAME = re.compile(r"\.((darwin_\d+)\.(arm64|x86_64|ppc|i386))\.tbz2(?=[\"'<\s])")
LISTING_ROW = re.compile(r'<a href="([^"?]+)">[^<]*</a></td><td align="right">([^<]+)</td>')


def parse_archive_page(html):
    """Platform tokens from a packages.macports.org per-port page."""
    return sorted({match.group(1) for match in ARCHIVE_FILENAME.finditer(html)})


def parse_directory_listing(html):
    """Map per-port folder href to its last-modified stamp."""
    result = {}
    for match in LISTING_ROW.finditer(html):
        href, modified = match.group(1), match.group(2).strip()
        if href.endswith("/") and not href.startswith(("?", "/")):
            result[href.rstrip("/")] = modified
    return result


def parse_bindist_packages(text, os_tree, arch):
    """Map package name to deb filename from a Fink bindist Packages index."""
    result = {}
    current = {}
    def flush():
        if "Package" in current and "Filename" in current:
            result[current["Package"]] = current["Filename"]
    for line in text.splitlines():
        if not line.strip():
            flush()
            current = {}
        elif line[0] in (" ", "\t"):
            pass
        elif ":" in line:
            field, value = line.split(":", 1)
            current[field.strip()] = value.strip()
    flush()
    token = f"{os_tree}/binary-darwin-{arch}"
    return {name: token for name in result}


def merge_archive_state(previous, probed):
    """Merge fresh per-port probes over previous state; probed wins per port."""
    merged = dict(previous)
    merged.update(probed)
    return merged


def attach_archive_state(packages, state):
    """Set binaries on package dicts from {(manager, type, name): [tokens]}."""
    for package in packages:
        tokens = state.get((package.get("manager"), package.get("package_type"), package.get("native_name")))
        if tokens:
            package["binaries"] = sorted(tokens)
    return packages


def _get(url, timeout=60):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def fetch_archive_page(port):
    return _get(f"{PACKAGES_BASE}/{port}/")


def fetch_directory_listing():
    return _get(PACKAGES_BASE + "/")


def _get_bytes(url, timeout=60):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_bindist_packages(os_tree, arch):
    """Fetch a bindist Packages.gz index as text (gunzipped when needed)."""
    payload = _get_bytes(f"{BINDIST_BASE}/{os_tree}/dists/stable/main/binary-darwin-{arch}/Packages.gz")
    if payload[:2] == b"\x1f\x8b":
        payload = gzip.decompress(payload)
    return payload.decode("utf-8", "replace")

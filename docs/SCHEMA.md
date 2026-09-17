# Schema
Package records contain manager, type, native name, aliases, historical names, description, homepage, upstream, version/revision, provides/conflicts/replaces/renamed-by, source URL/revision, last-seen, and binaries. Relations are separate and contain source, target, confidence, method, evidence, review status, and source versions.
# Binary availability
`binaries` is ranking-only evidence, like popularity: it never raises confidence or authorizes installation. Vocabulary is source-native per manager: Homebrew formulae carry raw bottle tags (`sonoma` is Intel, `arm64_sonoma` is ARM); Homebrew casks carry `["any"]` (casks are inherently binaries); MacPorts carries `darwin_<major>.<arch>` tokens from archive filenames (e.g. `darwin_23.x86_64`); Fink carries `<os-tree>/binary-darwin-<arch>` tokens from bindist Packages indexes (e.g. `10.14/binary-darwin-x86_64`). Empty means unknown, never "source-only".
# Popularity records

Popularity is separate from package identity and relationships. Homebrew
analytics are stored with their period, source URL, count, rank, and whether
the value represents all installs or install-on-request events. Intel fields
remain `unknown` unless the source explicitly provides package-level data.

Near-hit relationships use `matching_method: version-family`, a confidence
cap below the automatic threshold, and `review_status: needs-review`.

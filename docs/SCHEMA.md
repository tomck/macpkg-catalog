# Schema
Package records contain manager, type, native name, aliases, historical names, description, homepage, upstream, version/revision, provides/conflicts/replaces/renamed-by, source URL/revision, and last-seen. Relations are separate and contain source, target, confidence, method, evidence, review status, and source versions.
# Popularity records

Popularity is separate from package identity and relationships. Homebrew
analytics are stored with their period, source URL, count, rank, and whether
the value represents all installs or install-on-request events. Intel fields
remain `unknown` unless the source explicitly provides package-level data.

Near-hit relationships use `matching_method: version-family`, a confidence
cap below the automatic threshold, and `review_status: needs-review`.

# macpkgmap

Development status: reproducible catalog artifacts, conservative relationships, near-hit review records, popularity data, JSON/SQLite queries, checksums, and static lookup output are implemented. Live source refresh and deployment are staged for the automated workflow; incomplete source fetches must fail validation rather than publish partial data.

The `source-download-smoke-test` workflow verifies the public Homebrew,
MacPorts PortIndex, and Fink distribution downloads on a GitHub-hosted runner
before the full refresh pipeline is enabled.

Neutral, reproducible package identity and relationship catalog for Homebrew, MacPorts, and Fink. Identity is `(manager, type, native_name)`; relationships are separate and carry confidence, method, evidence, review status, and source versions. Similarity never proves equivalence.

See `docs/` and `curated/` for policy, schema, sources, and usage. Homebrew’s public analytics provide 30-, 90-, and 365-day install and install-on-request reports; Intel-specific package demand is recorded only when explicitly available, otherwise it remains unknown.

The migration applications are maintained separately in
[brew2port](https://github.com/tomck/brew2port),
[brew2fink](https://github.com/tomck/brew2fink), and
[macpkg-migrate](https://github.com/tomck/macpkg-migrate). They consume the
published catalog contract; this repository contains no application copies.

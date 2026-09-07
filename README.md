# macpkgmap

Development status: reproducible catalog artifacts, conservative relationships, near-hit review records, popularity data, JSON/SQLite queries, checksums, and static lookup output are implemented. Live source refresh and deployment are staged for the automated workflow; incomplete source fetches must fail validation rather than publish partial data.

Neutral, reproducible package identity and relationship catalog for Homebrew, MacPorts, and Fink. Identity is `(manager, type, native_name)`; relationships are separate and carry confidence, method, evidence, review status, and source versions. Similarity never proves equivalence.

See `docs/` and `curated/` for policy, schema, sources, and usage. Homebrew’s public analytics provide 30-, 90-, and 365-day install and install-on-request reports; Intel-specific package demand is recorded only when explicitly available, otherwise it remains unknown.

The earlier Homebrew-to-MacPorts application has been migrated under
`integrations/brew2port/`. It remains a separate consumer project; the catalog
is the reusable source of package identities and reviewed relationships.

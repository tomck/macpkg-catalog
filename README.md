# macpkg-catalog

Development status: offline snapshot generation, JSON/SQLite queries, checksums, and static lookup output are implemented. Full live source import, mapping/curation ingestion, and deployment are still in progress. The refresh workflow currently fails explicitly rather than publishing a partial catalog.

Neutral, reproducible package identity and relationship catalog for Homebrew, MacPorts, and Fink. Identity is `(manager, type, native_name)`; relationships are separate and carry confidence, method, evidence, review status, and source versions. Similarity never proves equivalence.

See `docs/` and `curated/` for policy, schema, sources, and usage.

The earlier Homebrew-to-MacPorts application has been migrated under
`integrations/brew2port/`. It remains a separate consumer project; the catalog
is the reusable source of package identities and reviewed relationships.

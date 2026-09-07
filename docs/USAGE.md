# macpkgmap usage

`macpkgmap` is a neutral, offline-readable catalog of package identities and
cross-manager relationships for Homebrew, MacPorts, and Fink. It does not
install, remove, or modify packages.

## Published snapshot

The continuously published snapshot is available at
`https://tomck.github.io/macpkg-catalog/`. Its main files are:

```text
catalog.json       complete portable snapshot
packages.json      package records only
relations.json     relationship records only
popularity.json    contextual popularity data
catalog.sqlite     local SQLite database
checksums.txt      SHA-256 checksums for published files
mapping-report.md  human-readable generation summary
v1/package/...     exact package lookup documents
v1/relations/...   exact relationship lookup documents
```

Consumers should download a consistent set of files from one catalog version
and verify `checksums.txt` when reproducibility matters. Full snapshots and
static responses include `catalog_version` where applicable.

## Install and query locally

From a checkout:

```sh
python3 -m pip install -e .
macpkgmap lookup homebrew formula wget --snapshot dist/catalog.sqlite
macpkgmap relations homebrew formula wget --snapshot dist/catalog.sqlite
macpkgmap search "video editor" --snapshot dist/catalog.sqlite
macpkgmap popularity homebrew formula wget --snapshot dist/catalog.json
macpkgmap export --format sqlite --snapshot dist/catalog.json --output copy.sqlite
```

All query commands are offline. `--snapshot` accepts a full `catalog.json`,
`catalog.sqlite`, or a relevant published JSON array such as `relations.json`
or `packages.json`. SQLite can also be queried directly:

```sh
sqlite3 dist/catalog.sqlite \
  'SELECT source_name, target_name, confidence, review_status FROM relations;'
```

## Generate artifacts locally

Generation consumes a normalized snapshot and writes to an empty directory:

```sh
macpkgmap generate --input snapshots/catalog.json --output build/catalog
```

To refresh sources locally, fetch first and then generate:

```sh
macpkgmap fetch-live --output snapshots/catalog.json
macpkgmap generate --input snapshots/catalog.json --output build/catalog
```

The GitHub Actions refresh job performs the same fetch, generation, tests,
validation, checksum creation, and Pages deployment weekly or on manual
dispatch, using standard GitHub-hosted runners.

## Identity and relationship contract

A package identity is `(manager, type, native_name)`, for example
`(homebrew, formula, wget)` or `(macports, port, wget)`. Package records also
contain aliases and historical names, descriptive and upstream identity,
versions and revisions, `provides`, `conflicts`, `replaces`, `renamed_by`,
source provenance, and `last_seen`.

Relations are separate from packages. Supported types are `equivalent`,
`renamed-to`, `replaced-by`, `split-from`, `split-into`, `provides`,
`conflicts`, and `no-equivalent`. Each relation has `source`, `target`,
`confidence`, `matching_method`, `evidence`, `review_status`, and
`source_catalog_versions`.

`automatic` means evidence is strong enough for catalog use; `needs-review`
is a suggestion only. Spelling, character overlap, and description similarity
never prove equivalence. `macs-fan-control` and `qmail-spamcontrol` are a
tested negative example and must not be mapped merely because their names
overlap.

## Curating data

Add durable decisions to `curated/relations.yaml`, `curated/aliases.yaml`,
`curated/no-equivalent.yaml`, or `curated/sources.yaml`. Include a YAML
comment explaining why the decision is valid or invalid, using inspectable
upstream or source evidence. Run `python3 -m pytest -q` before submitting.
Validation rejects duplicate identities, missing endpoints, invalid manager
names, weak automatic mappings, conflicting curated entries, and known
negative examples.

## Consumer guidance

`brew2port`, `brew2fink`, and `macpkg-migrate` are separate applications and
should consume this contract rather than copy source-download or matching
logic. Migration plans should record catalog version, relationship type,
confidence, review status, matching method, and evidence.

Consumers should query the catalog first, verify that the proposed local
target still exists, and use local heuristics only when the package is absent
from the catalog. A `needs-review` or missing relation must never by itself
authorize installation or removal.

## Static hosting limitations

GitHub Pages serves files but provides no server-side search, joins,
authentication, or transactional multi-file reads. Download a snapshot and
query SQLite or JSON locally. Pin or record the catalog version and validate
checksums; separate URLs fetched at different times may belong to different
releases.

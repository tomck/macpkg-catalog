# Usage
Generate from a normalized snapshot with `python3 -m macpkg_catalog generate --input snapshot.json --output output`. The output directory must be empty. A snapshot contains `packages`, `sources`, and optionally `relations`; omitting relations runs the conservative matching engine.

Query JSON or SQLite entirely offline:

```sh
python3 -m macpkg_catalog lookup homebrew formula wget --snapshot output/catalog.json
python3 -m macpkg_catalog relations homebrew formula wget --snapshot output/catalog.sqlite
python3 -m macpkg_catalog search "video editor" --snapshot output/catalog.sqlite
python3 -m macpkg_catalog export --format sqlite --snapshot output/catalog.json --output copy.sqlite
sqlite3 output/catalog.sqlite 'SELECT source_name,target_name,confidence FROM relations;'
```

Generation includes catalog.json, catalog.sqlite, packages.json, relations.json, checksums.txt, mapping-report.md, and static files under v1/package, v1/lookup, and v1/relations. Responses contain the catalog version. Static Pages cannot perform arbitrary server-side searches; clients download a snapshot and query locally.

Full live refresh and deployment are not yet operational. The old dist directory is a scaffold artifact and is not a published catalog.

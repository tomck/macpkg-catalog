# brew2port

Conservative Homebrew → MacPorts migration planner for Intel and Apple-silicon Macs.

`brew2port` inventories only formulae installed on request (not dependency leaves) and installed casks, scores possible MacPorts equivalents, and produces a reviewable plan. It never removes Homebrew packages automatically. MacPorts installation is opt-in and each command is shown before execution.

For the Homebrew tap, use `brew tap tomck/brew2port`; the tap repository is named `homebrew-brew2port` as required by Homebrew, while the source project remains `brew2port`.

The one-stop preparation workflow is `brew2port prepare`. It ensures MacPorts is present, refreshes its local PortIndex, inventories Homebrew, generates `migration-plan.json`, and writes `migration-preview.csv` for review. It does not install any migrated ports. After reviewing the CSV, run `brew2port migrate --plan migration-plan.json --install`; that command asks for confirmation, while `--yes` enables unattended execution.

If MacPorts is not installed, bootstrap it explicitly with `brew2port setup-macports`. This detects the macOS release, downloads the matching official installer, validates its checksum when the release provides one, validates the package signature, asks for administrator authorization, and verifies `/opt/local/bin/port` afterward. Use `--dry-run` to inspect the selected installer without changing the system, or `--skip-update` to omit the post-install `port selfupdate`.

To refresh an existing MacPorts installation independently, run `brew2port update-macports`. The equivalent plan option is `brew2port plan --inventory brew-inventory.json --update-macports`.

## Quick start

```sh
python3 -m brew2port inventory --output brew-inventory.json
python3 -m brew2port plan --inventory brew-inventory.json --output migration-plan.json
python3 -m brew2port plan --inventory brew-inventory.json --format text
python3 -m brew2port migrate --plan migration-plan.json --install
python3 -m brew2port verify --plan migration-plan.json
```

Without `--install`, `migrate` is a dry run. `--yes` is required for unattended installation. Homebrew is preserved; uninstalling it is deliberately outside this tool.

## Mapping data

`plan` first checks a small, published definitions database of trusted mappings. It is cached at `~/.cache/brew2port/definitions.json`, so common packages do not require a large catalog download or pairwise matching. Anything absent from that table falls back to the local MacPorts `PortIndex` when `port` is installed. Use `--refresh-definitions` to fetch the newest published table. If MacPorts is not installed, brew2port downloads the public MacPorts catalog from its read-only API and caches it at `~/.cache/brew2port/macports-ports.json`. Use `--refresh-ports` to update that web cache, or `--ports FILE` for a local snapshot. `build-index --output FILE` explicitly saves a fresh catalog. A port index can be JSON (an array of objects with `name`, `description`, `homepage`, `provides`, `replaces`, `conflicts`, or `aliases`), TSV/CSV, or the line-oriented output of `port search --index`. The optional `--overrides FILE` flag accepts a curated override file when needed.

The definitions database is generated from the current Homebrew formula/cask APIs and MacPorts port index by `build-definitions`. A scheduled GitHub Actions workflow refreshes `definitions/mappings.json` weekly and can also be run manually. The workflow publishes only high-confidence or curated mappings; it does not turn uncertain fuzzy matches into automatic installations. The repository is public, so standard GitHub-hosted Actions runners are free. Users can also generate a private/local table when reviewing changes:

```sh
python3 -m brew2port build-definitions --output definitions/mappings.json
```

```json
{"muse-code": {"port": "muse_code", "confidence": 1.0, "reason": "curated"}, "foo": null}
```

`null` explicitly marks a package as no-match. Matching order is exact, normalized spelling, aliases/provides/replaces, conservative shared-stem/token evidence, then curated overrides. Generic character similarity is deliberately not treated as package evidence, and casks do not receive spelling-only heuristic matches. Scores are evidence, not proof; ambiguous and low-confidence results require review.

## Development

```sh
python3 -m unittest discover -s tests
python3 -m pip install .
```

The Homebrew formula template is in `packaging/homebrew/brew2port.rb`; release archives should be built from a tagged commit and checksum-pinned there.

Sources: [Homebrew Formulae API](https://formulae.brew.sh/docs/api/), [Homebrew querying](https://docs.brew.sh/Querying-Brew), and [MacPorts port(1)](https://man.macports.org/port.1.html).

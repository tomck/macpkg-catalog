# brew2fink

Install from the Homebrew tap:

```sh
brew tap tomck/brew2fink
brew install brew2fink
```

Safe Homebrew-to-Fink migration planner. It inventories explicitly requested
Homebrew formulae and installed casks, reads the published `macpkg-catalog`,
and produces a reviewable migration plan and CSV. Confident Fink mappings may
be installed only with `--install`; near-hits and ambiguous results always
remain review-only. Homebrew is never removed automatically.

```sh
brew2fink prepare
brew2fink migrate --plan migration-plan.json
brew2fink migrate --plan migration-plan.json --install
```

#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/codex-commit.sh --model MODEL [--reasoning-effort EFFORT]
                              [--thread THREAD_ID] -- GIT_COMMIT_ARGUMENTS...

This wrapper enables the gated prepare-commit-msg hook. Ordinary git commits
remain untouched; commits made through this wrapper receive Codex attribution.
EOF
}

model=${CODEX_COMMIT_MODEL:-}
reasoning=${CODEX_COMMIT_REASONING_EFFORT:-}
thread=${CODEX_COMMIT_THREAD_ID:-}

while (($#)); do
    case $1 in
        --model) (($# >= 2)) || { echo "--model requires a value" >&2; exit 2; }; model=$2; shift 2 ;;
        --model=*) model=${1#*=}; shift ;;
        --reasoning-effort) (($# >= 2)) || { echo "--reasoning-effort requires a value" >&2; exit 2; }; reasoning=$2; shift 2 ;;
        --reasoning-effort=*) reasoning=${1#*=}; shift ;;
        --thread) (($# >= 2)) || { echo "--thread requires a value" >&2; exit 2; }; thread=$2; shift 2 ;;
        --thread=*) thread=${1#*=}; shift ;;
        --) shift; break ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown wrapper option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

[[ -n $model ]] || { echo "A precise --model value is required." >&2; exit 2; }
(($#)) || { echo "Pass git commit arguments after --." >&2; exit 2; }

export CODEX_COMMIT=1 CODEX_COMMIT_MODEL=$model
export CODEX_COMMIT_REASONING_EFFORT=$reasoning CODEX_COMMIT_THREAD_ID=$thread
exec git commit "$@"

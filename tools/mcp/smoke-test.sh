#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${ZANDRONUM_NODE:-}" ]]; then
  node_bin="$ZANDRONUM_NODE"
else
  node_bin="$(command -v node)" || {
    echo "node not found on PATH; set ZANDRONUM_NODE" >&2
    exit 1
  }
fi

exec "$node_bin" "$script_dir/smoke-test.mjs" "$@"

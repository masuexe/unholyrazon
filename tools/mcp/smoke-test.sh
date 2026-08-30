#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
node_bin="${ZANDRONUM_NODE:-/home/user/.nvm/versions/node/v22.23.2/bin/node}"

exec "$node_bin" "$script_dir/smoke-test.mjs" "$@"

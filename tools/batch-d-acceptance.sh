#!/usr/bin/env bash
set -uo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mode="${1:-quick}"

usage() {
  cat <<'EOF'
Usage: batch-d-acceptance.sh [quick|runtime|full|--help]

  quick    static/resource checks, boss definitions, and PK3 validation
  runtime  direct minimal startup plus optional MCP smoke
  full     quick checks and direct full-profile startup

MCP is attempted in runtime mode but reported separately because it depends on
the local MCP server. Multiplayer/directed gameplay remains a manual gate.
EOF
}

if [[ "$mode" == "--help" || "$mode" == "-h" ]]; then usage; exit 0; fi
if [[ "$mode" != "quick" && "$mode" != "runtime" && "$mode" != "full" ]]; then usage >&2; exit 2; fi

failures=0
run_required() {
  printf '\n== %s ==\n' "$1"
  shift
  "$@" || failures=$((failures + 1))
}

if [[ "$mode" == "quick" || "$mode" == "full" ]]; then
  run_required "Batch D source/resources" python3 "$repo_root/tools/check_batch_d.py"
  run_required "Boss registry actors" python3 "$repo_root/tools/check_boss_defs.py"
  run_required "Packaged mod" "$repo_root/tools/validate-build-pk3.sh"
fi

if [[ "$mode" == "runtime" ]]; then
  run_required "Direct minimal startup" node "$repo_root/tools/direct-startup-test.mjs"
  printf '\n== Optional MCP smoke ==\n'
  if ! "$repo_root/tools/mcp/smoke-test.sh" --json; then
    printf 'SKIP/INFRA: MCP smoke unavailable; direct startup result above remains valid.\n'
  fi
fi

if [[ "$mode" == "full" ]]; then
  run_required "Direct full-profile startup" node "$repo_root/tools/direct-startup-test.mjs" --profile mm8bdm-v6c-full --duration-sec 30
fi

printf '\nManual gate: server + 2 clients, forced events/combos, reconnect/disconnect, two-round cleanup, and HUD aspect checks.\n'
if (( failures )); then
  printf 'Batch D automated acceptance: FAIL (%d required stage(s) failed)\n' "$failures"
  exit 1
fi
printf 'Batch D automated acceptance: PASS (manual multiplayer gate still required)\n'

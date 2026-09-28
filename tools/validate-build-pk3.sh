#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
pk3_path="${1:-$repo_root/out/build.pk3}"
json=0
if [[ "$pk3_path" == "--json" ]]; then
  json=1
  pk3_path="${2:-$repo_root/out/build.pk3}"
fi

if [[ ! -f "$pk3_path" ]]; then
  echo "error: PK3 not found: $pk3_path" >&2
  exit 2
fi

if ! unzip -t "$pk3_path" >/dev/null; then
  echo "error: invalid ZIP/PK3 archive: $pk3_path" >&2
  exit 1
fi

mapfile -t entries < <(unzip -Z1 "$pk3_path")
# Engine authentication compares full lump paths case-insensitively.
duplicates=()
declare -A seen=()
for entry in "${entries[@]}"; do
  [[ "$entry" == */ ]] && continue
  key="${entry,,}"
  if [[ -v 'seen[$key]' ]]; then
    duplicates+=("$key")
  fi
  seen[$key]=1
done
if (( ${#duplicates[@]} )); then
  if (( json )); then
    printf '{"status":"error","reason":"duplicate_lumps","duplicates":['
    sep=""
    for entry in "${duplicates[@]}"; do
      entry="${entry//\\/\\\\}"
      entry="${entry//\"/\\\"}"
      printf '%s"%s"' "$sep" "$entry"
      sep=,
    done
    printf ']}\n'
  else
    printf 'error: duplicate lump path (case-insensitive): %s\n' "${duplicates[@]}" >&2
  fi
  exit 1
fi
# CORE8BDT must shadow the base-game lump. Naming it 8BDT.o leaves imports
# using the stock library, which lacks UH's getPitCount and crashes in ACS.
required=(DECORATE KEYCONF LOADACS acs/CORE8BDT.o)
missing=()
for lump in "${required[@]}"; do
  if [[ ! -v 'seen[${lump,,}]' ]]; then
    missing+=("$lump")
  fi
done

size_bytes="$(stat -c '%s' "$pk3_path")"
json_path="${pk3_path//\\/\\\\}"
json_path="${json_path//\"/\\\"}"
json_path="${json_path//$'\n'/\\n}"
if (( ${#missing[@]} )); then
  if (( json )); then
    printf '{"status":"error","path":"%s","entries":%d,"size_bytes":%d,"missing":[' "$json_path" "${#entries[@]}" "$size_bytes"
    printf '"%s"' "${missing[0]}"
    for lump in "${missing[@]:1}"; do printf ',"%s"' "$lump"; done
    printf ']}\n'
  else
    printf 'status=error path=%s entries=%d size_bytes=%d missing=%s\n' \
      "$pk3_path" "${#entries[@]}" "$size_bytes" "${missing[*]}" >&2
  fi
  exit 1
fi

if (( json )); then
  printf '{"status":"ok","path":"%s","entries":%d,"size_bytes":%d}\n' \
    "$json_path" "${#entries[@]}" "$size_bytes"
else
  printf 'status=ok path=%s entries=%d size_bytes=%d required=DECORATE,KEYCONF,LOADACS,acs/CORE8BDT.o\n' \
    "$pk3_path" "${#entries[@]}" "$size_bytes"
fi

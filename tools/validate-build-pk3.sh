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
required=(DECORATE KEYCONF LOADACS)
missing=()
for lump in "${required[@]}"; do
  # Do not use grep -q here: with `pipefail`, an early match makes printf see
  # SIGPIPE and incorrectly turns a valid archive into a failure.
  if ! printf '%s\n' "${entries[@]}" | grep -Fx "$lump" >/dev/null; then
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
  printf 'status=ok path=%s entries=%d size_bytes=%d required=DECORATE,KEYCONF,LOADACS\n' \
    "$pk3_path" "${#entries[@]}" "$size_bytes"
fi

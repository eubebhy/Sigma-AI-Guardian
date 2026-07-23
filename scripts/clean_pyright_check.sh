#!/usr/bin/env bash
set -euo pipefail

if (( $# != 1 )); then
  printf 'Usage: %s <python-file-or-directory>\n' "$0" >&2
  exit 2
fi

TARGET="$1"

if [[ ! -f "$TARGET" && ! -d "$TARGET" ]]; then
  printf 'Target does not exist: %s\n' "$TARGET" >&2
  exit 2
fi

if [[ -f "$TARGET" && "$TARGET" != *.py ]]; then
  printf 'Target file must use the .py extension: %s\n' "$TARGET" >&2
  exit 2
fi

pyright --outputjson "$TARGET" 2>/dev/null |
  jq -r '
.generalDiagnostics
| if length == 0 then
    "No issues."
  else
    group_by(.file)[]
    | (.[0].file | split("/") | last),
      (
        .[]
        | "\(.range.start.line + 1)\t|\t\(.message)"
      )
  end
'

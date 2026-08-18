#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  printf 'Usage: %s <python-file-or-directory>\n' "$0" >&2
  exit 2
fi

TARGET="$1"

if [ ! -f "$TARGET" ] && [ ! -d "$TARGET" ]; then
  printf 'Target does not exist: %s\n' "$TARGET" >&2
  exit 2
fi

if [ -f "$TARGET" ]; then
  case "$TARGET" in
    *.py) ;;
    *)
      printf 'Target file must use the .py extension: %s\n' "$TARGET" >&2
      exit 2
      ;;
  esac
fi

RESULT=$(mktemp)
trap 'rm -f "$RESULT"' EXIT HUP INT TERM

if ! pyright --outputjson "$TARGET" > "$RESULT" 2>/dev/null; then
  jq -r '
.generalDiagnostics[]?
| "\(.file):\(.range.start.line + 1): \(.message)"
' "$RESULT" >&2
  exit 1
fi

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
  ' "$RESULT"

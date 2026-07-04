#!/usr/bin/env bash
set -euo pipefail

TARGET="$1"
TARGET_ABS=$(realpath "$TARGET")

# 1. Xác định project root
PROJECT_ROOT=$(dirname "$TARGET_ABS")
while [[ "$PROJECT_ROOT" != "/" ]]; do
  if [[ -f "$PROJECT_ROOT/pyproject.toml" ||
    -f "$PROJECT_ROOT/basedpyrightconfig.json" ||
    -f "$PROJECT_ROOT/pyrightconfig.json" ||
    -d "$PROJECT_ROOT/.git" ]]; then
    break
  fi
  PROJECT_ROOT=$(dirname "$PROJECT_ROOT")
done

if [[ "$PROJECT_ROOT" == "/" ]]; then
  PROJECT_ROOT="."
fi

# 2. Thực thi (Đã bỏ --level strict để tránh crash)
basedpyright -p "$PROJECT_ROOT" --outputjson "$TARGET_ABS" 2>/dev/null |
  jq -r '
.generalDiagnostics as $d
| if ($d|length)==0 then
    "No issues."
  else
    ($d[0].file | split("/") | last),
    (
      $d[]
      | "\(.range.start.line + 1)\t|\t\(.message)"
    )
  end
'

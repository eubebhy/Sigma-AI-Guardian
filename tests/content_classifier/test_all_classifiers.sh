#!/usr/bin/env bash

set -u

levels=(xlow low mid strict xstrict)
log_dir="tests/content_classifier"
cpu_count="$(nproc)"

mkdir -p "$log_dir"

pids=()
failed=0

for i in "${!levels[@]}"; do
  level="${levels[$i]}"
  cpu=$((i % cpu_count))
  log_file="$log_dir/log_${level}.txt"

  {
    echo "========================================"
    echo "Strict level: $level"
    echo "CPU core: $cpu"
    echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================"
    echo

    taskset -c "$cpu" \
      .pyvenv/bin/python3 \
      tests/content_classifier/test_all_classifiers.py \
      -an 100 \
      --strict-level "$level" \
      -p random

    exit_code=$?

    echo
    echo "========================================"
    echo "Finished: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Exit code: $exit_code"
    echo "========================================"

    exit "$exit_code"
  } >"$log_file" 2>&1 &

  pids+=("$!")
done

for i in "${!pids[@]}"; do
  level="${levels[$i]}"

  if wait "${pids[$i]}"; then
    printf '[PASS] %s\n' "$level"
  else
    printf '[FAIL] %s — xem log_%s.txt\n' "$level" "$level"
    failed=1
  fi
done

exit "$failed"

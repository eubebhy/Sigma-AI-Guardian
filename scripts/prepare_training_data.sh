#!/bin/sh
set -eu

usage() {
    printf 'Usage: %s --training-dir DIR [--threshold N] [--dry-run]\n' "$0" >&2
    exit 2
}

training_dir=
threshold=15
dry_run=false

while [ "$#" -gt 0 ]; do
    case "$1" in
        --training-dir)
            [ "$#" -ge 2 ] || usage
            training_dir=$2
            shift 2
            ;;
        --threshold)
            [ "$#" -ge 2 ] || usage
            threshold=$2
            shift 2
            ;;
        --dry-run)
            dry_run=true
            shift
            ;;
        *)
            usage
            ;;
    esac
done

[ -n "$training_dir" ] || usage
[ -d "$training_dir" ] || {
    printf 'Training directory does not exist: %s\n' "$training_dir" >&2
    exit 2
}
case "$threshold" in
    ''|*[!0-9]*) usage ;;
esac
[ "$threshold" -gt 0 ] || usage

work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

for category_dir in "$training_dir"/*; do
    [ -d "$category_dir" ] || continue
    category=$(basename "$category_dir")
    merged_file="$work_dir/${category}.merged"
    short_file="$work_dir/short_${category}.txt"
    long_file="$work_dir/long_${category}.txt"
    : > "$merged_file"

    for source_file in "$category_dir"/*; do
        [ -f "$source_file" ] || continue
        while IFS= read -r line || [ -n "$line" ]; do
            trimmed=$(printf '%s' "$line" | tr '\t\r\n' '   ' | \
                sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            [ -n "$trimmed" ] && printf '%s\n' "$trimmed" >> "$merged_file"
        done < "$source_file"
    done

    LC_ALL=C sort -f -u "$merged_file" | while IFS= read -r line; do
        length=$(printf '%s' "$line" | wc -m | tr -d ' ')
        if [ "$length" -lt "$threshold" ]; then
            printf '%s\n' "$line" >> "$short_file"
        else
            printf '%s\n' "$line" >> "$long_file"
        fi
    done
    : >> "$short_file"
    : >> "$long_file"

    short_count=$(wc -l < "$short_file" | tr -d ' ')
    long_count=$(wc -l < "$long_file" | tr -d ' ')
    printf '%s: short=%s long=%s\n' "$category" "$short_count" "$long_count"
    [ "$dry_run" = true ] && continue

    for source_file in "$category_dir"/*; do
        [ -f "$source_file" ] && rm -f "$source_file"
    done
    mv "$short_file" "$category_dir/short_${category}.txt"
    mv "$long_file" "$category_dir/long_${category}.txt"
done

#!/bin/bash
# Keep a role journal small. Costs no tokens. Run from the workspace root.
#   journal-archive.sh <role> --list   print the day files due for archive (nothing = not due yet)
#   journal-archive.sh <role>          move those files to journal/archive/YYMM/
# Due when the role has more than JOURNAL_MAX_DAYS day files; the newest JOURNAL_KEEP_DAYS stay.
# Compact the listed files into journal/memory.md first (team operating model §8), then archive.
set -euo pipefail
export LC_ALL=C
ROLE="${1:-}"
MAX="${JOURNAL_MAX_DAYS:-7}"
KEEP="${JOURNAL_KEEP_DAYS:-2}"
[[ "$ROLE" =~ ^[a-z][a-z-]*$ ]] || { echo "usage: $0 <role> [--list]" >&2; exit 2; }
DIR="team/roles/$ROLE/journal"
[ -d "$DIR" ] || { echo "no journal: $DIR" >&2; exit 2; }

mapfile -t DAYS < <(find "$DIR" -maxdepth 1 -name '[0-9][0-9][0-9][0-9][0-9][0-9].md' -printf '%f\n' | sort)
[ "${#DAYS[@]}" -gt "$MAX" ] || exit 0
DUE=("${DAYS[@]:0:${#DAYS[@]}-KEEP}")

if [ "${2:-}" = "--list" ]; then
  printf "$DIR/%s\n" "${DUE[@]}"
  exit 0
fi
exec 9>"$DIR/.archive.lock"
flock -n 9 || { echo "another agent is archiving $ROLE" >&2; exit 1; }
for f in "${DUE[@]}"; do
  dest="$DIR/archive/${f:0:4}"
  mkdir -p "$dest"
  mv "$DIR/$f" "$dest/$f"
done
echo "archived ${#DUE[@]} files from $DIR"

#!/bin/bash
# Run one heavy command (docker build, a large test suite, a package install) under this machine's limit. Costs no tokens.
#   heavy.sh <command> [args...]        run from the workspace root; exits with the command's exit code
# One heavy job runs at a time. "heavySlots" in team/team.local.json (capacity.heavySlots, default 1) allows more:
# a slot after the first is used only while capacity-check.sh says GREEN. A job that finds no slot waits.
# The locks are per machine and per user (TEAM_LOCK_DIR to change), so every workspace on the machine shares them.
set -u
[ $# -gt 0 ] || { echo "usage: heavy.sh <command> [args...]" >&2; exit 2; }
TOOLS="$(cd "$(dirname "$0")" && pwd)"
SLOTS=$(python3 - "${TEAM_LOCAL:-team/team.local.json}" <<'PY'
import json, sys
try:
    print(max(1, int(json.load(open(sys.argv[1])).get('capacity', {}).get('heavySlots', 1))))
except (OSError, ValueError):
    print(1)
PY
)
DIR="${TEAM_LOCK_DIR:-/tmp/team-heavy-$(id -u)}"
mkdir -p "$DIR"
while true; do
  for i in $(seq 1 "$SLOTS"); do
    if [ "$i" -gt 1 ]; then  # an extra slot needs room on the machine
      [ "$("$TOOLS/capacity-check.sh" | awk '{print $2}')" = GREEN ] || break
    fi
    exec 9>"$DIR/slot-$i.lock"
    if flock -n 9; then
      "$@" 9>&-   # the command does not inherit the lock: a process it leaves behind cannot hold the slot
      exit $?
    fi
    exec 9>&-
  done
  sleep 5
done

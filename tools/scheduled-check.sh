#!/bin/bash
# Scheduled check: wakes a headless Product Owner only when work is waiting. Costs no tokens when idle.
# Run from cron in the workspace root, e.g. every 30 minutes:
#   */30 * * * * cd /path/to/workspace && .team/tools/scheduled-check.sh >> team/scheduled.out 2>&1
# Work is waiting when: a ticket is in triage, or a source's "check" command prints anything (CI results come this way).
# Resolved tickets alone do not wake it: they wait for the owner's GO or a release result, which arrives as a signal.
# Skips when capacity is RED, when the previous run is still going, or when schedule.enabled is false
# in team/team.local.json. Tools the headless PO may use: schedule.allowedTools (the owner's choice).
set -uo pipefail
export LC_ALL=C
LOCAL="team/team.local.json"
CFG="team/team.config.json"
[ -f "$CFG" ] || { echo "run from the workspace root" >&2; exit 2; }

read -r ENABLED ALLOWED < <(python3 - "$LOCAL" <<'PY'
import json, sys
try: s = json.load(open(sys.argv[1])).get('schedule', {})
except OSError: s = {}
print(str(s.get('enabled', False)).lower(), ','.join(s.get('allowedTools', [])) or '-')
PY
)
[ "$ENABLED" = "true" ] || exit 0

exec 9>team/.scheduled.lock
flock -n 9 || { echo "$(date +%H:%M) previous run still going"; exit 0; }

CAP=$(.team/tools/capacity-check.sh)
case "$CAP" in *" RED "*) echo "$CAP skip"; exit 0;; esac

TRIAGE=$(.team/tools/ticket.py list --state triage 2>/dev/null | grep -c .)
RESOLVED=$(.team/tools/ticket.py list --state resolved 2>/dev/null | grep -c .)
# Each source may have a "check" command: a cheap script that prints a line only when something is new.
SIGNALS=$(python3 - "$CFG" <<'PY'
import json, subprocess, sys
for s in json.load(open(sys.argv[1])).get('sources', []):
    if s.get('check'):
        out = subprocess.run(s['check'], shell=True, capture_output=True, text=True, timeout=120).stdout.strip()
        if out:
            for line in out.splitlines()[:20]:
                print(f"{s['name']}: {line}")
PY
)
NSIG=$(printf '%s' "$SIGNALS" | grep -c .)

if [ "$TRIAGE" -eq 0 ] && [ "$NSIG" -eq 0 ]; then
  echo "$(date +%H:%M) idle"
  exit 0
fi
echo "$CAP triage=$TRIAGE resolved=$RESOLVED signals=$NSIG: starting the PO"

PROMPT="Scheduled check: the owner is not here. You are the Product Owner; follow CLAUDE.md and the team rules, and .team/docs/work-loop.md for a scheduled run.
Waiting: $TRIAGE ticket(s) in triage, $RESOLVED resolved. New signals:
${SIGNALS:-none}
Do only what needs no owner: hire an Observer for the signals, triage tickets, start or continue accepted work within capacity and the ceiling. Anything needing the owner (new scope, GO to merge, a task past its retry limit) goes to the board as a question and its ticket to waiting. Never merge, push or tag without the owner's GO recorded on the board. Stop when nothing is left that you can do alone; write your log and journal entries."

ARGS=(-p "$PROMPT")
[ "$ALLOWED" != "-" ] && ARGS+=(--allowedTools "$ALLOWED")
claude "${ARGS[@]}"

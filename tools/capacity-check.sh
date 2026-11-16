#!/bin/bash
# Team capacity check. Costs no tokens: prints one status line.
# GREEN = may hire; YELLOW = no new hires, capped runs only; RED = stop every run.
# Limits come from team/team.local.json (capacity.*); run from the workspace root or set TEAM_LOCAL.
# Open agents: roster rows (team/status/roster.md, or ROSTER) whose state starts with running or parked, against ceiling in team/team.config.json (or TEAM_CONFIG).
# --parked-expired prints each parked row older than PARK_TTL_MIN (default 60), one line each, so the PO can stop it.
# --json prints the same numbers as one JSON object, for resource-lease.py.
export LC_ALL=C
CFG="${TEAM_LOCAL:-team/team.local.json}"
read -r MINA STOPA MAXL STOPD < <(python3 - "$CFG" <<'PY'
import json,sys
try: c=json.load(open(sys.argv[1])).get('capacity',{})
except OSError: c={}
print(c.get('minAvailGb',8),c.get('stopAvailGb',6),c.get('maxLoad5',12),int(c.get('stopDiskPct',85)))
PY
)
L=$(awk '{print $2}' /proc/loadavg)
D=$(df / | awk 'NR==2{print $5+0}')
A=$(free -m | awk '/Mem/{printf "%.1f", $7/1024}')
SW=$(free -m | awk '/Swap/{ if($2>0) printf "%.0f", $3/$2*100; else print 0}')
# Host out-of-memory only: a container hitting its own limit logs "Memory cgroup out of memory" and is not a host shortage.
OOM=$(journalctl -k --since -6min 2>/dev/null | grep -i "out of memory" | grep -vci "memory cgroup")
ROSTER="${ROSTER:-team/status/roster.md}"
PARK_TTL_MIN="${PARK_TTL_MIN:-60}"
# Roster rows: "name|state". A state "parked (since HH:MM)" older than the limit is expired (a time later than now means yesterday).
rows() { [ -f "$ROSTER" ] && awk -F'|' 'NR>2 && NF>=6 && $2!~/^ *-+ *$/ {gsub(/^ +| +$/,"",$2); gsub(/^ +| +$/,"",$6); print $2"|"$6}' "$ROSTER"; }
if [ "${1:-}" = "--parked-expired" ]; then
  NOW=$(( 10#$(date +%H)*60 + 10#$(date +%M) ))
  rows | while IFS='|' read -r N S; do
    case "$S" in parked*) T=$(echo "$S" | grep -oE '[0-9]{1,2}:[0-9]{2}' | head -1); [ -n "$T" ] || continue
      M=$(( 10#${T%:*}*60 + 10#${T#*:} )); AGE=$(( NOW - M )); [ "$AGE" -ge 0 ] || AGE=$(( AGE + 1440 ))
      [ "$AGE" -ge "$PARK_TTL_MIN" ] && echo "$N $S age=${AGE}min limit=${PARK_TTL_MIN}min";; esac
  done
  exit 0
fi
NAG=$(rows | awk -F'|' '$2~/^(running|parked)/{n++} END{print n+0}')
CEIL=$(python3 - "${TEAM_CONFIG:-team/team.config.json}" <<'PY'
import json,sys
try: print(int(json.load(open(sys.argv[1])).get('ceiling',2)))
except (OSError,ValueError): print(2)
PY
)
HEAVY=$(pgrep -fc 'jest|vitest|docker build')
ST=GREEN
awk -v l="$L" -v m="$MAXL" 'BEGIN{exit !(l<m)}' || ST=YELLOW
awk -v a="$A" -v m="$MINA" 'BEGIN{exit !(a>m)}' || ST=YELLOW
{ awk -v a="$A" -v m="$STOPA" 'BEGIN{exit !(a<m)}' || [ "$D" -ge "$STOPD" ] || [ "$OOM" -ne 0 ]; } && ST=RED
if [ "$NAG" -gt "$CEIL" ]; then ST=RED; elif [ "$NAG" -eq "$CEIL" ] && [ "$ST" = GREEN ]; then ST=YELLOW; fi
WARN=""; [ "$SW" -lt 80 ] || WARN=" WARN:swap"
if [ "${1:-}" = "--json" ]; then  # for resource-lease.py, locally or over ssh
  T=$(free -m | awk '/Mem/{printf "%.1f", $2/1024}')
  echo "{\"status\":\"$ST\",\"load5\":$L,\"availGb\":$A,\"totalGb\":$T,\"cores\":$(nproc),\"disk\":$D,\"oom\":$OOM,\"heavy\":$HEAVY,\"agents\":$NAG,\"ceiling\":$CEIL,\"minAvailGb\":$MINA,\"maxLoad5\":$MAXL}"
  exit 0
fi
echo "$(date +%H:%M) $ST load5=$L availG=$A disk=$D% swap=$SW% oom6m=$OOM heavy=$HEAVY agents=$NAG/$CEIL$WARN"

#!/bin/bash
# Team capacity check. Costs no tokens: prints one status line.
# GREEN = may hire; YELLOW = no new hires, capped runs only; RED = stop every run.
# Limits come from team/team.local.json (capacity.*); run from the workspace root or set TEAM_LOCAL.
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
HEAVY=$(pgrep -fc 'jest|vitest|docker build')
ST=GREEN
awk -v l="$L" -v m="$MAXL" 'BEGIN{exit !(l<m)}' || ST=YELLOW
awk -v a="$A" -v m="$MINA" 'BEGIN{exit !(a>m)}' || ST=YELLOW
{ awk -v a="$A" -v m="$STOPA" 'BEGIN{exit !(a<m)}' || [ "$D" -ge "$STOPD" ] || [ "$OOM" -ne 0 ]; } && ST=RED
WARN=""; [ "$SW" -lt 80 ] || WARN=" WARN:swap"
echo "$(date +%H:%M) $ST load5=$L availG=$A disk=$D% swap=$SW% oom6m=$OOM heavy=$HEAVY$WARN"

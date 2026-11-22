#!/bin/bash
# Team capacity check. Costs no tokens: prints one status line.
# GREEN = may hire; YELLOW = no new hires, capped runs only; RED = stop every run.
# Limits come from team/team.local.json (capacity.*); run from the workspace root or set TEAM_LOCAL.
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
# Heavy jobs: one per job. Count a jest/vitest/next or docker-build process only when its parent is not one too
# (workers and re-spawned children are skipped); a shell that only mentions the words is skipped.
# Counted: jest, vitest and next started through node (npx, npm, pnpm, node_modules/.bin or the package path), and
# docker build, docker buildx build, docker compose build. Not counted: Yarn PnP, and tools started without node.
HEAVY=$(ps -eo pid=,ppid=,args= | awk '
  { pid=$1; pp[pid]=$2; $1=""; $2=""; a[pid]=substr($0,3) }
  function heavy(s) { return s ~ /^[^ ]*node .*\/(\.bin\/(\.\.\/)?)?(jest|vitest|next)(\/[^ ]*)?( |$)/ || s ~ /^([^ ]*\/)?docker(-compose)? (buildx |compose )?build( |$)/ }
  END { n=0; for (p in a) if (heavy(a[p]) && !heavy(a[pp[p]])) n++; print n }')
ST=GREEN
awk -v l="$L" -v m="$MAXL" 'BEGIN{exit !(l<m)}' || ST=YELLOW
awk -v a="$A" -v m="$MINA" 'BEGIN{exit !(a>m)}' || ST=YELLOW
{ awk -v a="$A" -v m="$STOPA" 'BEGIN{exit !(a<m)}' || [ "$D" -ge "$STOPD" ] || [ "$OOM" -ne 0 ]; } && ST=RED
WARN=""; [ "$SW" -lt 80 ] || WARN=" WARN:swap"
if [ "${1:-}" = "--json" ]; then  # for resource-lease.py, locally or over ssh
  T=$(free -m | awk '/Mem/{printf "%.1f", $2/1024}')
  echo "{\"status\":\"$ST\",\"load5\":$L,\"availGb\":$A,\"totalGb\":$T,\"cores\":$(nproc),\"disk\":$D,\"oom\":$OOM,\"heavy\":$HEAVY,\"minAvailGb\":$MINA,\"maxLoad5\":$MAXL}"
  exit 0
fi
echo "$(date +%H:%M) $ST load5=$L availG=$A disk=$D% swap=$SW% oom6m=$OOM heavy=$HEAVY$WARN"

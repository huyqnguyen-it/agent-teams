#!/bin/bash
# Join a machine to the team as a worker. Costs no tokens. Run from the workspace root.
#   On the new machine:   host-join.sh [--cli claude|codex|cursor] [--model M]
#       checks it can work (CLI, git identity, team folder, capacity), saves "worker" in its team/team.local.json,
#       and prints the command to run on the main machine.
#   On the main machine:  host-join.sh add NAME SSH PATH [--max N]
#       runs the check on that machine over ssh and adds or updates it in team/team.local.json "hosts".
#   host-join.sh check --json    the check alone (used by "add")
# The owner signs the CLI in on each machine; this script never handles credentials.
set -u
export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$PATH"
TOOLS="$(cd "$(dirname "$0")" && pwd)"
LOCAL="${TEAM_LOCAL:-team/team.local.json}"

cli_bin() { case "$1" in claude) echo claude ;; codex) echo codex ;; cursor) echo cursor-agent ;; *) echo "$1" ;; esac; }

# One JSON line: ok, cli, problems. Each problem is a short reason the machine cannot take work yet.
check() {
  local cli problems=()
  cli=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('worker',{}).get('cli','claude'))" "$LOCAL" 2>/dev/null || echo claude)
  command -v "$(cli_bin "$cli")" >/dev/null || problems+=("$(cli_bin "$cli") not installed")
  [ -n "$(git config user.name)" ] && [ -n "$(git config user.email)" ] || problems+=("no git identity")
  [ -x "$TOOLS/worker-run.sh" ] || problems+=("no .team/tools/worker-run.sh")
  [ -d team/roles ] || problems+=("no team/ here: run .team/init.sh --yes")
  local cap; cap=$("$TOOLS/capacity-check.sh" --json 2>/dev/null) || problems+=("capacity-check failed")
  python3 - "$cli" "$cap" "${problems[@]+"${problems[@]}"}" <<'PY'
import json, sys
cli, cap, problems = sys.argv[1], sys.argv[2], sys.argv[3:]
try:
    status = json.loads(cap)['status']
except (ValueError, KeyError):
    status = 'RED'
print(json.dumps({'ok': not problems, 'cli': cli, 'status': status, 'problems': problems}))
PY
}

join_here() {
  local cli=claude model=""
  while [ $# -gt 0 ]; do case "$1" in --cli) cli="$2"; shift ;; --model) model="$2"; shift ;; esac; shift; done
  python3 - "$LOCAL" "$cli" "$model" <<'PY'
import json, pathlib, sys
path, cli, model = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
data = json.loads(path.read_text()) if path.exists() else {}
w = data.setdefault('worker', {})
w['cli'] = cli
if model:
    w['model'] = model
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2) + '\n')
PY
  local result; result=$(check)
  echo "$result"
  if python3 -c "import json,sys; sys.exit(not json.loads(sys.argv[1])['ok'])" "$result"; then
    echo "Ready. On the main machine run:"
    echo "  .team/tools/host-join.sh add $(hostname -s) <ssh name of this machine> $(pwd)"
  else
    echo "Fix the problems above, then run this again."; exit 1
  fi
}

add_host() {
  local name="${1:-}" ssh="${2:-}" path="${3:-}" max=""
  [ -n "$path" ] || { echo "usage: host-join.sh add NAME SSH PATH [--max N]"; exit 3; }
  [ "${4:-}" = "--max" ] && max="${5:-}"
  local result
  result=$(ssh -o BatchMode=yes -o ConnectTimeout=5 "$ssh" "cd $path && .team/tools/host-join.sh check --json") \
    || { echo "cannot run the check on $ssh: test 'ssh $ssh' and the path $path"; exit 1; }
  echo "$result"
  python3 - "$LOCAL" "$name" "$ssh" "$path" "$max" "$result" <<'PY'
import json, pathlib, sys
path, name, ssh, wpath, max_, result = sys.argv[1:]
r = json.loads(result)
if not r['ok']:
    sys.exit(f"{name} is not ready: " + '; '.join(r['problems']))
p = pathlib.Path(path)
data = json.loads(p.read_text()) if p.exists() else {}
old = next((h for h in data.get('hosts', []) if h.get('name') == name), {})
hosts = [h for h in data.get('hosts', []) if h.get('name') != name]
host = old | {'name': name, 'ssh': ssh, 'path': wpath, 'use': ['exec', 'worker'], 'cli': r['cli']}  # keeps the owner's other settings, such as maxAgents
if max_:
    host['maxAgents'] = int(max_)
data['hosts'] = hosts + [host]
p.write_text(json.dumps(data, indent=2) + '\n')
print(f"added {name} ({r['cli']}, now {r['status']}): check with .team/tools/resource-lease.py status")
PY
}

case "${1:-}" in
  check) check ;;
  add) shift; add_host "$@" ;;
  *) join_here "$@" ;;
esac

#!/bin/bash
# Run one brief headless on this machine with its own agent CLI and account, then exit. Costs no tokens itself.
#   worker-run.sh ROLE BRIEF_FILE        run from the workspace root (the PO runs it over ssh)
# The CLI and its caps come from "worker" in this machine's team/team.local.json:
#   { "cli": "claude|codex|cursor", "cmd": "", "model": "", "maxTurns": 40, "maxBudgetUsd": 2,
#     "timeoutMin": 20, "allowedTools": ["Bash(git add:*)", ...] }
# "cmd" overrides the built-in command for any other CLI: {brief} is replaced by the brief file path.
# The brief is sent with templates/worker-rules.md in front, because only Claude Code runs the team hooks.
# Exit: the CLI's exit code; 124 = timeout; 3 = bad setup.
set -u
ROLE="${1:-}"; BRIEF="${2:-}"
[ -n "$ROLE" ] && [ -f "$BRIEF" ] || { echo "usage: worker-run.sh ROLE BRIEF_FILE (from the workspace root)"; exit 3; }
TEAM="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$PATH"  # a plain 'ssh host cmd' does not load the login PATH

# Read the worker settings as shell-safe lines: CLI, CMD, MODEL, TURNS, BUDGET, MINUTES, then one allowed tool per line.
mapfile -t CFG < <(python3 - "${TEAM_LOCAL:-team/team.local.json}" <<'PY'
import json, sys
try:
    w = json.load(open(sys.argv[1])).get('worker', {})
except (OSError, ValueError):
    w = {}
for v in (w.get('cli', 'claude'), w.get('cmd', ''), w.get('model', ''), w.get('maxTurns', 40),
          w.get('maxBudgetUsd', 2), w.get('timeoutMin', 20)):
    print(v)
for t in w.get('allowedTools', ["Bash(git switch:*)", "Bash(git add:*)", "Bash(git commit:*)", "Bash(date:*)"]):
    print(t)
PY
)
CLI="${CFG[0]}"; CMD="${CFG[1]}"; MODEL="${CFG[2]}"; TURNS="${CFG[3]}"; BUDGET="${CFG[4]}"; MINUTES="${CFG[5]}"
TOOLS=("${CFG[@]:6}")

PROMPT_FILE="$(mktemp)"; trap 'rm -f "$PROMPT_FILE"' EXIT
cat "$TEAM/templates/worker-rules.md" "$BRIEF" > "$PROMPT_FILE"
PROMPT="$(cat "$PROMPT_FILE")"
export TEAM_ROLE="$ROLE"  # Claude Code hooks on this machine treat the run as a team agent

if [ -n "$CMD" ]; then
  RUN=(bash -c "${CMD//\{brief\}/$PROMPT_FILE}")
else
  case "$CLI" in
    claude) RUN=(claude -p "$PROMPT" --max-turns "$TURNS" --max-budget-usd "$BUDGET" --permission-mode acceptEdits
                 --output-format json --allowedTools "${TOOLS[@]}")
            [ -n "$MODEL" ] && RUN+=(--model "$MODEL") ;;
    codex)  RUN=(codex exec --sandbox workspace-write)
            [ -n "$MODEL" ] && RUN+=(-m "$MODEL"); RUN+=("$PROMPT") ;;
    cursor) RUN=(cursor-agent -p --output-format text)
            [ -n "$MODEL" ] && RUN+=(--model "$MODEL"); RUN+=("$PROMPT") ;;
    *) echo "unknown cli '$CLI': set worker.cmd in team/team.local.json"; exit 3 ;;
  esac
  command -v "${RUN[0]}" >/dev/null || { echo "${RUN[0]} not found on this machine (PATH=$PATH)"; exit 3; }
fi

LABEL="$CLI"; [ -n "$CMD" ] && LABEL=custom
echo "$(date +%H:%M) worker-run $ROLE cli=$LABEL timeout=${MINUTES}m"
timeout "${MINUTES}m" "${RUN[@]}"
CODE=$?
echo "$(date +%H:%M) worker-run $ROLE exit=$CODE branch=$(git branch --show-current 2>/dev/null)"
exit $CODE

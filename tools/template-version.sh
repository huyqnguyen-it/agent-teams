#!/bin/bash
# Print the template version this workspace uses and the newest release. Costs no tokens.
#   template-version.sh            from the workspace root (or anywhere: it reads its own clone)
# Exit: 0 up to date or cannot tell, 1 a newer release exists (update: git -C .team checkout <tag>, then .team/init.sh).
set -u
TPL="$(cd "$(dirname "$0")/.." && pwd -P)"
# Only when .team is its own clone: otherwise git would answer for the workspace repository.
[ "$(git -C "$TPL" rev-parse --show-toplevel 2>/dev/null)" = "$TPL" ] || { echo "template unknown (.team is not a git clone)"; exit 0; }
HERE=$(git -C "$TPL" describe --tags --always 2>/dev/null || echo unknown)
NOTE=""
# No prompt and a short timeout: an agent runs this, and the remote may be out of reach.
GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND='ssh -oBatchMode=yes -oConnectTimeout=5' timeout 20 git -C "$TPL" fetch -q --tags 2>/dev/null \
  || NOTE=" (remote not reached: from the tags already here)"
# Release tags only (v1.2.3); a pre-release (v1.2.3-rc1) sorts before its release.
LATEST=$(git -C "$TPL" -c versionsort.suffix=- tag -l 'v[0-9]*' --sort=-v:refname | head -1)
[ -n "$LATEST" ] || { echo "template $HERE (no release tag here$NOTE)"; exit 0; }
if git -C "$TPL" merge-base --is-ancestor "$LATEST" HEAD 2>/dev/null; then
  echo "template $HERE: up to date (newest release $LATEST)$NOTE"
else
  echo "template $HERE: UPDATE to $LATEST$NOTE"
  exit 1
fi

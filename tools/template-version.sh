#!/bin/bash
# Print the template version this workspace uses and the newest release. Costs no tokens.
#   template-version.sh            from the workspace root (or anywhere: it reads its own clone)
# Exit: 0 up to date or cannot tell, 1 a newer release exists (update: git -C .team checkout <tag>, then .team/init.sh).
set -u
TPL="$(cd "$(dirname "$0")/.." && pwd)"
HERE=$(git -C "$TPL" describe --tags --always 2>/dev/null || echo unknown)
git -C "$TPL" fetch -q --tags 2>/dev/null || { echo "template $HERE (cannot reach the template remote: newest release unknown)"; exit 0; }
LATEST=$(git -C "$TPL" tag -l 'v*' --sort=-v:refname | head -1)
[ -n "$LATEST" ] || { echo "template $HERE (no release tag yet)"; exit 0; }
if git -C "$TPL" merge-base --is-ancestor "$LATEST" HEAD 2>/dev/null; then
  echo "template $HERE: up to date (newest release $LATEST)"
else
  echo "template $HERE: UPDATE to $LATEST"
  exit 1
fi

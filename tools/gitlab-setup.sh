#!/bin/bash
# GitLab access for the team, set by the owner in their own terminal (never through an agent or the chat).
# Asks for the GitLab URL and a personal access token with the read_api scope only, saves them to
# ~/.config/agent-team/gitlab.env (mode 600, outside every repository), and checks the connection.
# Run once per machine:  .team/tools/gitlab-setup.sh
set -euo pipefail
FILE="${GITLAB_ENV_FILE:-$HOME/.config/agent-team/gitlab.env}"
[ -t 0 ] || { echo "Run this in your own terminal: it asks for the token without showing it." >&2; exit 2; }

OLD_URL=""
[ -f "$FILE" ] && OLD_URL=$(sed -n 's/^GITLAB_URL=//p' "$FILE")
read -r -p "GitLab URL [${OLD_URL:-https://gitlab.com}]: " URL
URL="${URL:-${OLD_URL:-https://gitlab.com}}"
URL="${URL%/}"
read -r -s -p "Personal access token (read_api scope only; input hidden): " TOKEN; echo
[ -n "$TOKEN" ] || { echo "No token given: nothing changed." >&2; exit 2; }
read -r -p "CA certificate file for a self-signed GitLab (empty for none): " CA

mkdir -p "$(dirname "$FILE")"
chmod 700 "$(dirname "$FILE")"
umask 077
TMP="$FILE.new"
{ echo "GITLAB_URL=$URL"; echo "GITLAB_TOKEN=$TOKEN"; [ -n "$CA" ] && echo "SSL_CERT_FILE=$CA"; } > "$TMP"
unset TOKEN
if GITLAB_ENV_FILE="$TMP" "$(dirname "$0")/gitlab-pipelines.py" whoami; then
  mv "$TMP" "$FILE"
  echo "Saved to $FILE (only you can read it). Agents use it through gitlab-pipelines.py and never read it."
else
  rm -f "$TMP"
  echo "Not saved: check the URL, the token and its read_api scope, then run this again." >&2
  exit 1
fi

#!/bin/bash
# Set up the agent team in the current workspace. Safe to rerun: answers are kept, team data is never overwritten.
exec python3 "$(dirname "$0")/init.py" "$@"

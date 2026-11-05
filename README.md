# agent-team-claude-code

A reusable agent team for Claude Code: roles, rules, templates, tools and skills.

## Set up in a workspace

```bash
cd <workspace>
# the template lives on an internal GitLab; replace with your own mirror if you have one
git clone https://github.com/huyqnguyen-it/agent-teams.git .team
claude "Set up the team: follow .team/SETUP.md"
```

Claude reads the workspace, detects the stack, asks a few questions, and runs `init`. Needs Python 3. Rerun it any time: answers are kept and team data is never overwritten. Start a new Claude Code session afterwards, so the agents load.

Without Claude: `.team/init.sh` asks in the terminal, and `.team/init.sh --yes` takes the defaults.

## What it creates

| Path | Purpose | Git |
|---|---|---|
| `.team/` | This template: never edit it in a workspace | Ignored |
| `team/team.config.json` | Shared settings | Committed |
| `team/team.local.json` | This machine's limits | Ignored |
| `team/status/`, `team/roles/`, `team/skills/`, `team/tools/`, `team/log/` | Workspace team data | Committed, except handovers |
| `.claude/agents/`, `.claude/skills/` | Generated | Ignored |

## Update

`git -C .team pull`, then `.team/init.sh`.

## In this repository

| Path | Contents |
|---|---|
| `docs/team-operating-model.md` | The rules |
| `docs/multi-server.md` | Running the team on several machines |
| `docs/instruction-topology.md` | Which file tells which agent what, and which one wins |
| `roles/` | Role definitions |
| `templates/` | Brief, design review, plan-complete, work report, skill |
| `tools/` | `capacity-check.sh` |
| `skills/` | Generic skills: `md-guide-to-html`, `team-board` |

No secrets, internal hosts or project details belong here.

## Limits and what is untested

- Linux only: `init.py` and `tools/capacity-check.sh` use `/proc`, `free`, `pgrep`. The OOM check reads `journalctl -k`, which an ordinary user may not be allowed to read; then it reports 0.
- Needs Python 3; `md-guide-to-html` also needs the Python `markdown` package.
- The team board needs claude.ai access (Artifact tools); without it, the team runs with no board.
- Proven end to end only on a small Node project, headless (`claude -p`, sonnet): staffing, a build with tests, lead review, work log. See the report for the runs. Not run: the Architect, DevOps, Auditor, Tester and Data Specialist roles; FE Lead; several machines; the board skill; the interactive SETUP.md menus.
- In a headless run, `.claude/settings.json` rules are ignored until the workspace is trusted, and agents are denied any command not on `--allowedTools`; pass the list on the command line.
- `init` adds only `Bash(.team/tools/capacity-check.sh)` to `.claude/settings.json`. Git and test commands are not added: whether it may add them is the owner's decision.
- There are no tests for `init.py`. A skill removed from the template leaves a dangling link in `.claude/skills/` until deleted by hand.

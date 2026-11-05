# agent-team-claude-code

A reusable agent team for Claude Code: roles, rules, templates, tools and skills.

## Set up in a workspace

```bash
cd <workspace>
git clone https://github.com/huyqnguyen-it/agent-teams.git .team
.team/init.sh
```

`init.sh` asks for roles, repositories, models and capacity, suggesting limits from this machine. Add `--yes` for the defaults. Needs Python 3. Rerun it any time: answers are kept and team data is never overwritten. Start a new Claude Code session afterwards, so the agents load.

## What it creates

| Path | Purpose | Git |
|---|---|---|
| `.team/` | This template: never edit it in a workspace | Ignored |
| `team/team.config.json` | Shared settings | Committed |
| `team/team.local.json` | This machine's limits | Ignored |
| `team/status/`, `team/roles/`, `team/skills/`, `team/log/` | Workspace team data | Committed, except handovers |
| `.claude/agents/`, `.claude/skills/` | Generated | Ignored |

## Update

`git -C .team pull`, then `.team/init.sh`.

## In this repository

| Path | Contents |
|---|---|
| `docs/team-operating-model.md` | The rules |
| `roles/` | Role definitions |
| `templates/` | Brief, design review, plan-complete, work report, skill |
| `tools/` | `capacity-check.sh` |
| `skills/` | Generic skills |

No secrets, internal hosts or project details belong here.

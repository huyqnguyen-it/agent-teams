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
| `team/status/`, `team/tickets/`, `team/roles/`, `team/skills/`, `team/tools/`, `team/log/` | Workspace team data | Committed, except handovers |
| `.claude/agents/`, `.claude/skills/` | Generated | Ignored |
| `.gitattributes` | Merges `team/log/*.md` by keeping both sides | Committed |

## Update

`git -C .team pull`, then `.team/init.sh`.

## In this repository

| Path | Contents |
|---|---|
| `docs/team-operating-model.md` | The rules |
| `docs/work-loop.md` | How work goes round: who starts it, the owner's gates, retry limit, scheduled check |
| `docs/multi-server.md` | Running the team on several machines |
| `docs/instruction-topology.md` | Which file tells which agent what, and which one wins |
| `roles/` | Role definitions |
| `templates/` | Brief, design review, plan-complete, work report, journal entry, journal memory, skill |
| `tools/` | `capacity-check.sh`, `journal-archive.sh`, `ticket.py` (Markdown tickets, or the configured tracker), `scheduled-check.sh` (wakes the PO when work waits), `gitlab-pipelines.py` (GitLab CI results, read-only), `gitlab-setup.sh` (the owner saves the GitLab URL and token, once per machine), `resource-lease.py` (places and reserves each hire across hosts), `team-hooks.py` (Claude Code hooks that enforce team rules) |
| `skills/` | Generic skills: `md-guide-to-html`, `team-board` |

No secrets, internal hosts or project details belong here.

## Limits and what is untested

- Linux only: `init.py` and `tools/capacity-check.sh` use `/proc`, `free`, `pgrep`. The OOM check reads `journalctl -k`, which an ordinary user may not be allowed to read; then it reports 0.
- Needs Python 3; `md-guide-to-html` also needs the Python `markdown` package.
- The team board needs claude.ai access (Artifact tools); without it, the team runs with no board. A headless worker on a second machine did not have those tools (one signed-in VM).
- Proven end to end only on a small Node project, headless (`claude -p`, sonnet): staffing, a build with tests, lead review, work log. See the report for the runs. Not run: the Architect, DevOps, Auditor, Tester, Data Specialist and Observer roles; signal sources, tickets with a real provider (Markdown tickets were tested by script only); `gitlab-pipelines.py` against a real GitLab (tested with a stub server); the scheduled check with a real headless PO (tested only up to the start, with a stub); skill drafts and their acceptance; journal compaction; FE Lead; the board skill; the interactive SETUP.md menus.
- Several machines: communication proven on two 1 CPU, 2 GB VMs, headless, haiku, on a small Python repo: init on each, capacity check and tests over SSH, one worker per VM with its branch and log entry back on the main machine, a lead on one VM starting a worker on the other and merging its branch. Capacity was not tested. Not run: Remote Control sessions (`ListAgents`, `SendMessage`), `DOCKER_HOST=ssh://`, a shared git remote (branches moved by `git fetch` over SSH), the Resource Manager reading several hosts, a live board from a second machine, `flock` across work on two machines.
- In a headless run, `.claude/settings.json` rules are ignored until the workspace is trusted, and agents are denied any command not on `--allowedTools`; pass the list on the command line.
- `init` adds to `.claude/settings.json`: the team tools to `allow`; `deny` rules for secrets, `.team/` and ticket files; `attribution` with no AI lines; and the `team-hooks.py` hooks (team operating model §7). Git and test commands are not added: whether it may add them is the owner's decision.
- The `.env` deny rules also hide `.env.example`. Remove that rule from `.claude/settings.json` if agents need it.
- Learned resource estimates need samples: on the main machine the hooks take one a minute while agents work; other hosts are sampled only when `resource-lease.py` runs.
- There are no tests for `init.py`. A skill removed from the template leaves a dangling link in `.claude/skills/` until deleted by hand.

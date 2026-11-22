# Running the team on several machines

Use this when one machine is not enough. Local agents are light: tests, Docker stacks and builds are what run out of memory, so start with remote execution.

## When to use it

| Sign | Use |
|---|---|
| `capacity-check.sh` is often YELLOW or RED during tests or builds | Remote execution |
| You need more members working at once, and the local machine is full | Headless worker |
| A role needs to keep context on another machine | Remote session |
| A whole area should run separately, with its own lead and members | Department (later phase) |
| Several workspaces, accounts or machines to see and start from one board | Multica (`multica.md`) |

Each machine adds token cost. Moving work does not make it cheaper.

## Prepare a machine (once per machine)

The owner does these steps. Agents never set up credentials.

Each machine can use its own account and its own agent CLI: Claude Code (`claude`), Codex (`codex`) or Cursor (`cursor`). Any other CLI works through `worker.cmd`.

1. Install the agent CLI and sign in, with that machine's account (not needed for remote execution only).
2. Add SSH key access from the main machine, with a name in `~/.ssh/config`.
3. Clone the workspace repositories, and `.team/`, at the same relative paths.
4. Set a git identity there (`git config user.name`, `user.email`). A fresh machine has none, and a worker cannot commit without it.
5. Run `.team/init.sh --yes` there, so capacity limits suit that machine.
6. If it runs the scheduled check or a lead that tracks GitLab CI: run `.team/tools/gitlab-setup.sh` there, in a terminal on that machine (`SETUP.md`, GitLab CI). Use a token for that machine, so it can be revoked alone.
7. Join, on that machine, from the workspace root: `.team/tools/host-join.sh --cli codex [--model M]`. It checks the CLI, the git identity, `team/` and capacity, saves `worker` in that machine's `team/team.local.json`, and prints the next command.
8. Add, on the main machine: `.team/tools/host-join.sh add pc2 pc2 /home/me/workspace [--max 3]` (name, ssh name, absolute path on that machine). It runs the check over SSH and writes the host into `team/team.local.json`:

```json
{ "hosts": [
  { "name": "pc2", "ssh": "pc2", "path": "/home/me/workspace", "use": ["exec", "worker"], "cli": "codex", "maxAgents": 3 }
] }
```

`use` values: `exec`, `worker`, `session`. Only `worker` hosts take hires. `maxAgents` is a hard cap for that host (default: `capacity.maxAgents`); the real room is measured each time. Run `add` again after you change the CLI on that machine; it keeps your other settings.

9. Check it: `.team/tools/resource-lease.py status` on the main machine prints a line for every host, with its CLI. `unreachable` means SSH failed.

## Choose how to use it

### Remote execution: agents stay, heavy commands move

```bash
ssh pc2 'cd ~/workspace && git fetch && git switch <branch> && <test command>'
DOCKER_HOST=ssh://pc2 docker compose up -d
```

The code must be on that machine: push the feature branch first, with its plan and any docs the task needs.

### Headless worker: one task, then it exits

```bash
.team/tools/resource-lease.py reserve developer-3 developer [--cli codex]   # HIRE developer-3 on pc2 cli=codex ... (or WAIT)
scp brief.md pc2:workspace/brief-developer-3.md
ssh pc2 'cd ~/workspace && .team/tools/worker-run.sh developer brief-developer-3.md'; .team/tools/resource-lease.py release developer-3
```

- Reserve first and release after, in the same command, so a failed run still gives the room back. A lease left behind expires on its own.
- `worker-run.sh` reads `worker` in that machine's `team/team.local.json` (`cli`, `model`, `maxTurns`, `maxBudgetUsd`, `timeoutMin`, `allowedTools`, or `cmd`), puts `templates/worker-rules.md` in front of the brief, and runs the CLI under `timeout`. Exit 124 means the time ran out.
- It sets `TEAM_ROLE`, so a Claude Code worker's hooks treat the run as a team agent: it may push its feature branch, never main, tags or with force, and must write its log and journal entries.

| CLI | Command it runs | Limits |
|---|---|---|
| `claude` | `claude -p … --max-turns --max-budget-usd --permission-mode acceptEdits --allowedTools …` | Turns, budget, tool list, team hooks, timeout |
| `codex` | `codex exec --sandbox workspace-write [-m model] …` | Sandbox (writes only in the workspace; no network by default, so it cannot push), timeout |
| `cursor` | `cursor-agent -p --output-format text [--model model] …` | Cursor's own permission file in that workspace, timeout |
| other | `worker.cmd`, with `{brief}` as the prompt file path | Only what that CLI enforces, and the timeout |

- Only Claude Code runs the team hooks. On other CLIs, the rules in the brief, branch protection, a git token that can push only feature branches, and the lead's review are the gates.
- The code goes to the provider of that machine's CLI. Use only providers the owner allows for that repo.
- Each account has its own quota. A budget cap exists only on Claude Code: keep `timeoutMin` short on the others.
- Headless cannot ask for approval. List what it may run in `allowedTools`, and keep it tight. Never skip permissions.
- `Bash(x:*)` matches `x` followed by a space. `Bash(git fetch host:*)` does not match `git fetch host:repo`: write the full command as the rule.
- A rule matches the command as typed: `Bash(~/run.sh:*)` and `Bash(/home/ubuntu/run.sh:*)` are different rules. Tell the worker the exact form to use.
- A headless worker ignores `.claude/settings.json` until the workspace is trusted, so pass permissions on the command line.
- Commit messages carry no AI or co-author line: say so in the brief, as `templates/brief.md` does.
- A chained command (`a && b`, `a; b`) is denied unless every part is allowed. Tell the worker to run one command per call.
- The result is the worker's output and its branch. The worker pushes that branch to the shared remote. With no remote the worker can reach, fetch it from the machine you started it from: `git fetch pc2:workspace feat/x:feat/x`.

### A lead on another machine

A lead on one machine can start a worker on another with the same two commands, and take its branch back the same way. It needs SSH to that machine, and rules in its own `--allowedTools` for `scp`, `ssh` and `git fetch`. The names in `~/.ssh/config` belong to each machine: use an address that works from the lead's machine.

### Remote session: a role that keeps context

Start Claude Code with Remote Control on that machine, in `tmux`, on the same account (Claude Code only). It then appears in `ListAgents` and takes `SendMessage`. Another account cannot join this way: use a headless worker or a department.

## Team rules on several machines

| Rule | Detail |
|---|---|
| One gate | Only the PO starts agents, on any machine |
| Capacity per host | `resource-lease.py reserve` reads every host, reserves the room, and answers `HIRE developer-3 on pc2`. No agent spends tokens on placement |
| Roster | Fill the `Host` column |
| Files | No shared disk: work moves through git feature branches |
| Pushing | Members may push feature branches only. Tags and protected branches stay with the PO; branch protection enforces it |
| Locks | `flock` is per machine |
| Silence | A session can go quiet with no error: set a timeout, then check its branch and log |
| Secrets | Each machine holds its own. Nothing goes in `team/` or a brief. Do not mount the main machine's home on a worker machine: an agent there can read its credentials |
| Permissions | A denial on one machine is not routed through another |
| Work log | Each machine appends its entry on its branch; the lead merges it. `init` sets `team/log/*.md` to `merge=union`, so entries from two branches keep both, in no fixed order |
| Board | Only the PO's session writes it. A worker returns a question in its reply or on its branch, and the PO adds it. A headless worker on another machine does not have the Artifact tools |

## Questions from a worker on another machine

A worker has no board tools, so a machine with them relays. Tested on two VMs with an owner's answer.

1. The worker writes the question to a file on its branch, then stops.
2. The relay reads it and adds it to the board.
3. The relay reads the answer from the board, which wakes nobody, so it checks on a timer with a time limit.
4. The relay starts the next run with the answer in its brief. It never answers for the owner.

## Multipass test machines

An instance named `primary` mounts your whole home folder read-write at `~/Home`. Remove that before any agent runs there: `multipass umount primary`. Use another name for new instances.

## Check before relying on it

Run one small task end to end: brief, remote run, branch, lead review, log entry. Only then add more.

`worker-run.sh` and `host-join.sh` are tested with stub CLIs only. A real `codex` or `cursor-agent` run is not tested: check its flags on the first run.

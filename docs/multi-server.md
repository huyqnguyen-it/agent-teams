# Running the team on several machines

Use this when one machine is not enough. Local agents are light: tests, Docker stacks and builds are what run out of memory, so start with remote execution.

## When to use it

| Sign | Use |
|---|---|
| `capacity-check.sh` is often YELLOW or RED during tests or builds | Remote execution |
| You need more members working at once, and the local machine is full | Headless worker |
| A role needs to keep context on another machine | Remote session |
| A whole area should run separately, with its own lead and members | Department (later phase) |

Each machine adds token cost. Moving work does not make it cheaper.

## Prepare a machine (once per machine)

The owner does these steps. Agents never set up credentials.

1. Install Claude Code and sign in (not needed for remote execution only). A second account needs a seat or API key your plan allows.
2. Add SSH key access from the main machine, with a name in `~/.ssh/config`.
3. Clone the workspace repositories, and `.team/`, at the same relative paths.
4. Set a git identity there (`git config user.name`, `user.email`). A fresh machine has none, and a worker cannot commit without it.
5. Run `.team/init.sh --yes` there, so capacity limits suit that machine.
6. Add it to `team/team.local.json` on the main machine:

```json
{ "hosts": [
  { "name": "pc2", "ssh": "pc2", "path": "~/workspace", "use": ["exec", "worker"] }
] }
```

`use` values: `exec`, `worker`, `session`.

7. Check it: `ssh pc2 'cd ~/workspace && .team/tools/capacity-check.sh'`.

## Choose how to use it

### Remote execution: agents stay, heavy commands move

```bash
ssh pc2 'cd ~/workspace && git fetch && git switch <branch> && <test command>'
DOCKER_HOST=ssh://pc2 docker compose up -d
```

The code must be on that machine: push the feature branch first.

### Headless worker: one task, then it exits

```bash
scp brief.md pc2:brief.md
ssh pc2 'cd ~/workspace && timeout 280 ~/.local/bin/claude -p "$(cat ~/brief.md)" --model sonnet --max-budget-usd 2 --permission-mode acceptEdits --output-format json --allowedTools "Bash(git switch:*)" "Bash(git add:*)" "Bash(git commit:*)" "Bash(date:*)" "<test command rule>"'
```

- Use the full path: `~/.local/bin` is not on `PATH` in a plain `ssh host 'command'`.
- Always set a budget, and use `timeout` as well.
- Headless cannot ask for approval. List what it may run in `--allowedTools`, and keep it tight. Never skip permissions.
- `Bash(x:*)` matches `x` followed by a space. `Bash(git fetch host:*)` does not match `git fetch host:repo`: write the full command as the rule.
- A rule matches the command as typed: `Bash(~/run.sh:*)` and `Bash(/home/ubuntu/run.sh:*)` are different rules. Tell the worker the exact form to use.
- A headless worker ignores `.claude/settings.json` until the workspace is trusted, so pass permissions on the command line.
- Commit messages carry no AI or co-author line: say so in the brief, as `templates/brief.md` does.
- A chained command (`a && b`, `a; b`) is denied unless every part is allowed. Tell the worker to run one command per call.
- The result is the worker's output and its branch. The worker pushes that branch to the shared remote. With no remote the worker can reach, fetch it from the machine you started it from: `git fetch pc2:workspace feat/x:feat/x`.

### A lead on another machine

A lead on one machine can start a worker on another with the same two commands, and take its branch back the same way. It needs SSH to that machine, and rules in its own `--allowedTools` for `scp`, `ssh` and `git fetch`. The names in `~/.ssh/config` belong to each machine: use an address that works from the lead's machine.

### Remote session: a role that keeps context

Start Claude Code with Remote Control on that machine, in `tmux`, on the same account. It then appears in `ListAgents` and takes `SendMessage`. Another account cannot join this way: use a headless worker or a department.

## Team rules on several machines

| Rule | Detail |
|---|---|
| One gate | Only the PO starts agents, on any machine |
| Capacity per host | The Resource Manager reads each host's check, and answers `HIRE developer on pc2` |
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

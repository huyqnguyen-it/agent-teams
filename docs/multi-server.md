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
4. Run `.team/init.sh --yes` there, so capacity limits suit that machine.
5. Add it to `team/team.local.json` on the main machine:

```json
{ "hosts": [
  { "name": "pc2", "ssh": "pc2", "path": "~/workspace", "use": ["exec", "worker"] }
] }
```

`use` values: `exec`, `worker`, `session`.

6. Check it: `ssh pc2 'cd ~/workspace && .team/tools/capacity-check.sh'`.

## Choose how to use it

### Remote execution: agents stay, heavy commands move

```bash
ssh pc2 'cd ~/workspace && git fetch && git switch <branch> && <test command>'
DOCKER_HOST=ssh://pc2 docker compose up -d
```

The code must be on that machine: push the feature branch first.

### Headless worker: one task, then it exits

```bash
ssh pc2 'cd ~/workspace && claude -p "$(cat brief.md)" --model sonnet --max-budget-usd 2 --output-format json'
```

- Always set a budget, and use `timeout` as well.
- Headless cannot ask for approval. The owner sets what it may run in that machine's Claude Code settings, and keeps it tight. Never skip permissions.
- The worker pushes a feature branch; the result is its output and that branch.

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
| Secrets | Each machine holds its own. Nothing goes in `team/` or a brief |
| Permissions | A denial on one machine is not routed through another |
| Work log | Each machine appends its entry on its branch; the lead merges it |

## Check before relying on it

Run one small task end to end: brief, remote run, branch, lead review, log entry. Only then add more.

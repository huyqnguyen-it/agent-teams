# Set up the team in this workspace

You are Claude Code, setting up the agent team. Work from the workspace root. `.team/` is the template: never edit it.

## 1. Look before asking

Read, without changing anything:
- `team/team.config.json` and `team/team.local.json`, if they exist: this is a rerun, so use their values as defaults.
- `README.md`, `CLAUDE.md`, and the top-level folders.
- Stack files: `package.json`, `pnpm-lock.yaml`, `pyproject.toml`, `requirements.txt`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`, `*.csproj`, `Dockerfile`, `.gitlab-ci.yml`.

From these, work out the stack, frontend and backend folders, and the test, build and lint commands. Take commands only from what the files show; if unsure, leave one empty.

## 2. Ask the owner

Ask with your question tool, in one round. Offer what you found as the first option.

| Question | Saved as |
|---|---|
| Which roles? PO and Resource Manager are always on. Options: `architect`, `devops`, `fe-lead`, `be-lead` | `roles` |
| Repositories or folders for each lead | `repos` |
| Are the test, build and lint commands right? | `commands` |
| What may DevOps change? | `devopsPermissions` |
| Most agents running at once | `ceiling` |
| Team board URL, if any | `boardUrl` |

Keep default models unless the owner asks. Do not ask about capacity: step 4 suggests limits from this machine.

## 3. Write the settings

Copy the shape from `.team/team.config.example.json` into `team/team.config.json`, and put the answers in. Always list `product-owner` and `resource-manager` in `roles`. Put `boardUrl` in `team/team.local.json`, with the rest of that file as in `.team/team.local.example.json` but without `capacity`.

Never write secrets to these files.

## 4. Run

```bash
.team/init.sh --yes
```

It creates `team/`, generates `.claude/agents/`, links skills, updates `.gitignore` and `CLAUDE.md`, and suggests capacity limits. Reruns never overwrite team data.

## 5. Team board

If the owner wants a board and has none, follow `.team/skills/team-board/SKILL.md`, then save its URL as `boardUrl` in `team/team.local.json`. This needs claude.ai access: if the tools are missing, say so and continue without one.

## 6. GitLab CI

If the workspace has `.gitlab-ci.yml`, or the owner says it uses GitLab CI, connect the team to the pipeline results. Never ask for the token in the chat and never handle it yourself: whatever is pasted here stays in the session.

1. Check first: run `.team/tools/gitlab-pipelines.py whoami`. If it prints "connected as", skip to step 4.
2. Tell the owner, in these words or close to them:

   > The team reads pipeline results from GitLab with a personal access token that can only read. Please:
   > 1. In GitLab, open your avatar → **Edit profile** → **Access tokens** → **Add new token**.
   > 2. Name: `agent-team-<this machine>`. Expiry: a date you will renew (GitLab's limit is one year). Scope: **read_api** only, nothing else.
   > 3. Create it and copy the token (it starts with `glpat-`). GitLab shows it once.
   > 4. In **your own terminal** (not in this chat), in this workspace, run: `.team/tools/gitlab-setup.sh`
   >    It asks for the GitLab URL (for example `https://gitlab.example.com`), the token (hidden as you type), and a CA certificate file only if your GitLab uses a self-signed certificate. It checks the connection and saves both to `~/.config/agent-team/gitlab.env`, readable only by you.
   > 5. Tell me when it says "connected as".
   >
   > A project or group access token with `read_api` works too, and does not depend on one person's account.
3. Run `.team/tools/gitlab-pipelines.py whoami` again to confirm.
4. Ask which GitLab projects the team should follow (paths like `group/service`; offer the repositories you found), and add the source to `sources` in `team/team.config.json`:
   `{"name": "gitlab-ci", "kind": "ci", "check": ".team/tools/gitlab-pipelines.py check group/service-a group/web"}`
5. Run its `check` once: the first run records history and prints nothing; later runs print each finished pipeline once.

The token is per machine: every machine that runs the scheduled check or a lead repeats step 2 there.

## 7. More machines

If the owner plans to use more than one machine, point them to `.team/docs/multi-server.md`. Do not set up other machines yourself.

## 8. Report

Show the owner: roles, repositories, commands, capacity limits, the capacity check line, and the GitLab connection (the `whoami` line, or "not connected"). Then say: start a new Claude Code session so the agents load, and commit `team/`, `CLAUDE.md`, `.gitignore` and `.gitattributes`. Do not commit for them.

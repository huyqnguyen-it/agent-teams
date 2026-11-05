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

## 6. More machines

If the owner plans to use more than one machine, point them to `.team/docs/multi-server.md`. Do not set up other machines yourself.

## 7. Report

Show the owner: roles, repositories, commands, capacity limits, and the capacity check line. Then say: start a new Claude Code session so the agents load, and commit `team/`, `CLAUDE.md` and `.gitignore`. Do not commit for them.

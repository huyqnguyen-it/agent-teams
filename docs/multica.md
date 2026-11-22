# Multica as the control layer (advanced)

Use this when you run several workspaces, several accounts or several machines, and one terminal session is not enough to see and start the work. [Multica](https://github.com/multica-ai/multica) is a self-hostable board: you assign an issue to an agent, and a daemon on your machine starts the agent CLI for it.

Do not use it for one workspace on one machine. The team works without it.

## What each part does

| Job | Without Multica | With Multica |
|---|---|---|
| Rules, roles, gates, retry limit, design review | The team template | The team template (unchanged) |
| Who starts leads and members | The PO, after `resource-lease.py reserve` | The PO (unchanged) |
| Who starts the PO | The owner, in a terminal | Multica, when an issue is assigned to the PO agent |
| Owner's questions and GO | The team board | A comment on the issue; Multica's inbox |
| Seeing what a run did | The work log and the branch | The same, plus Multica's run log and cost |
| Several workspaces | One terminal session each | One PO agent each, on one board |

**One rule decides the shape: the whole team is one Multica agent, the PO.** Do not make each role a Multica agent. Multica starts an agent on every mention, so the PO would no longer be the only one that hires, and the capacity rules (team operating model §5) would not hold.

## Shape

```
              Multica server (board, issues, inbox)
                 |                |               |
        container: ws-a   container: ws-b   container: devops
        daemon + PO agent daemon + PO agent daemon + DevOps agent
        workspace ws-a    workspace ws-b    cluster access only
                 \________________/
                 worker pool (optional): members, over SSH
```

- **One container (or machine, or Unix user) per workspace.** Multica starts the agent CLI with permission prompts off and no sandbox, as the user that runs the daemon. The container is the boundary. Never run the daemon as your own user on your own machine.
- **One PO agent per workspace, one run at a time.** The team assumes one PO is the gate.
- **The worker pool stays as in `multi-server.md`.** The PO's container is the "main machine"; it hires members on the pool with `host-join.sh` and `worker-run.sh`.

## Set up

The owner does every step that handles a credential.

1. **Server.** Run Multica's `docker-compose.selfhost.yml` with a random `JWT_SECRET`. Set `DO_NOT_TRACK=1` to send no telemetry. Check that the port answers as Multica: `curl http://127.0.0.1:<port>/healthz` must return `{"status":"ok",...}`. Another service on the same port can answer first and give confusing login errors.
   - **Login codes.** Multica signs a user in with a code sent by email. With no mail server set (`RESEND_API_KEY` or `SMTP_HOST` in `.env`), the code is printed in the backend log, for the first user and for every member added later: `docker logs --since 10m multica-backend-1 2>&1 | grep "Verification code"`. Whoever reads that log can sign in as any user, so set a mail server before other people join.
   - **Sign-up.** It is open by default. After the accounts exist, set `ALLOW_SIGNUP=false` (or `ALLOWED_EMAILS`) in `.env` and recreate the backend.
2. **A container per workspace.** Install the agent CLI, `git`, Python 3 and the `multica` CLI. Run agents as a non-root user. Give the container a hard memory limit, so `free` inside shows the limit. Let it reach the Multica API, and nothing else it does not need.
3. **Credentials, in the container** (see the table below): the agent CLI's login, a Multica personal access token, a git key for this workspace's repositories only, and a GitLab API token if the team reads CI results.
4. **The workspace.** Clone it in the container, with submodules. If the workspace cannot be cloned (unpushed work, nested repositories), mount the folder instead; then the owner's own sessions and the container share one checkout, so do not run both on one repository at once.
5. **The team.** In the workspace: clone this template to `.team/` and run `.team/init.sh --yes`. Limits in `team/team.local.json` then fit the container.
6. **The daemon.** `multica login --token`, then run `multica daemon start --foreground --no-auto-update` as a service that restarts.
7. **Project and agent.** In Multica: a project for the workspace; the workspace folder added as a local directory in direct mode (`--type local_directory --execution-mode in_place`), which starts the PO in the workspace and runs one PO at a time; a PO agent on that container's runtime with `--max-concurrent-tasks 1`.
8. **Test.** Assign an issue that changes nothing: ask for the working directory, the first heading of the team rules, and the capacity check line.

### Instructions for the PO agent

```
You are the Product Owner of the <workspace> workspace. Work in <path>.
Rules: .team/docs/team-operating-model.md. Your role: team/roles/product-owner/profile.md.
Read team/roles/product-owner/handover.md and team/status/board.md first.
- The Multica issue is the owner's request. Handle it by the team rules.
- The owner is not at a terminal. Ask a decision, or ask for GO, as one comment on the issue
  with your recommendation, then stop. Never guess the owner's answer.
- The Artifact team board is not available here. Keep team/status/board.md current instead.
- Never push a protected branch or a tag without the owner's GO written in a comment on this issue.
- Before you stop: write your work log entry, then post a short result comment on the issue.
```

## Many accounts

| Credential | Where it lives | Notes |
|---|---|---|
| Agent CLI login | Each container or machine | Each may use a different account; each account has its own quota |
| Multica personal access token | Each container, in `~/.multica` after login | It acts as your account in every Multica workspace. Never copy a container after `multica login`: two daemons would share one identity |
| Git key | Each container | One key per container, with access to that workspace only, so one can be revoked alone |
| GitLab API token | Each container, in `~/.config/agent-team/gitlab.env` | The git key carries git only: CI results need this token. One per container, for that workspace's GitLab server, scope `read_api` only. The owner runs `.team/tools/gitlab-setup.sh` in the container; check with `gitlab-pipelines.py whoami` |
| Cluster access | The DevOps container only | See below |

An old GitLab has no `read_api` scope: its API accepts only the `api` scope, which can also write. There, create the token for a separate user with the Reporter role on the projects, so the token can read pipelines and nothing more.

Claude Code has two kinds of login:

| | Long-lived token (`claude setup-token`, `CLAUDE_CODE_OAUTH_TOKEN`) | Full login (`/login`) |
|---|---|---|
| Headless runs, which is how Multica starts the PO | Yes | Yes |
| Remote Control, claude.ai connectors, Artifact tools | No | Yes |
| Set up with no browser on that machine | Yes | No |

Use the long-lived token in PO containers. Multica can also hold a credential as an agent environment variable, but it stores the value as plain text in its database: keep high-value tokens in the container.

## Optional: a model router

By default each container holds its own agent login (the long-lived token above). That is the simple setup, and it is enough for one account.

Add a router only when one account's limit stops the team, or when roles must use different providers (several accounts, a cheaper provider, a model server of your own). A router such as 9router holds the accounts and gives every container one address and one key:

- In each container set `ANTHROPIC_BASE_URL` to the router and `ANTHROPIC_AUTH_TOKEN` to a router key, and remove the agent login. The other credentials (Multica, git, CI) stay.
- Give each container its own router key, so usage is visible per container and one key can be revoked alone.
- Keep the core roles (PO, leads, Architect) on one model family. Let only members fall back to a weaker model: set the fallback as `worker.model` of the worker host in `team.local.json`.
- The router is one more service every agent depends on, and it holds all the accounts: keep it off the open network, and keep the direct login as a way back.
- Check the terms of each account before you share it through a router.

Tried once: three containers through 9router with two accounts. A real switch at a limit was not observed.

## Many servers

- **Access from the LAN.** The server listens on localhost only. For other machines, put a proxy on the LAN address in front of it: WebSocket paths (`/ws`, `/collab`) go to the backend, the rest to the web app. Set `FRONTEND_ORIGIN` and `CORS_ALLOWED_ORIGINS` in `.env` to the address people open, or the backend refuses them. Without the proxy the pages load but live updates do not arrive.
- **A daemon needs only an outbound connection to the Multica server.** A machine you cannot reach by SSH can still take work. Put the server behind a reverse proxy with TLS for other machines; do not publish its ports directly.
- **A runtime is one machine plus one agent CLI.** An agent is bound to one runtime: put each PO agent on its own workspace's container.
- **A pool shared by two workspaces:** each PO keeps its own leases, so it does not see the other's hires. Set `maxAgents` low on that host, or give each workspace its own pool.
- **PO to PO:** one PO can ask another by mention on an issue. Use it for work between workspaces, not for capacity: each mention is a paid run, and two agents that answer each other do not stop on their own. Write the stop rule in the instructions.

## Leads as agents (pilot)

The PO stays the only Multica agent by default. A second shape puts the long-lived core roles on the board too:

- Each lead (and the Architect) is a Multica agent on the workspace's runtime, one run at a time, with `TEAM_ROLE=<role>` in its environment so the guard hook applies to it.
- A squad has the PO as leader and the leads as members. Assign an issue to the squad: the PO delegates by mention and stops; the lead's reply wakes the PO.
- A lead hires its own members inside its run, after `resource-lease.py reserve`. Members never become Multica agents: they are short-lived, and they are what the capacity rules must count.
- Cost: every reply of a lead starts a new PO run. Lead runs hold no lease; "one run at a time" per agent is their limit. With the workspace folder in direct mode, only one agent of the workspace works at a time.
- The owner still asks the PO, not a lead, so priorities stay in one place.

Tried once: an issue assigned to the squad, delegated by the PO, answered by the lead, closed by the PO. No real work yet.

## Infrastructure: one DevOps agent

Only one agent may change a shared machine or cluster (see `devopsPermissions` in `team.config.json`). With Multica:

- A separate container with the cluster tools and a limited account: manage the project namespaces, read the rest, no cluster-wide rights. It holds no project code.
- One Multica agent on that runtime, `--max-concurrent-tasks 1`. Multica then queues requests, so only one is at work.
- PO agents get no cluster credential. Their instructions say: ask the DevOps agent by mention on the issue, then stop.
- Releases still go through the pipeline. The DevOps agent restarts, scales, diagnoses and rolls back; it asks the owner for GO before anything that deletes data.

## Limits and what is untested

- Tried once, on one machine: Multica 0.11.1, two workspaces in LXC containers, a setup-check issue answered by each PO agent, and one hire of a member inside a PO run.
- Not run: real work through a PO run; a hire from a PO container to a pool; a PO asking the DevOps agent; a restart of the machine; a daemon on a second machine.
- Team hooks under Multica: checked once. In a PO run started by Multica, a hired developer was refused `git tag` by the guard hook, and its reservation was tied to it and released when it stopped. Not checked: the stop hook refusing a stop with no log entry, and the `deny` rules.
- The guard hook reads the whole command text: a log entry written with a shell command that quotes `git tag` or `git push` is refused too. Reword the entry, or write it with the file tool.
- Multica is source-available, not open source. Read its licence before company use.

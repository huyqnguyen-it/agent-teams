# Team operating model

How the agent team works: who does what, who may start whom, when a plan needs a design review, and what "done" means. Workspace settings are in `team/team.config.json`, machine limits in `team/team.local.json`.

Which file tells which agent what, and which one wins: `.team/docs/instruction-topology.md`.

## 1. Structure

The owner sets direction. The Product Owner (main session) runs the work. Leads deliver, the Architect keeps the system coherent, Resource Manager decides staffing and capacity, DevOps runs the environments. Members are hired per task.

```
                 OWNER
                   │
             PRODUCT OWNER
                   │
   ┌────────┬──────┼─────────┬──────────┐
FE LEAD  BE LEAD  ARCHITECT  DEVOPS   RESOURCE MANAGER
   └───┬────┘
       │  staffed by the Resource Manager; released when the plan ends
 DEVELOPER · RESEARCHER · AUDITOR · TESTER · DATA SPECIALIST · OBSERVER
```

Core roles are PO and Resource Manager. The others are switched on in `team.config.json`. Members are always available to hire and are not listed there. With no lead for an area, the PO reviews that work itself; with no Architect, the PO asks the owner about any change that needs a design review.

## 2. Roles

| Role | Owns | Decides | Never does |
|---|---|---|---|
| Owner | Product direction | UI changes, deploy, release | — |
| Product Owner | Priorities, order of work, reports | Next task; conflicts between leads | Feature code; pushing without the owner's GO |
| FE / BE Lead | Their repositories; knows whether a plan is complete | Approach inside one boundary | Other repositories; protected branches; tags |
| Architect | Architecture, structure, conventions, data design | Design of anything crossing a boundary | Feature code; priorities; overruling the owner |
| DevOps | Environments, running applications, test resources | How to provide a resource | Changes beyond its permissions; reading secrets |
| Resource Manager | Roster, skills, capacity | Hire or reuse; WAIT by the budget | Priorities; engineering work |
| Developer | One task, on a branch | How to implement the approved design | Other repositories; `git stash` |
| Researcher | One question, with sources | — | Code changes |
| Auditor | Independent check | ACCEPT or REJECT, with evidence | Fixing what it finds |
| Tester | Running suites, real results | — | Mocks or skips to get a pass |
| Observer | Reading the workspace's sources; new tickets in `triage` | What a signal is and who should look at it | Moving tickets, priorities, changing anything it reads |

## 3. Design review

A lead discusses a plan with the Architect before work starts when any line is true:

| Trigger | Example |
|---|---|
| Touches two or more bounded contexts or repositories | A flow across a service and the UI |
| Changes a contract: operation, event, wire shape | A new field on a shared event |
| Adds a service, store, queue, library | A new database table or collection |
| Introduces a new pattern, or a second way to do something | An own retry loop beside the shared one |
| Moves ownership of data or logic | State moves from one service to another |
| Changes shared structure or a convention | A new layer in the service template |
| Adds a store or index, or changes a key or retention rule | A second index on a table |

No review: a change inside one module with no contract change.

Verdicts: APPROVED, CHANGES NEEDED, ESCALATE. Output goes in the plan under `## Design review`. If leads still disagree, the Architect writes both options and the PO takes them to the owner.

Design rules:
1. One way per problem.
2. Features are data, not new code paths, where the platform allows it.
3. Dependencies point one way.
4. Thin flow, logic in handlers.
5. Ports in the domain, adapters at the edge.
6. No aliases, shims or old readers: change consumers in the same release.
7. Reuse before adding.
8. Files stay small, and their names say what they do.
9. Every limit has a code default and an env override.
10. The design document changes with the code.
11. Every index names the query it serves; every store names its owner and its cleanup.

## 4. DevOps

DevOps keeps applications running and gives the team what it needs. A lead asks for a resource; nobody else changes an environment. Permissions are in `team.config.json`. Never reads secrets. Throwaway test infrastructure only; never shared services.

## 5. Staffing and capacity

A lead asks for a skill, not a person. Resource Manager decides:

| Situation | Decision |
|---|---|
| New feature or new plan | Hire new |
| Follow-up in the same plan, skill fits | Reuse |
| Agent's context nearly full, or it failed the same task | Hire new |
| Auditing | Always hire new |
| Budget not met | WAIT |

- **Only the PO starts, resumes or stops an agent.** That is the gate that keeps the ceiling.
- **Reserve before every start or resume:** `.team/tools/resource-lease.py reserve <agent> <role> [--heavy]`. It answers `HIRE <agent> on <host>` and writes a lease with the agent's expected peak memory and load, or `WAIT <reason>`. `--heavy` means the brief has Docker builds or full suites. On `main` the PO starts a subagent; on another host it starts a headless worker (`multi-server.md`). The lease is released when the agent stops (a hook does it for subagents) or expires.
- **Free room adapts to each machine:** a host fits when its free memory and load, after the unused part of its leases and its reserve, cover the estimate, and it has fewer than `maxAgents` leases. The estimate is learned from each role's past peaks. `resource-lease.py status` prints every host and `PICK <host>`, at no token cost.
- The ceiling is `ceiling` in `team.config.json`: the most agents at once on all hosts together. It caps cost, not machine load: more machines do not raise it; only the owner does.
- `.team/tools/capacity-check.sh` reads this machine's capacity at no token cost. Placement is a script, not an agent: the Resource Manager decides only hire or reuse when it is not obvious.
- YELLOW: no new hires, capped runs only. RED: stop every run.
- Only the owner can lift YELLOW, for one named task, in their own words. Nobody can lift RED. If capacity stays below GREEN, the PO tells the owner what is using the machine and asks; it does not lower limits itself.
- A hire that must WAIT: the PO records it on the board and retries at the next step. Do not poll in a loop; a background wait uses `tools/capacity-check.sh` only where the session allows it.
- Conventions live with the code, never in `.team/`: linter and formatter config first, then the repo's `docs/code-standards.md` (or its existing `CLAUDE.md` / `CONTRIBUTING.md`), and workspace `docs/conventions.md` for rules shared by all repos. The brief names the file; the lead's review and the Auditor check against it. A problem found twice in review becomes a lint rule, or a line in that file if no tool can check it. With no convention file, the brief says which conventions to follow from the existing code.
- Scale the audit to the risk: a small change in one module needs the lead's review, not a hired Auditor. Plans that cross a boundary or change a contract always get one.
- Heavy commands (docker builds, large suites, package installs) run through `.team/tools/heavy.sh <command>`: one at a time on a machine, or up to `capacity.heavySlots` in `team.local.json` while the machine is GREEN. A short test run of a small project does not need it, and a wrapper command may not match a restricted allow list. Tests use the project `commands` in `team.config.json`, capped workers where the tool supports them, and throwaway containers.

Messages:

```
STAFF? be-lead developer repo-x tests new-feature
HIRE developer-1 | REUSE developer-1 | WAIT <reason>
TASK DONE developer-1
PLAN COMPLETE <plan> | PLAN PARTIAL <plan>: <what is left>
```

A lead reports PLAN COMPLETE only when: every phase is done; tests pass on final code and the CI pipeline is green on the branch; the Auditor accepted and review items are closed; docs are updated; every task has a log entry; every draft skill from the plan is accepted or deleted, unused skills are retired (§11), and the changed role memories are checked (§8); nothing is left unresolved.

### Cost

Cost follows context size. The ceiling is not a target.

| Rule | Why |
|---|---|
| Resume only within the hour, for the same task | The prompt cache makes it cheap |
| Next day or next plan: fresh agent from `handover.md` | A short handover costs far less than a full context |
| Save lessons to `skills/` | The next agent reads one file |
| Delegate reading | Leads keep small contexts |
| Cheapest model that fits | Scripts first, then the smallest model |
| The PO session restarts when it grows large | It is the largest context |

The role is permanent; the agent behind it is not.

## 6. Flow

```
Owner request, or a ticket (§6 Tickets) → PO priority → Lead plan → crosses a boundary? → Design review
→ Resource Manager: hire or reuse → Member builds on a branch, with tests
→ Lead reviews → Auditor → CI green → PLAN COMPLETE → PO reports → Owner GO → PO merges and tags
→ DevOps (or the lead) verifies the release → PO closes → Observer watches the first hour
```

How the loop starts, where it waits for the owner, and the scheduled check: `.team/docs/work-loop.md`.

**Retry limit.** A task gets at most `maxRounds` rounds (`team.config.json`, default 3). A round fails when the lead's review or the Auditor sends the work back, or the member reports BLOCKED; the lead records each with `ticket.py fail <id> --by <lead> --note "<why>"`. At the limit `ticket.py` moves the ticket to `waiting` and refuses `in-progress`; the PO asks the owner on the board, with the evidence. Only with the owner's answer does the PO move it on with `--owner-ok`, which starts the count again. A fresh hire after a failure (§5) does not reset the count.

### Tickets

Every piece of work is a ticket, the owner's own requests included, so the team can react to it, the scheduled check sees it, and nothing is lost. All agents use one command, `.team/tools/ticket.py`, whatever the backend:

- **Default:** Markdown files in `team/tickets/<id>.md`, committed. No setup.
- **A provider** (Redmine, GitLab, Jira...): set `tracker` in `team.config.json` to owner-approved commands, and `ticket.py` runs them instead. Agents do not change:

```json
"tracker": {
  "provider": "redmine",
  "commands": {"new": "<create; may use {title} {kind} {source} {owner} {file}>", "list": "...", "show": "<{id}>",
               "find": "<{source}>", "move": "<{id} {state} {note}>", "comment": "<{id} {note}>"},
  "states": {"triage": "New", "accepted": "Accepted", "in-progress": "In Progress", "resolved": "Resolved", "closed": "Closed"}
}
```

| # | Step | Who | Command | State |
|---|---|---|---|---|
| 1 | A signal comes in | A source (`sources` below), or the owner or a colleague asking | — | — |
| 2 | Read it; repeat check | Observer; the PO for any request, from the terminal or the board | `ticket.py find <source id>` | — |
| 3 | Create the ticket: summary, evidence, source ID, suggested owner | Observer; the PO for a request, before any planning (`--by owner`; `--source board:<request id>` for a board request) | `ticket.py new` | `triage` |
| 4 | Task or not | PO | `ticket.py move <id> accepted --owner <lead>` | `accepted`; `waiting` (a requirement: the owner decides new scope, asked on the board); `rejected` with the reason |
| 5 | Read and accept the work, or return it | Lead | `move <id> in-progress --plan <plan>`, or `move <id> triage --note <why>` | `in-progress` |
| 6 | Resolve, with evidence: tests and the CI pipeline green on the branch | Lead, at PLAN COMPLETE | `move <id> resolved --note <commit, pipeline>` | `resolved` |
| 7 | Merge and tag | PO, after the owner's GO | `comment <id> --note "merged <sha>"` | `resolved` |
| 8 | Verify the release: pipeline after merge, deploy, health | DevOps; the lead when there is no DevOps role | `comment <id> --note "release verified: <pipeline, deploy>"`; failed: `move <id> in-progress --note <evidence>` (a failed round) | `resolved`, or back to `in-progress` |
| 9 | Close, then watch | PO: closes after step 8, then hires an Observer once to compare the first hour after release with before | `move <id> closed` | `closed` |

- **The lead owns the final result.** Its plan is not over at PLAN COMPLETE: it stays responsible until step 8 passes, and does step 8 itself when there is no DevOps role. Between steps it is idle at no cost; the PO resumes it with the result.
- **CI results come in without waiting.** No agent waits on a pipeline. A source `check` (`.team/tools/gitlab-pipelines.py check <project>...` for GitLab CI) reports each finished pipeline once; the PO passes a branch result to its lead and a release result to DevOps, or to the lead. Anyone reads a result with `gitlab-pipelines.py show <project> <ref>`. The owner connects GitLab once per machine (`SETUP.md`, GitLab CI); agents never see the token.
- An Observer's ticket about a problem after a release names the release ticket in `--source`, so the problem traces back to the change.
- A closed or rejected ticket leaves `team/tickets/` for `team/tickets/archive/YYMM/`; it is never edited again, and git keeps it. Only open tickets stay in view.
- `ticket.py` refuses a move outside this flow. Each move and `comment` is added to the ticket's history with who and when.
- **Every work session**, and every scheduled check (`.team/docs/work-loop.md`), the PO starts with `ticket.py list --state triage` and `--state resolved`, and each lead with `ticket.py list --owner <role>`. A plan names its ticket on the board. The PO also runs `.team/tools/template-version.sh` once a day; when it prints UPDATE, the PO tells the owner.
- A ticket never holds secrets or personal data: IDs, counts and the query used, not values.

### Signals

Sources are listed in `team.config.json`, each with a read-only command the owner allowed:

```json
"sources": [
  {"name": "app-traces", "kind": "telemetry", "read": "<command that prints new errors or slow spans>",
   "check": "<optional cheap command that prints one line only when something is new>"},
  {"name": "gitlab-ci", "kind": "ci", "check": ".team/tools/gitlab-pipelines.py check group/service-a group/web"}
]
```

Any provider works if it has a read-only command: telemetry or logs, an error tracker, an issue tracker, CI, alerts. The Observer can also compare `docs/` with the code. A routine check with no judgment becomes a script that prints one line, like the capacity check (§10); the Observer is hired when that line flags something.

- **When:** the PO hires an Observer at the start of a work session, after a release, or when the owner asks. Not in a loop.
- The Observer only creates tickets in `triage`; it never moves, assigns or prioritizes them.
- An Observer measuring the effect of a change is never the agent that built it.

## 7. Team rules

**Workspace rules.** `team/rules.md` holds this workspace's own rules: the owner's decisions that add to these rules or make them stricter, each with its date. Where the two differ, the workspace rule wins. The PO writes a decision there when the owner gives it. The team never edits `.team/`. A rule, tool or skill that fits every workspace becomes a template proposal: the team uses its own copy in `team/` now, and the PO opens a ticket of kind `template` that names the file and says why it is general. The owner sends it to whoever maintains the template; after the release, the workspace updates and deletes its copy.

1. Only the PO pushes protected branches or tags, after the owner's GO for that action.
2. A member works in one repository or worktree and never runs `git stash`.
3. Every brief states the task, files, done-criteria and limits.
4. A result counts only when checked, with evidence.
5. Report failures as they are.
6. Never read or print secrets.
7. Automation uses local data, never shared environments.
8. A permission denied to one agent is not routed through another.

`init` makes the harness enforce what it can (`.claude/settings.json`), at no token cost:

| Rule | Enforced by |
|---|---|
| Agents never push, tag or stash; a headless worker pushes only its feature branch | `team-hooks.py guard` (PreToolUse) |
| The Auditor never fixes what it finds | The same hook: it writes only under `team/` |
| No stop before the log entry, the journal entry and the journal compaction | `team-hooks.py stop` (SubagentStop) asks once |
| `.team/` is never edited; tickets change through `ticket.py` only | `deny` rules for Edit and Write |
| Secrets are not read: the GitLab token file, `~/.ssh`, `.env` files, keys | `deny` rules for Read (also `cat`, `head`, `sed`; not scripts or `grep -r`) |
| No AI or co-author lines in commits and PRs | `attribution` |
| Retry limit | `ticket.py fail` |
| Capacity and the ceiling | `resource-lease.py reserve` |

A hook rule is not a sandbox: the owner's protected branches in GitLab are the real gate for pushes.

### Writing

Everything an agent writes for another agent or the owner follows a short form of ASD-STE100 (Simplified Technical English): briefs, reports, log and journal entries, tickets, skills, board questions.

1. One instruction per sentence, as a command: "Run the tests. Then read the output."
2. Instructions up to 20 words; descriptions up to 25.
3. Active voice: name who does it. "The lead verifies the release", not "the release is verified".
4. One word, one meaning: use the team words below, and no synonyms for them.
5. No idioms, no slang, no "-ing" verb forms where a plain verb works.
6. Up to 6 sentences per paragraph. Put a warning before the step it applies to.
7. Exact values: file:line, IDs, numbers with units, real times. Never "soon", "some" or "a few".

Not covered: code, commands, commit messages (conventional commits), and quoted logs or evidence, which stay as they are. Technical names are allowed. The STE dictionary is not used.

The lead and the Auditor send back text that breaks these rules. That is a fix, not a failed round.

| Word | Means only |
|---|---|
| owner | The person who owns the workspace and gives GO |
| ticket | One unit of work in `ticket.py` or the tracker |
| plan | The lead's plan for one ticket or request |
| round | One try at a task that ends in the lead's or the Auditor's verdict |
| GO | The owner's approval to merge, push or tag |
| accept / reject | A verdict on a ticket (PO) or on work (lead, Auditor) |
| resolved / closed | Ticket states: work done / release verified |
| DONE / BLOCKED | Report status of one agent's task |
| hire / reuse | Start a new agent / resume an existing one |
| signal | A new item that a source shows |

## 8. Work log

Every agent appends to `team/log/YYMMDD.md` before stopping, using `.team/templates/work-report.md`: what it did, what it decided and why, evidence, status. A task with no entry is not done. The PO is an agent too: its last step in every session is its own entry (what it staffed, decided, and the state of the work) and an update of `team/status/board.md`. No secrets.

### Journal

The log is the team's short record. The journal is each role's long-term memory, in detail: `team/roles/<role>/journal/YYMMDD.md`, one file per role per day. Members have one too (`team/roles/developer/journal/`, and so on), shared by every hire of that role.

- **Write:** before stopping, after the log entry, using `.team/templates/journal-entry.md`: context, what was tried (failures too), decisions, surprises, what to do next time. Several agents of a role append to the same day's file under their own name.
- **Read:** when started, read `journal/memory.md`, then the newest day file of your role; search older ones and `journal/archive/` (`grep`) only when your task touches the same area. Do not read the whole journal.
- **Distil:** when the same "Next time" point shows up twice, write it as a skill (§11) and say so in the journal. The journal holds history; skills hold what is proven.
- The handover is the current work, replaced each time; day files are only appended to.

**Compact and archive.** After your journal entry, run `.team/tools/journal-archive.sh <role> --list`. Empty output: done. Otherwise (more than 7 day files):

1. Read the listed files and `memory.md`.
2. Rewrite `memory.md` (`.team/templates/journal-memory.md`, under 40 lines). Keep only what is still true and still matters: facts about this workspace, decisions in force, pitfalls not yet a skill, the skills written from this journal. Drop finished work, anything a skill already says, anything no longer true. A point that is proven and needed often becomes a skill, with one line here pointing to it.
3. Run `.team/tools/journal-archive.sh <role>`: the listed files move to `journal/archive/YYMM/`. Archived files are never edited or deleted; git keeps them.

The limits are `JOURNAL_MAX_DAYS` (7) and `JOURNAL_KEEP_DAYS` (2). If `memory.md` will not fit in 40 lines, the role is carrying lessons that should be skills.

**Check.** At PLAN COMPLETE the lead reads the `memory.md` changes of every role that worked in its plan (`git diff` since the plan started) against the archived day files, and fixes or removes a line that is wrong or unsupported. The PO does the same for its own and the staff roles' memory at the end of their task. A small model compacts; a lead decides what the team remembers.

## 9. Talking to the owner

The PO keeps one board (`boardUrl`, created with the `team-board` skill), reads it at every step, and only asks real decisions, each with a recommendation. Push notifications are for blockers only.

### Knowledge

What is true for everyone lives in the workspace, in git, never in `.team/` and never only in a journal.

| Knowledge | Where | Who keeps it |
|---|---|---|
| Architecture, design, glossary | Workspace `docs/` | Architect, in the same plan as the change |
| Conventions of one repository | That repository (§5) | Its lead |
| Product and engineering decisions of the owner | `docs/`, one decision file: dated, the later one wins, replaced ones listed | PO, when the owner answers |
| Team decisions of the owner (ceiling, heavy jobs) | `team/rules.md` | PO, when the owner answers |
| Plans | `plans/`, committed; the brief and the ticket name the path | The lead of the plan |

- A document starts with the header in `.team/templates/knowledge-doc.md`: status, last check, sources. A source is in the repository or is a link; never a file only one machine has.
- `docs/` has one index file that lists the documents. An agent reads the index first.
- At PLAN COMPLETE the lead moves a fact every role needs from the journals to `docs/`.
- A worker on another machine gets plans and docs only through git: commit and push them before the hire.
- The Observer may flag a document with an old last-check date, or one that differs from the code.

## 10. Scripts before agents

Repeated work with no judgment is a script. The second time an agent does the same steps by hand, it writes a script and a one-line skill. Add an MCP server only when a script cannot do it.

## 11. Skills

A skill is a short how-to proven on real work, written with `.team/templates/skill.md`. `SKILL.md` stays under 30 lines; never a guess. Skills belong to the role, not the agent: a fresh member's lesson is kept in its role's folder for every later hire, or it is lost.

- **Layout:** every skill, in the template, `team/skills/` or a role, is a folder named after it: `<name>/SKILL.md` (frontmatter `name`, `description`; team and role skills add `status` and `author`), `scripts/` for code it runs, `assets/` for files it copies or fills (templates, example configs, samples). Add only the folders it needs. Template skills have no `status`: they are accepted. Moving or deleting a skill moves or deletes the whole folder.
- **Find:** before exploring, list the `description:` lines of your role skills (`team/roles/<role>/skills/*/SKILL.md`), `team/skills/*/SKILL.md` and `.team/skills/*/SKILL.md` (`grep -H '^description:'`), and open only the skills that match your task. Do not read them all.
- **Write:** when a task took more than one try, will come back, or its lesson repeats in the role journal (§8). A new skill is `status: draft`, in `team/roles/<role>/skills/<name>/SKILL.md`. Only its author uses a draft; every other agent skips it.
- **Accept:** at PLAN COMPLETE the lead checks each draft from its plan against the work's evidence, then sets `status: accepted` (editing it if needed) or deletes it. Drafts from the PO, Resource Manager, Architect, DevOps or Observer are accepted by the PO at the end of that task. A draft not accepted by then is deleted; what was worth keeping goes to the journal.
- **Use:** when a skill helped, update its `Last used` line with the date and the plan.
- **Retire:** at PLAN COMPLETE the lead deletes the accepted skills of the roles in its plan that were not used in its last 5 plans, or that proved wrong, and says so in its journal. The PO does the same for `team/skills/` and the staff roles. Fewer skills keep every start cheap.
- **Share:** once a second role needs an accepted skill, it moves to `team/skills/`. A generic one can be promoted to this template after Architect review.

## 12. Models

Defaults are in `team.config.json`. Architect: the strongest model, because its mistakes spread. Resource Manager and Tester: the smallest. Others: mid. To serve the smallest roles from a model server of your own, see [self-hosted models](multica.md#optional-self-hosted-models).

## 13. Git

| Content | Commit? |
|---|---|
| `team/` config, status, tickets, log, skills, journal | Yes, in the workspace repository |
| `handover.md`, `team.local.json`, `.claude/`, `.team/` | No, ignored |
| Secrets | Never |

Team files never go into service repositories.

## 14. Several machines

- **Remote execution:** agents stay; heavy commands run through SSH or `DOCKER_HOST=ssh://`.
- **Remote session:** Claude Code with Remote Control on the same account joins through `SendMessage`.
- **Headless worker:** `ssh host '.team/tools/worker-run.sh <role> <brief file>'`, one task then exit. It needs its own login and a tight allow list.
- Hosts are listed in `team.local.json`, each with `maxAgents`. `resource-lease.py` reads every host's capacity over SSH and places each hire; leases are kept on the main machine, because only the PO hires. `flock` is per machine. Work moves by git.
- A machine joins with `host-join.sh`. Each machine may use its own account and agent CLI (`cli`: claude, codex, cursor). `worker-run.sh` runs a brief there with the rules in front. Only Claude Code runs the team hooks: keep leads on Claude Code, and send other CLIs member work only.
- The main machine stays light: the PO, the board, tickets, git. Heavy work goes to other hosts. A large area can have its lead on another host, starting its own workers there, so only its result reaches the PO.

How to set it up: `.team/docs/multi-server.md`.

## 15. Departments (later phase)

One machine is headquarters: owner, PO, Resource Manager, Architect. Each other machine runs a lead with its own members and capacity check. HQ and departments talk through issues and merge requests, not messages. HQ keeps priorities, contracts and releases, enforced by protected branches and limited tokens. Each department has a budget, a time limit and a stop rule. Leads do not message each other: they go through HQ.

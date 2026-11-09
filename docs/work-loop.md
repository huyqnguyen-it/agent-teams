# Work loop

How work goes round the team: what starts it, what keeps it going, where it waits for the owner, and what stops it from running forever. The rules themselves are in `team-operating-model.md`; this page shows how they connect.

## The loop

```
              ┌─────────────────────────── OUTER LOOP: work ───────────────────────────┐
              │                                                                        │
  SOURCES ──► OBSERVER ──► ticket.py new ──► [triage]                                  │
  telemetry,   (hired by the PO)  repeat check     │                                   │
  issues, CI,                     by source ID     ▼                                   │
  docs drift                              PO triage ──rejected──► archive              │
                                          │      └──waiting──► OWNER decides ◄─────────┼── gate 1: new scope
  OWNER request ──► PO ──────────────────►│ accepted, owner = lead                     │
                                          ▼                                            │
                                   LEAD: plan, design review if needed                 │
                                          │ in-progress                                │
                                          ▼                                            │
                             RESOURCE MANAGER: hire / reuse / WAIT (capacity)          │
                                          ▼                                            │
                     ┌─────────► MEMBER builds on a branch, with tests                 │
      INNER LOOP:    │                    ▼                                            │
      rework,        ├─ changes ── LEAD review                                         │
      max maxRounds  │                    │ ok                                         │
                     └─ REJECT ─── AUDITOR (fresh hire)                                │
                        (limit hit → ticket waiting → OWNER) ◄─────────────────────────┼── gate 3: retry limit
                                          │ ACCEPT                                     │
                                          ▼                                            │
                                   CI green on the branch → PLAN COMPLETE → [resolved] │
                                          ▼                                            │
                                   PO reports ──► OWNER GO ◄───────────────────────────┼── gate 2: merge and release
                                          ▼                                            │
                                   PO merges, tags; GitLab CI runs the release         │
                                          ▼                                            │
                     DEVOPS (or the LEAD if no DevOps) verifies: pipeline, deploy      │
                          │ failed → [in-progress], a failed round, back to the lead   │
                          ▼ ok                                                         │
                                   PO closes → [closed] → archive                      │
                                          ▼                                            │
                     OBSERVER watches the first hour ──► new tickets, --source = release ticket ─┘
```

```
  LEARNING LOOP (every agent, every stop)

  log entry → journal day file → more than 7 files: compact into memory.md, archive the rest
           → a lesson seen twice → draft skill → lead accepts or deletes it at PLAN COMPLETE
           → the next hire reads memory.md and the matching skills when it starts ──┐
                     ▲                                                              │
                     └──────────────────────────────────────────────────────────────┘
```

## What starts it

Nothing in the loop runs unless a Product Owner session runs. Putting work in does not start it; waking the PO does.

| Put work in | Wake the PO |
|---|---|
| A ticket: `ticket.py new`, or an issue in the configured tracker | The owner opens Claude Code in the workspace, or sends a running session "check tickets" |
| A request to the PO or on the board | The scheduled check, below |
| A signal in a source, found by an Observer | — the Observer is hired by the PO, so it needs a PO too |

When the PO runs, it starts with `ticket.py list --state triage` and `--state resolved`, and the board.

## Who tracks the result

The lead owns the final result: its plan is not over until the release is verified.

| Stage | Who | How |
|---|---|---|
| Tests on the branch | Member runs, lead checks | Project `commands` |
| CI pipeline on the branch | Lead, before PLAN COMPLETE | `gitlab-pipelines.py show <project> <branch>` |
| Pipeline after merge, deploy, health | DevOps; the lead when there is no DevOps role | `gitlab-pipelines.py show <project> <main or tag>`; a comment on the ticket |
| Behavior after release | Observer, hired once by the PO for the first hour | Sources; new tickets name the release ticket |

No agent waits on a pipeline: that would cost tokens while nothing happens. The lead or DevOps stops idle at no cost; the `gitlab-ci` source reports each finished pipeline once; the scheduled check (or the owner) wakes the PO, which resumes the right agent with the result. A failed release sends the ticket back to `in-progress` and counts as a failed round.

## The owner's gates

The loop stops and waits for the owner at three points, on purpose. A scheduled run never passes them.

| Gate | When | Ticket | How the owner answers |
|---|---|---|---|
| 1. New scope | A requirement, or anything the owner did not ask for | `waiting` | Board question |
| 2. Merge and release | PLAN COMPLETE | `resolved` | GO on the board or in the terminal |
| 3. Retry limit | A task failed `maxRounds` times | `waiting` | Board question: retry, change the task, or drop it |

## Loops inside the loop

| Loop | Goes round when | Ends when | Limit |
|---|---|---|---|
| Rework | The lead's review sends work back | The lead accepts | `maxRounds` |
| Audit | The Auditor rejects | The Auditor accepts | `maxRounds`, same count |
| Returned ticket | The lead moves it back to `triage` | The PO accepts or rejects it | The PO decides |
| Reopened ticket | `resolved` goes back to `in-progress` | Resolved again | `maxRounds` |
| Learning | Every agent stops | — | `memory.md` under 40 lines; journal compaction |

**Retry limit.** A round fails when the lead's review or the Auditor sends work back, or the member reports BLOCKED. The lead records each failed round on the ticket. After `maxRounds` (default 3) the task stops: the ticket goes to `waiting` and the owner is asked. Hiring a fresh agent does not reset the count. This is what keeps one hard task from burning tokens without end.

## Scheduled check

To keep the loop going without the owner at the terminal, cron runs `.team/tools/scheduled-check.sh` in the workspace:

```
*/30 * * * * cd /path/to/workspace && .team/tools/scheduled-check.sh >> team/scheduled.out 2>&1
```

Each run costs no tokens unless work is waiting:

```
schedule.enabled? ─no─► exit
previous run still going? ─yes─► exit
capacity RED? ─yes─► exit
a triage ticket, or a source "check" printed something (CI results too)? ─no─► "idle", exit
                                                                        └─yes─► headless PO (claude -p)
```

The headless PO does only what needs no owner: hires an Observer for new signals, triages, starts or continues accepted work within capacity and the ceiling. Everything at a gate goes to the board as a question, and the run stops when nothing is left it can do alone.

Set it up in `team/team.local.json` (per machine):

```json
"schedule": { "enabled": true, "allowedTools": ["Read", "Write", "Edit", "Glob", "Grep", "Agent", "Bash(.team/tools/ticket.py:*)"] }
```

- `allowedTools` is the owner's decision: a headless run is denied any tool not listed. Add the project's test and git commands only if you want scheduled runs to build.
- A source's `check` command (in `team.config.json`) should be a cheap script that prints one line only when something is new. Without one, signals are found only when an Observer is hired.
- Pick the interval by cost: an idle check is free, but each run that finds work starts a PO session.
- Do not run the schedule while you work with an interactive PO session on the same workspace: two POs would triage the same tickets. Set `enabled` to false, or stop cron, first.
- Resolved tickets do not wake it: they wait for the owner's GO or for a release result, which comes in as a CI signal.
- For GitLab CI, add the `gitlab-ci` source (`gitlab-pipelines.py check <project>...`); the owner connects GitLab once per machine with `.team/tools/gitlab-setup.sh` (`SETUP.md`, step 6); cron needs nothing more.
- Board requests and answers are not seen by the script (it has no board access); the PO reads them when it runs.
- Output goes to `team/scheduled.out`, which git ignores.

## Not covered yet

- The board has no form for a new request: today the owner adds a ticket or an issue in the tracker.
- The scheduled check has run only up to starting the PO; a full headless PO run on a schedule is not tested.

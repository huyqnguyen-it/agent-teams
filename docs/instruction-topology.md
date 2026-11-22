# Instruction topology

Where each instruction lives, who reads it, and which one wins. Read this when an agent misses a rule, or before you add one.

## How instructions reach an agent

```
                         OWNER MESSAGE
                              │
                              ▼
 Session start ──► CLAUDE.md (workspace)
                     ├─ workspace rules, docs/
                     ├─ @.team/docs/team-operating-model.md   the team rules
                     └─ @team/rules.md                         this workspace's rules; they win
                              │
              ┌───────────────┴────────────────┐
              ▼                                ▼
       MAIN SESSION = Product Owner      AGENT started by the PO
       team/status/board.md              .claude/agents/<role>.md   generated
       team/status/roster.md                   │
              │                                ├─ core role
              │ brief                          │    team/roles/<role>/profile.md
              │ .team/templates/brief.md       │    team/roles/<role>/handover.md
              └───────────────►                ├─ member
                                               │    .team/roles/members/<role>.md
                                               └─ then
                                                    the brief
                                                    skills matching the task, by description
                                                    team/team.config.json   commands, repositories
```

Agent definitions load when a session starts: after `init`, start a new session.

## Who reads what

| Reader | Reads | When |
|---|---|---|
| Product Owner | `CLAUDE.md`, team rules, `team/status/`, the board | Every session; the board at every step |
| Lead | Agent file, profile, handover, the plan | When started or resumed |
| Architect | Agent file, profile, handover, the plan, `docs/` | Before a design review |
| Resource Manager | Agent file, profile, roster, `team.config.json`, `team.local.json`, capacity check | On each staffing request |
| DevOps | Agent file, profile, handover, its skills | When started or resumed |
| Member | Agent file, member profile, the brief, matching skills, role journal memory | When hired |
| Observer | Also `sources` in `team.config.json`, open tickets (`ticket.py list`) | When hired |

## Who writes what

| File | Written by | When |
|---|---|---|
| `.team/` | Nobody in a workspace | Only through a template update |
| `.claude/agents/` | `init` | Generated: do not edit |
| `CLAUDE.md` | Owner; `init` adds one section | Rarely |
| `team/team.config.json` | Owner, through setup | When the team changes |
| `team/rules.md` | PO, with the owner's decision and its date | When the owner decides a rule for this workspace |
| `docs/`, `plans/` | Architect and leads; any kit the workspace uses sets the format | In the same plan as the change |
| `team/roles/<role>/profile.md` | `init`; PO with the owner's OK | Scope changes |
| `team/status/roster.md` | Resource Manager | On each hire or release |
| `team/status/board.md` | Product Owner | On each change of status |
| `handover.md` | That role | Before stopping |
| `team/log/YYMMDD.md` | Every agent | Before stopping |
| `team/roles/<role>/journal/YYMMDD.md` | Every agent of that role, members too | Before stopping, after the log entry |
| Skills | The agent that learned it, as a draft; the lead (or PO) accepts or deletes it | Draft: when a task took more than one try. Accept: at PLAN COMPLETE |
| `team/tickets/` (or the tracker) | Through `.team/tools/ticket.py` only: Observer or PO create; PO accepts, rejects, closes; the lead takes and resolves | At each step of §6 Tickets |

## Which one wins

Highest first:

1. The owner's latest message.
2. The workspace: `CLAUDE.md` and `docs/`, including owner rulings.
3. The approved plan and its design review.
4. Team rules: `.team/docs/team-operating-model.md`.
5. Role profile.
6. The brief.
7. Skills.

A lower level never overrides a higher one. If two conflict, stop and ask the level above. Nothing here overrides the permission check: a denied action stops there.

## Where a new rule goes

| Rule is about | Put it in |
|---|---|
| One decision by the owner | Workspace `docs/` |
| Every workspace | Template: `docs/team-operating-model.md` |
| One role, in every workspace | Template: `roles/<role>/profile.md` |
| One role, here only | `team/roles/<role>/profile.md` |
| How code looks in one repo | That repo: linter and formatter config first; the rest in its `docs/code-standards.md` (or its existing `CLAUDE.md` / `CONTRIBUTING.md`) |
| How code looks across repos | Workspace `docs/conventions.md`, owned by the Architect |
| How to do a repeated task | A skill |
| One task only | The brief |

State a rule in one place, and link to it from others. A copied rule goes stale.

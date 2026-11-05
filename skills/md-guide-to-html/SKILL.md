---
name: md-guide-to-html
description: Turn a Markdown guide (deployment guide, runbook, reference doc) into one self-contained HTML page with a side menu, search, table filter, checklist and copy buttons. Use when a team member asks for an HTML version of a guide, or edits a guide that has one.
---

# Markdown guide to HTML

The `.md` stays the source. The HTML is generated, so never edit it by hand: edit the Markdown and rebuild.

## What the page gives

- Side menu grouped by purpose, with the current section marked.
- Search across all sections and table rows.
- "Required variables only" filter for tables with a `Required` column; required rows are marked.
- Checklist with a progress bar on one section's table, saved in the reader's browser.
- Copy button on code blocks. ASCII diagrams stay as they are.
- Light and dark mode, phone layout, print layout. It works offline: no CDN, no fonts to fetch.

## Steps

1. Start from `assets/deployment-guide-template.md` for a deployment guide, or any Markdown with one `#` title, `##` sections and pipe tables. A blank line must come before each table.
2. Copy `guide.config.example.json` beside the guide as `<guide>.config.json`, and list the menu groups. Without a config, all sections go in one group.
3. Check: `python3 .team/skills/md-guide-to-html/scripts/guide-check.py <guide>.md`. Fix everything it reports: a broken row shows under the wrong header in the HTML too.
4. Build: `python3 .team/skills/md-guide-to-html/scripts/guide-md-to-html.py <guide>.md`. Needs Python `markdown`.
5. Open the page once in a browser.

## Deployment guide structure

Keep this order. A reader must find what to prepare and what to run first, and what changed last.

| Section | Holds |
|---|---|
| Revision | Rev, date, scope, and how to read the tables |
| Infrastructure Request | New services with resources, new data stores, other requests |
| Before You Start | Glossary, names in Check lines, how to deploy one service, if a step fails |
| Runbook | Numbered steps naming their section; rollback; what a passing smoke test looks like |
| Services, Topology | Image and tag table; an ASCII diagram |
| Configuration | Ingress, ConfigMap, secrets, data stores |
| One section per service | Image, variables, a **Check** line |
| Post-Deploy Operations | Commands with expected results |
| Change Summary (last) | Everything that changed against the last release, for DevOps to compare with the environment |

## Variables

List variables in alphabetical order in every table whose first column is `Variable` or `Key`, and in the Change Summary lists. `guide-check.py` reports a table out of order, and `guide-md-to-html.py` does not sort for you: fix the Markdown.

## Change Summary

Generate it, never write it from memory:

```bash
python3 .team/skills/md-guide-to-html/scripts/guide-diff.py <last-guide>.md <this-guide>.md
```

Use the output for these tables: Services, Infrastructure, Ingress, Environment renamed, removed and new. The tool compares documents, not code: "new" can mean newly documented, "removed" means no longer in the guide, and a rename shows as a removal plus an addition. Check each line against the manifests.

## Example

`examples/` has a full sample: `sample-guide.md`, `sample-guide.config.json`, `sample-guide.html`. Open the HTML to see the result.

## Config

| Key | Use |
| --- | --- |
| `groups` | Menu groups: `{"name", "sections"}`, sections by heading |
| `rest`, `restAfter` | Group name for unlisted sections, and how many groups come before it |
| `checklist` | Section heading whose table gets checkboxes; default `Runbook` |

## Rules

- No secrets in a guide: the HTML holds the same text.
- Checklist state lives only in that reader's browser.
- The page shows what the Markdown says: it does not prove the content is right.

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

1. Write the guide: one `#` title, `##` sections, pipe tables. A blank line must come before each table.
2. Copy `guide.config.example.json` beside the guide as `<guide>.config.json`, and list the menu groups. Without a config, all sections go in one group.
3. Build: `python3 .team/skills/md-guide-to-html/scripts/guide-md-to-html.py <guide>.md`. Needs Python `markdown`.
4. Check that every table row has the same column count as its header. A broken row shows under the wrong header in the HTML too.
5. Open the page once in a browser.

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

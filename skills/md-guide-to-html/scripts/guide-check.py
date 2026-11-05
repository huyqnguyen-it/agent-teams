#!/usr/bin/env python3
"""Check a Markdown guide before building it. Usage: guide-check.py <guide.md> [--config guide.config.json]
Reports: table rows with the wrong column count, service sections with no Check line, menu entries and
runbook references to sections that do not exist. Exit code 1 when anything is wrong."""
import json, pathlib, re, sys


def main():
    args = sys.argv[1:]
    cfg_path = None
    if '--config' in args:
        i = args.index('--config')
        cfg_path = pathlib.Path(args[i + 1])
        del args[i:i + 2]
    src = pathlib.Path(args[0])
    sibling = src.with_suffix('.config.json')
    cfg_path = cfg_path or (sibling if sibling.exists() else None)
    cfg = json.loads(cfg_path.read_text()) if cfg_path else {}
    lines = src.read_text().split('\n')
    text = '\n'.join(lines)
    problems = []
    i = 0
    while i < len(lines):
        if lines[i].startswith('|'):
            j = i
            while j < len(lines) and lines[j].startswith('|'):
                j += 1
            cols = lines[i].replace('\\|', '').count('|')
            problems += [f'line {k + 1}: wrong column count' for k in range(i, j)
                         if lines[k].replace('\\|', '').count('|') != cols]
            if i and lines[i - 1].strip():
                problems.append(f'line {i + 1}: table needs a blank line before it')
            i = j
        else:
            i += 1
    parts = re.split(r'^## (.+)$', text, flags=re.M)
    sections = {parts[n].strip(): parts[n + 1] for n in range(1, len(parts), 2)}
    subs = {s.strip() for s in re.findall(r'^### (.+)$', text, flags=re.M)}
    for name, body in sections.items():
        if '**Image:**' in body and '**Check:**' not in body:
            problems.append(f'section "{name}": image but no Check line')
    for group in cfg.get('groups', []):
        problems += [f'menu: no section "{s}"' for s in group['sections'] if s not in sections]
    plan = sections.get(cfg.get('checklist', 'Runbook'), '')
    for row in re.findall(r'^\| *\d+ *\|.*\|([^|\n]+)\|$', plan, flags=re.M):
        for ref in row.split(','):
            ref = ref.strip()
            if ref and ref != '—' and ref not in sections and ref not in subs:
                problems.append(f'runbook: no section "{ref}"')
    print('\n'.join(problems) if problems else f'OK: {len(sections)} sections')
    sys.exit(1 if problems else 0)


main()

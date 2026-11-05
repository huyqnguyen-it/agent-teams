#!/usr/bin/env python3
"""List what changed between two guides, as a start for the Change Summary. Usage: guide-diff.py <old.md> <new.md>
It compares documents, not code: "new" can mean newly documented, and "removed" means no longer in the guide.
Check each line against the manifests. Renames show as one removal plus one addition."""
import pathlib, re, sys


def sections(text):
    parts = re.split(r'^## (.+)$', text, flags=re.M)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts), 2)}


def names(body):
    return set(re.findall(r'^\| `([A-Za-z_.][\w.]*)`', body, flags=re.M))


def paths(body):
    return dict(re.findall(r'^\| `(/[^`]*)`\s*\| ([\w-]+)', body, flags=re.M))


def tags(text):
    rows = re.findall(r'^\| ([\w. -]+?) +\| `[^`]*/[^`]*` +\| `([^`]+)`', text, flags=re.M)  # image rows only
    return {a: b for a, b in rows}


def main():
    old_text, new_text = (pathlib.Path(p).read_text() for p in sys.argv[1:3])
    old, new = sections(old_text), sections(new_text)
    print('## Sections\n')
    print('Added:', ', '.join(s for s in new if s not in old) or 'none')
    print('Removed:', ', '.join(s for s in old if s not in new) or 'none')
    a, b = tags(old_text), tags(new_text)
    print('\n## Versions\n')
    for name in b:
        if name not in a:
            print(f'New: {name} {b[name]}')
        elif a[name] != b[name]:
            print(f'{name}: {a[name]} -> {b[name]}')
    a, b = paths(old_text), paths(new_text)
    print('\n## Paths\n')
    for path in sorted(set(a) | set(b)):
        if a.get(path) != b.get(path):
            print(f'{path}: {a.get(path, "-")} -> {b.get(path, "-")}')
    print('\n## Variables\n')
    for name in new:
        if name in old and names(old[name]) != names(new[name]):
            print(f'{name}: added {sorted(names(new[name]) - names(old[name]))}, '
                  f'removed {sorted(names(old[name]) - names(new[name]))}')


main()

#!/usr/bin/env python3
"""Create team/ and .claude/ for this workspace from the template in .team/.
Usage (from the workspace root): .team/init.sh [--yes]   --yes takes the defaults without asking."""
import json, os, pathlib, shutil, subprocess, sys

TPL = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path.cwd()
TEAM = ROOT / 'team'
YES = '--yes' in sys.argv
OPTIONAL = ['architect', 'devops', 'fe-lead', 'be-lead']
CORE = ['product-owner', 'resource-manager']
DESC = {'resource-manager': 'Resource Manager: hire-or-reuse decisions and the capacity budget',
        'architect': 'Architect: architecture, conventions, cross-boundary design review',
        'devops': 'DevOps: environments, running apps, resources for teams',
        'fe-lead': 'FE Lead: frontend tasks and decisions', 'be-lead': 'BE Lead: backend tasks and decisions'}


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def ask(question, default):
    if YES:
        return default
    answer = input(f'{question} [{default}]: ').strip()
    return answer or default


def detect_capacity():
    """Suggest limits from this machine: hire above 20 % free memory, stop below 15 %, load limit = cores."""
    total_gb = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / 2**30
    return {'minAvailGb': round(total_gb * .2, 1), 'stopAvailGb': round(total_gb * .15, 1),
            'maxLoad5': os.cpu_count() or 4, 'stopDiskPct': 85}


def write_new(path, text):
    """Never overwrite team data."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def main():
    if TPL.parent != ROOT:
        sys.exit('Run this from the workspace root: .team/init.sh')
    example = json.loads((TPL / 'team.config.example.json').read_text())
    cfg = load(TEAM / 'team.config.json', example)
    local = load(TEAM / 'team.local.json', {})
    chosen = [r for r in OPTIONAL if r in cfg['roles']]
    roles = ask(f'Roles beside {", ".join(CORE)} (comma list of {", ".join(OPTIONAL)})', ','.join(chosen))
    roles = [r.strip() for r in roles.split(',') if r.strip()]
    unknown = sorted(set(roles) - set(OPTIONAL))
    if unknown:
        sys.exit(f'Unknown roles: {", ".join(unknown)}')
    cfg['roles'] = CORE + roles
    for lead in ('fe-lead', 'be-lead'):
        if lead in roles:
            cur = ','.join(cfg['repos'].get(lead, []))
            cfg['repos'][lead] = [x.strip() for x in ask(f'Repositories for {lead}', cur).split(',') if x.strip()]
    for role in roles + ['resource-manager']:
        cfg['models'][role] = ask(f'Model for {role}', cfg['models'][role])
    if 'devops' in roles:
        cfg['devopsPermissions'] = ask('What may DevOps change?', cfg['devopsPermissions'])
    cfg['ceiling'] = int(ask('Most agents running at once', cfg['ceiling']))
    cap = {**detect_capacity(), **local.get('capacity', {})}
    for key in cap:
        cap[key] = float(ask(f'Capacity {key}', cap[key]))
    local = {'capacity': cap, 'boardUrl': ask('Team board URL (empty for none)', local.get('boardUrl', '')),
             'hosts': local.get('hosts', [])}

    TEAM.mkdir(exist_ok=True)
    (TEAM / 'team.config.json').write_text(json.dumps(cfg, indent=2) + '\n')
    (TEAM / 'team.local.json').write_text(json.dumps(local, indent=2) + '\n')
    sk = TPL / 'skeleton'
    write_new(TEAM / 'README.md', (sk / 'README.md').read_text())
    for name in ('roster.md', 'board.md'):
        write_new(TEAM / 'status' / name, (sk / 'status' / name).read_text())
    (TEAM / 'log').mkdir(exist_ok=True)
    (TEAM / 'skills').mkdir(exist_ok=True)
    for role in cfg['roles']:
        base = TEAM / 'roles' / role
        write_new(base / 'handover.md', (sk / 'handover.md').read_text())
        (base / 'skills').mkdir(parents=True, exist_ok=True)
        (base / 'journal').mkdir(exist_ok=True)
        model = cfg['models'].get(role, 'main session')
        repos = ', '.join(cfg['repos'].get(role, [])) or 'as briefed'
        text = (TPL / 'roles' / role / 'profile.md').read_text()
        text = text.replace('{{model}}', model).replace('{{repos}}', repos)
        text = text.replace('{{devopsPermissions}}', cfg['devopsPermissions'])
        write_new(base / 'profile.md', text)

    agents = ROOT / '.claude' / 'agents'
    agents.mkdir(parents=True, exist_ok=True)
    tmpl = (TPL / 'agents' / 'agent.md.tmpl').read_text()
    for role in set(DESC) - set(cfg['roles']):  # a role switched off loses its generated agent
        (agents / f'{role}.md').unlink(missing_ok=True)
    for role in cfg['roles']:
        if role in DESC:
            (agents / f'{role}.md').write_text(tmpl.replace('{{name}}', role).replace(
                '{{description}}', DESC[role]).replace('{{model}}', cfg['models'][role]))
    skills = ROOT / '.claude' / 'skills'
    skills.mkdir(exist_ok=True)
    for skill in (TPL / 'skills').iterdir():
        link = skills / skill.name
        if not link.exists():
            link.symlink_to(os.path.relpath(skill, skills))

    ignore = ROOT / '.gitignore'
    have = ignore.read_text().splitlines() if ignore.exists() else []
    want = ['.team/', '.claude/', 'team/team.local.json', 'team/**/handover.md']
    missing = [w for w in want if w not in have]
    if missing:
        with ignore.open('a') as f:
            f.write('\n# Agent team\n' + '\n'.join(missing) + '\n')
    claude = ROOT / 'CLAUDE.md'
    note = '@.team/docs/team-operating-model.md'
    text = claude.read_text() if claude.exists() else ''
    if note not in text:
        with claude.open('a') as f:
            f.write(f'\n## Agent team\n\nTeam rules: {note}\nTeam data: `team/`. The main session is the Product Owner.\n')
    print('Team ready. Roles:', ', '.join(cfg['roles']))
    print(subprocess.run([str(TPL / 'tools' / 'capacity-check.sh')], capture_output=True, text=True).stdout.strip())


if __name__ == '__main__':
    main()

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
MEMBERS = {'developer': 'Developer: one task, one repository, on a branch, with tests',
           'researcher': 'Researcher: one question answered with sources',
           'auditor': 'Auditor: independent check of finished work, ACCEPT or REJECT',
           'tester': 'Tester: runs suites and reports real results',
           'data-specialist': 'Data Specialist: query analysis, index tests, rebuild plans',
           'observer': 'Observer: reads workspace sources (telemetry, issues, CI, docs) into tickets'}
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
    # /proc/meminfo, not sysconf: in a container with a memory limit, sysconf reports the host's memory.
    with open('/proc/meminfo') as f:
        total_gb = next(int(line.split()[1]) for line in f if line.startswith('MemTotal:')) / 2**20
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
    cfg.setdefault('commands', example.get('commands', {}))
    cfg.setdefault('sources', example.get('sources', []))
    cfg.setdefault('tracker', example.get('tracker', {'provider': 'markdown'}))
    cfg.setdefault('maxRounds', example.get('maxRounds', 3))
    cfg['models'] = {**example['models'], **cfg['models']}  # a role added to the template gets its default model
    # The template release this workspace runs: a tag, or tag-commits-hash between releases.
    version = subprocess.run(['git', '-C', str(TPL), 'describe', '--tags', '--always'], capture_output=True, text=True).stdout.strip()
    cfg['templateVersion'] = version or cfg.get('templateVersion', 'unknown')
    cap = {**detect_capacity(), **local.get('capacity', {})}
    for key in cap:
        cap[key] = float(ask(f'Capacity {key}', cap[key]))
    cap['stopDiskPct'] = int(cap['stopDiskPct'])
    # Keep keys init does not ask about ("worker", written by host-join.sh).
    local = {**local, 'capacity': cap, 'boardUrl': ask('Team board URL (empty for none)', local.get('boardUrl', '')),
             'hosts': local.get('hosts', []),
             'schedule': local.get('schedule', {'enabled': False, 'allowedTools': []})}

    TEAM.mkdir(exist_ok=True)
    (TEAM / 'team.config.json').write_text(json.dumps(cfg, indent=2) + '\n')
    (TEAM / 'team.local.json').write_text(json.dumps(local, indent=2) + '\n')
    sk = TPL / 'skeleton'
    write_new(TEAM / 'README.md', (sk / 'README.md').read_text())
    write_new(TEAM / 'rules.md', (sk / 'rules.md').read_text())
    (TEAM / 'tickets').mkdir(exist_ok=True)
    for name in ('roster.md', 'board.md'):
        write_new(TEAM / 'status' / name, (sk / 'status' / name).read_text())
    (TEAM / 'log').mkdir(exist_ok=True)
    (TEAM / 'skills').mkdir(exist_ok=True)
    (TEAM / 'tools').mkdir(exist_ok=True)
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
    for role in MEMBERS:  # members are hired fresh, but their role keeps skills and a journal
        for sub in ('skills', 'journal'):
            (TEAM / 'roles' / role / sub).mkdir(parents=True, exist_ok=True)

    agents = ROOT / '.claude' / 'agents'
    agents.mkdir(parents=True, exist_ok=True)
    tmpl = (TPL / 'agents' / 'agent.md.tmpl').read_text()
    for role in set(DESC) - set(cfg['roles']):  # a role switched off loses its generated agent
        (agents / f'{role}.md').unlink(missing_ok=True)
    def journal(role):
        """Start and finish lines for the role journal: its long-term memory (team operating model §8)."""
        j = f'team/roles/{role}/journal'
        return (f' Then read {j}/memory.md if it exists and the newest day file in {j}/;'
                ' grep older ones and the archive only when your task touches the same area.',
                f', then append your entry to {j}/YYMMDD.md (.team/templates/journal-entry.md)'
                f' and run `.team/tools/journal-archive.sh {role} --list`: if it lists files, compact and archive'
                ' (team operating model §8)')

    finish = 'Before you stop, append your entry to team/log/YYMMDD.md'
    for role in cfg['roles']:
        if role in DESC:
            base = f'team/roles/{role}'
            read, write = journal(role)
            text = tmpl.replace('{{start}}', f'Read {base}/profile.md, then {base}/handover.md.{read}')
            text = text.replace('{{finish}}', f'{finish}{write}, and replace {base}/handover.md.')
            (agents / f'{role}.md').write_text(text.replace('{{name}}', role).replace(
                '{{description}}', DESC[role]).replace('{{model}}', cfg['models'][role]))
    for role, desc in MEMBERS.items():
        read, write = journal(role)
        text = tmpl.replace('{{start}}', f'Read .team/roles/members/{role}.md, then your brief.{read}')
        text = text.replace('{{finish}}', f'{finish}{write}.')
        (agents / f'{role}.md').write_text(text.replace('{{name}}', role).replace(
            '{{description}}', desc).replace('{{model}}', cfg['models'][role]))
    skills = ROOT / '.claude' / 'skills'
    skills.mkdir(exist_ok=True)
    for skill in (TPL / 'skills').iterdir():
        link = skills / skill.name
        if not link.exists():
            link.symlink_to(os.path.relpath(skill, skills))

    settings = ROOT / '.claude' / 'settings.json'
    data = load(settings, {})
    before = json.dumps(data, sort_keys=True)
    perms = data.setdefault('permissions', {})
    allow, deny = perms.setdefault('allow', []), perms.setdefault('deny', [])
    allow.extend(r for r in [f'Bash(.team/tools/{t})' for t in ('capacity-check.sh', 'journal-archive.sh:*', 'ticket.py:*',
                 'scheduled-check.sh', 'gitlab-pipelines.py:*', 'resource-lease.py:*', 'heavy.sh:*',
                 'template-version.sh')] if r not in allow)
    # Enforced by the harness, not only written in the rules (team operating model §7):
    deny.extend(r for r in ['Read(~/.config/agent-team/**)',  # the owner's GitLab token: tools use it, agents never read it
                            'Read(~/.ssh/**)', 'Read(**/.env)', 'Read(**/.env.*)', 'Read(**/*.pem)', 'Read(**/*.key)',
                            'Edit(.team/**)', 'Write(.team/**)',  # the template is never edited in a workspace
                            'Edit(team/tickets/**)', 'Write(team/tickets/**)']  # tickets change through ticket.py only
                if r not in deny)
    data.setdefault('attribution', {'commit': '', 'pr': ''})  # no AI or co-author lines in commits and PRs
    hooks = data.setdefault('hooks', {})
    for event, matcher, arg in (('PreToolUse', 'Bash|Edit|Write', 'guard'), ('SubagentStart', '', 'start'), ('SubagentStop', '', 'stop')):
        command = f'"$CLAUDE_PROJECT_DIR"/.team/tools/team-hooks.py {arg}'
        entries = hooks.setdefault(event, [])
        if not any(h.get('command') == command for e in entries for h in e.get('hooks', [])):
            entries.append(({'matcher': matcher} if matcher else {}) | {'hooks': [{'type': 'command', 'command': command}]})
    if json.dumps(data, sort_keys=True) != before:
        settings.write_text(json.dumps(data, indent=2) + '\n')

    ignore = ROOT / '.gitignore'
    have = ignore.read_text().splitlines() if ignore.exists() else []
    want = ['.team/', '.claude/', 'team/team.local.json', 'team/**/handover.md', 'team/**/.archive.lock', 'team/.scheduled.lock', 'team/scheduled.out', 'team/.ci-seen.json', 'team/.capacity/']
    missing = [w for w in want if w not in have]
    if missing:
        with ignore.open('a') as f:
            f.write('\n# Agent team\n' + '\n'.join(missing) + '\n')
    attrs = ROOT / '.gitattributes'  # every machine appends to the same log file: merge by keeping both sides
    have = attrs.read_text().splitlines() if attrs.exists() else []
    for union in ('team/log/*.md merge=union', 'team/roles/*/journal/[0-9]*.md merge=union'):
        if union not in have:
            with attrs.open('a') as f:
                f.write(union + '\n')
    identity = subprocess.run(['git', 'config', 'user.email'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if not identity:  # a fresh machine has none, and a worker cannot commit without it
        print('Warning: no git identity here. Set git config user.name and user.email before starting a worker.')
    claude = ROOT / 'CLAUDE.md'
    note = '@.team/docs/team-operating-model.md'
    text = claude.read_text() if claude.exists() else ''
    if note not in text:
        with claude.open('a') as f:
            f.write(f'\n## Agent team\n\nTeam rules: {note}\nThe main session is the Product Owner.\n\n'
                    '| Need | Where |\n|---|---|\n| Roles, templates, shared tools and skills | `.team/` (never edit) |\n'
                    '| Status, roster, board, tickets, log, handovers | `team/` |\n| Workspace skills and tools | `team/skills/`, `team/tools/` |\n')
    rules = '@team/rules.md'
    if rules not in claude.read_text():  # also for a workspace set up before workspace rules existed
        with claude.open('a') as f:
            f.write(f'\nWorkspace rules (they win over the team rules): {rules}\n')
    print(f"Team ready (template {cfg['templateVersion']}). Roles:", ', '.join(cfg['roles']))
    print(subprocess.run([str(TPL / 'tools' / 'capacity-check.sh')], capture_output=True, text=True).stdout.strip())


if __name__ == '__main__':
    main()

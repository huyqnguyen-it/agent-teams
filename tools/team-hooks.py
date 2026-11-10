#!/usr/bin/env python3
"""Claude Code hooks that enforce team rules. init puts them in .claude/settings.json. Costs no tokens.

  team-hooks.py guard   PreToolUse (Bash, Edit, Write): an agent never pushes, tags or stashes; the Auditor
                        edits only team/ files. A headless worker (TEAM_ROLE set) may push its feature branch.
  team-hooks.py start   SubagentStart: ties the hire to its reservation (resource-lease.py bind).
  team-hooks.py stop    SubagentStop: no stop before the log and journal entries and the journal compaction;
                        then the reservation is released.

Only team agents are checked: the agent type, or TEAM_ROLE, must be a folder in team/roles/.
The PO (main session) is not limited here: its gates are the owner's GO and branch protection.
Exit 2 blocks the action and gives the reason to the agent.
"""
import json, os, pathlib, re, subprocess, sys, time

TOOLS = pathlib.Path(__file__).resolve().parent
# A git command at the start of a shell command (not inside a commit message), with its global options.
GIT = re.compile(r'(?:^|[;&|(`]|\$\()\s*(?:\w+=\S*\s+)*git(?:\s+-[cC]\s+\S+|\s+--[\w-]+(?:=\S+)?)*\s+(stash|tag|push)\b([^;&|\n]*)')
TAG_READ = ('-l', '--list', '-n', '--contains', '--no-contains', '--points-at', '--merged', '--no-merged', '--sort', '--column')


def block(reason):
    print(reason, file=sys.stderr)
    sys.exit(2)


def sample():
    """Note this machine's memory and load at most once a minute while team agents work: resource-lease.py learns peaks from it."""
    path = pathlib.Path('team/.capacity/samples.jsonl')
    if path.exists() and time.time() - path.stat().st_mtime < 60:
        return
    mem = dict(line.split(':', 1) for line in open('/proc/meminfo'))
    kb = lambda k: int(mem[k].split()[0])
    used = round((kb('MemTotal') - kb('MemAvailable')) / 2**20, 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as f:
        f.write(json.dumps({'host': 'main', 't': int(time.time()), 'usedGb': used, 'load5': float(open('/proc/loadavg').read().split()[1])}) + '\n')


def guard(data, role, subagent):
    if subagent:
        sample()
    tool, args = data.get('tool_name', ''), data.get('tool_input', {})
    if tool == 'Bash':
        for verb, rest in GIT.findall(args.get('command', '')):
            words = rest.split()
            if verb == 'stash':
                block('Team rule §7.2: never run git stash. Commit to your branch, or ask your lead.')
            if verb == 'tag' and words and not words[0].split('=')[0] in TAG_READ:
                block("Team rule §7.1: only the PO tags, after the owner's GO.")
            if verb == 'push' and subagent:
                block("Team rule §7.1: agents do not push. Report your branch; the PO pushes after the owner's GO.")
            if verb == 'push' and any(w in ('-f', '--force', '--force-with-lease', '--tags', '--mirror', '--delete', '-d', '--all')
                                      or w.startswith(('+', ':')) or w.split(':')[-1] in ('main', 'master') for w in words):
                block('Team rule §7.1: a worker pushes only its own feature branch: never main or master, tags, deletes, or force.')
    elif tool in ('Edit', 'Write') and role == 'auditor':
        path = pathlib.Path(args.get('file_path', '')).resolve()
        if not str(path).startswith(str(pathlib.Path('team').resolve()) + os.sep):
            block('The Auditor never fixes what it finds: report it. You may only write your log and journal under team/.')


def entry_since(path, name, since):
    """True when the file has a '## HH:MM <name...>' entry written at or after the given time."""
    if not path.exists():
        return False
    for hh, mm, who in re.findall(r'^## (\d\d):(\d\d) (\S+)', path.read_text(), re.M):
        if who.startswith(name) and int(hh) * 60 + int(mm) >= since:
            return True
    return False


def stop(data, role):
    leases = pathlib.Path('team/.capacity/leases')
    mine = [json.loads(p.read_text()) for p in sorted(leases.glob('*.json'))] if leases.is_dir() else []
    mine = [l for l in mine if l.get('agentId') == data.get('agent_id')]
    start = time.localtime(mine[0]['start']) if mine else None
    since = start.tm_hour * 60 + start.tm_min if start and start.tm_yday == time.localtime().tm_yday else 0
    day = time.strftime('%y%m%d')
    missing = []
    if not entry_since(pathlib.Path(f'team/log/{day}.md'), role, since):
        missing.append(f'your entry in team/log/{day}.md (.team/templates/work-report.md)')
    if not entry_since(pathlib.Path(f'team/roles/{role}/journal/{day}.md'), role, since):
        missing.append(f'your entry in team/roles/{role}/journal/{day}.md (.team/templates/journal-entry.md)')
    listed = subprocess.run([str(TOOLS / 'journal-archive.sh'), role, '--list'], capture_output=True, text=True).stdout.strip()
    if listed:
        missing.append(f'the journal compaction: .team/tools/journal-archive.sh {role} --list shows files (team operating model §8)')
    if missing and not data.get('stop_hook_active'):  # ask once; a second stop always goes through
        block('Before you stop, write: ' + '; '.join(missing) + '. Then stop.')
    subprocess.run([str(TOOLS / 'resource-lease.py'), 'release', '--id', data.get('agent_id', '')], capture_output=True)


def main():
    event = sys.argv[1] if len(sys.argv) > 1 else ''
    os.chdir(os.environ.get('CLAUDE_PROJECT_DIR', '.'))
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    subagent = bool(data.get('agent_type'))
    role = data.get('agent_type') or os.environ.get('TEAM_ROLE', '')
    if not role or not pathlib.Path('team/roles', role).is_dir():
        return
    if event == 'guard':
        guard(data, role, subagent)
    elif event == 'start':
        out = subprocess.run([str(TOOLS / 'resource-lease.py'), 'bind', role, data.get('agent_id', '')],
                             capture_output=True, text=True).stdout.strip()
        if out == 'none':
            print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SubagentStart', 'additionalContext':
                  'Note: this hire has no reservation (resource-lease.py reserve). Avoid heavy commands until the PO reserves one.'}}))
    elif event == 'stop':
        stop(data, role)


if __name__ == '__main__':
    main()

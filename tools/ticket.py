#!/usr/bin/env python3
"""Team tickets: one command for every agent, whatever the backend.

Default backend: Markdown files in team/tickets/<id>.md (no setup).
If team/team.config.json has "tracker": {"provider": "<name>", "commands": {...}, "states": {...}},
each action runs that owner-approved command instead (values are shell-quoted).

  ticket.py new --title T --kind K --by AGENT [--source S] [--owner ROLE] [--body TEXT | --body-file F]
  ticket.py list [--state S] [--owner ROLE]
  ticket.py show ID
  ticket.py find SOURCE                      open tickets for this source ID (repeat check)
  ticket.py move ID STATE --by AGENT [--note N] [--owner ROLE] [--plan P]
  ticket.py comment ID --by AGENT --note N
  ticket.py fail ID --by AGENT --note N         record a failed round; at maxRounds the ticket goes to waiting

Flow (team operating model §6, Tickets): triage -> accepted | waiting | rejected;
waiting -> accepted | rejected; accepted -> in-progress | triage; in-progress -> resolved | triage | waiting;
resolved -> closed | in-progress. Closed and rejected tickets move to team/tickets/archive/YYMM/.
A failed round (lead's review or the Auditor sends work back, or BLOCKED) is recorded with `fail`. At maxRounds
(team.config.json, default 3) the ticket goes to waiting for the owner, and `move ... in-progress` is refused until the
owner allows more rounds: then the PO moves it with --owner-ok, which starts the count again.
Exit codes: 0 ok, 2 bad input, 3 an open ticket already has this source, 5 retry limit reached.
"""
import argparse, datetime, json, os, pathlib, secrets, shlex, subprocess, sys

DIR = pathlib.Path(os.environ.get('TEAM_TICKETS', 'team/tickets'))
CFG = pathlib.Path(os.environ.get('TEAM_CONFIG', 'team/team.config.json'))
KINDS = ('bug', 'requirement', 'docs', 'ops', 'task', 'template')  # template: a proposal for the team template
FLOW = {'triage': {'accepted', 'waiting', 'rejected'}, 'waiting': {'accepted', 'rejected'},
        'accepted': {'in-progress', 'triage'}, 'in-progress': {'resolved', 'triage', 'waiting'},
        'resolved': {'closed', 'in-progress'}}
DONE = {'closed', 'rejected'}
FIELDS = ('id', 'title', 'kind', 'state', 'source', 'owner', 'plan', 'rounds', 'created')


def fail(msg, code=2):
    print(msg, file=sys.stderr)
    sys.exit(code)


def now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')


def one_line(text):
    return ' '.join(str(text or '').split())


# ---- Markdown backend -------------------------------------------------------

def read(path):
    """Split a ticket file into its header fields and its body."""
    text = path.read_text()
    _, head, body = text.split('---\n', 2)
    meta = dict(line.split(': ', 1) if ': ' in line else (line.rstrip(':'), '') for line in head.splitlines())
    return meta, body


def write(path, meta, body):
    head = ''.join(f'{k}: {meta.get(k, "")}\n' for k in FIELDS)
    path.write_text(f'---\n{head}---\n{body}')


def open_tickets():
    return sorted(DIR.glob('*.md')) if DIR.is_dir() else []


def locate(tid):
    path = DIR / f'{tid}.md'
    if path.exists():
        return path
    found = sorted(DIR.glob(f'archive/*/{tid}.md'))
    return found[0] if found else fail(f'no ticket {tid}')


def md_new(a):
    if a.source and md_find(a.source, quiet=True):
        md_find(a.source)
        sys.exit(3)
    body = pathlib.Path(a.body_file).read_text() if a.body_file else (a.body or '')
    tid = f'{datetime.date.today():%y%m%d}-{secrets.token_hex(2)}'
    meta = {'id': tid, 'title': one_line(a.title), 'kind': a.kind, 'state': 'triage', 'source': one_line(a.source),
            'owner': one_line(a.owner), 'plan': '', 'created': now()}
    DIR.mkdir(parents=True, exist_ok=True)
    write(DIR / f'{tid}.md', meta, f'\n{body.strip()}\n\n## History\n- {now()} {a.by}: created (triage)\n')
    print(tid)


def md_list(a):
    for path in open_tickets():
        m, _ = read(path)
        if (not a.state or m['state'] == a.state) and (not a.owner or m['owner'] == a.owner):
            print(f"{m['id']}  {m['state']:<11} {m['kind']:<11} {m['owner'] or '-':<14} {m['title']}")


def md_find(source, quiet=False):
    hits = [read(p)[0] for p in open_tickets() if read(p)[0].get('source') == source]
    if not quiet:
        for m in hits:
            print(f"{m['id']}  {m['state']}  {m['title']}")
    return hits


def md_move(a):
    path = locate(a.id)
    meta, body = read(path)
    if a.state not in FLOW.get(meta['state'], set()):
        fail(f"{a.id} is {meta['state']}: may go to {', '.join(sorted(FLOW.get(meta['state'], []))) or 'nowhere'}")
    rounds, limit = int(meta.get('rounds') or 0), max_rounds()
    if a.state == 'in-progress' and rounds >= limit:
        if not a.owner_ok:
            fail(f"{a.id} failed {rounds} rounds (limit {limit}): the owner decides. With the owner's answer, add --owner-ok", 5)
        meta['rounds'] = '0'
        a.note = ('owner allowed more rounds. ' + (a.note or '')).strip()
    meta['state'] = a.state
    meta['owner'] = one_line(a.owner) or meta['owner']
    meta['plan'] = one_line(a.plan) or meta['plan']
    note = f': {one_line(a.note)}' if a.note else ''
    write(path, meta, body.rstrip('\n') + f'\n- {now()} {a.by}: {a.state}{note}\n')
    if a.state in DONE:
        dest = DIR / 'archive' / a.id[:4]
        dest.mkdir(parents=True, exist_ok=True)
        path.rename(dest / path.name)
    print(f'{a.id} {a.state}')


def max_rounds():
    return int((json.loads(CFG.read_text()) if CFG.exists() else {}).get('maxRounds', 3))


def md_fail(a):
    path = locate(a.id)
    meta, body = read(path)
    rounds, limit = int(meta.get('rounds') or 0) + 1, max_rounds()
    meta['rounds'] = str(rounds)
    body = body.rstrip('\n') + f'\n- {now()} {a.by}: failed round {rounds}/{limit}: {one_line(a.note)}\n'
    if rounds >= limit and meta['state'] == 'in-progress':
        meta['state'] = 'waiting'
        body += f'- {now()} {a.by}: waiting: retry limit reached, the owner decides\n'
        print(f'{a.id} RETRY LIMIT: waiting. The PO asks the owner on the board: retry, change the task, or drop it.')
    else:
        print(f'{a.id} failed round {rounds}/{limit}')
    write(path, meta, body)


def md_comment(a):
    path = locate(a.id)
    meta, body = read(path)
    write(path, meta, body.rstrip('\n') + f'\n- {now()} {a.by}: {one_line(a.note)}\n')
    print(f'{a.id} commented')


# ---- Provider backend -------------------------------------------------------

def provider(tracker, action, a):
    """Run the owner-approved command for this action, with every value shell-quoted."""
    template = tracker.get('commands', {}).get(action)
    if not template:
        fail(f"tracker '{tracker['provider']}' has no '{action}' command in team.config.json")
    values = {k: v for k, v in vars(a).items() if isinstance(v, str)}
    if 'state' in values:
        values['state'] = tracker.get('states', {}).get(values['state'], values['state'])
    if action == 'new' and not a.body_file:
        tmp = pathlib.Path(os.environ.get('TMPDIR', '/tmp')) / f'ticket-{secrets.token_hex(4)}.md'
        tmp.write_text(a.body or '')
        values['body_file'] = str(tmp)
    command = template.format_map({k: shlex.quote(v) for k, v in values.items()} | {'file': shlex.quote(values.get('body_file', ''))})
    code = subprocess.run(command, shell=True).returncode
    if action == 'new' and not a.body_file:
        tmp.unlink(missing_ok=True)
    sys.exit(code)


def main():
    p = argparse.ArgumentParser(description='Team tickets', formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='action', required=True)
    n = sub.add_parser('new')
    n.add_argument('--title', required=True)
    n.add_argument('--kind', required=True, choices=KINDS)
    n.add_argument('--by', required=True)
    n.add_argument('--source', default='')
    n.add_argument('--owner', default='')
    n.add_argument('--body', default='')
    n.add_argument('--body-file', default='')
    ls = sub.add_parser('list')
    ls.add_argument('--state', default='')
    ls.add_argument('--owner', default='')
    sub.add_parser('show').add_argument('id')
    sub.add_parser('find').add_argument('source')
    mv = sub.add_parser('move')
    mv.add_argument('id')
    mv.add_argument('state', choices=sorted(set().union(*FLOW.values())))
    mv.add_argument('--by', required=True)
    for opt in ('--note', '--owner', '--plan'):
        mv.add_argument(opt, default='')
    mv.add_argument('--owner-ok', action='store_true')
    fl = sub.add_parser('fail')
    fl.add_argument('id')
    fl.add_argument('--by', required=True)
    fl.add_argument('--note', required=True)
    c = sub.add_parser('comment')
    c.add_argument('id')
    c.add_argument('--by', required=True)
    c.add_argument('--note', required=True)
    a = p.parse_args()

    tracker = json.loads(CFG.read_text()).get('tracker', {}) if CFG.exists() else {}
    if tracker.get('provider', 'markdown') != 'markdown':
        if a.action == 'fail':  # a provider has no round count: the lead counts the FAILED ROUND comments
            a.action, a.note = 'comment', f'FAILED ROUND: {a.note}'
        provider(tracker, a.action, a)
    if a.action == 'show':
        print(locate(a.id).read_text(), end='')
    elif a.action == 'find':
        md_find(a.source)
    else:
        {'new': md_new, 'list': md_list, 'move': md_move, 'comment': md_comment, 'fail': md_fail}[a.action](a)


if __name__ == '__main__':
    main()

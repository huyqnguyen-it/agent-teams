#!/usr/bin/env python3
"""Place and reserve agents across machines. Costs no tokens.

  resource-lease.py status                      one line per host: status, leases, free slots; then PICK <host>|none
  resource-lease.py reserve AGENT ROLE [--heavy] [--host H] [--minutes M] [--owner-ok]
                                                HIRE AGENT on HOST (a lease is written), or WAIT <reason> (exit 4)
  resource-lease.py release AGENT | --id AGENT_ID   give the reservation back and learn the agent's real peak
  resource-lease.py bind ROLE AGENT_ID           tie the newest unbound lease of ROLE on main to a started subagent
  resource-lease.py list                         active leases

Hosts: "main" (this machine) and every team.local.json host whose "use" has "worker", read with
capacity-check.sh --json (over ssh for other hosts). A host fits a hire when, after the unused part of
its leases and its minAvailGb reserve, it has the estimated peak memory and load free, has fewer than
maxAgents leases, and is GREEN (YELLOW only with --owner-ok, which the owner gives for one task).
The team ceiling (team.config.json) caps active leases across all hosts.
The estimate is the 90th percentile of past peaks for the role (and --heavy), else the defaults.
Only the PO reserves; leases live on the main machine in team/.capacity/ (ignored by git).
"""
import argparse, concurrent.futures, contextlib, fcntl, json, math, os, pathlib, subprocess, sys, time

TOOLS = pathlib.Path(__file__).resolve().parent
DIR = pathlib.Path('team/.capacity')
LEASES, SAMPLES, PEAKS = DIR / 'leases', DIR / 'samples.jsonl', DIR / 'peaks.jsonl'
DEFAULTS = {'perAgentGb': 2.0, 'perAgentLoad': 1.0, 'heavyGb': 4.0, 'heavyLoad': 2.0, 'maxAgents': 4}
WEEK = 7 * 86400


def load(path, default):
    try:
        return json.loads(pathlib.Path(path).read_text())
    except (OSError, ValueError):
        return default


def settings():
    local = load('team/team.local.json', {})
    cap = DEFAULTS | local.get('capacity', {})
    hosts = [{'name': 'main', 'maxAgents': cap['maxAgents']}]
    hosts += [h | {'maxAgents': h.get('maxAgents', cap['maxAgents'])} for h in local.get('hosts', []) if 'worker' in h.get('use', [])]
    return cap, hosts, load('team/team.config.json', {}).get('ceiling', 2)


def measure(host):
    """Read one host's capacity; None when it cannot be reached."""
    cmd = [str(TOOLS / 'capacity-check.sh'), '--json'] if host['name'] == 'main' else \
        ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', host['ssh'], f"cd {host['path']} && .team/tools/capacity-check.sh --json"]
    try:
        m = json.loads(subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout)
    except (ValueError, subprocess.TimeoutExpired, OSError):
        return None
    m['usedGb'] = round(m['totalGb'] - m['availGb'], 1)
    append(SAMPLES, {'host': host['name'], 't': int(time.time()), 'usedGb': m['usedGb'], 'load5': m['load5']})
    return m


def append(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as f:
        f.write(json.dumps(row) + '\n')


def rows(path, since=0):
    out = []
    if path.exists():
        for line in path.read_text().splitlines():
            with contextlib.suppress(ValueError):
                r = json.loads(line)
                if r.get('t', 0) >= since:
                    out.append(r)
    return out


def estimate(cap, role, heavy):
    """Peak memory and load one agent of this role needs: p90 of its last 20 peaks, else the defaults."""
    past = [r for r in rows(PEAKS) if r['role'] == role and r['heavy'] == heavy][-20:]
    if len(past) < 3:
        return (cap['heavyGb'], cap['heavyLoad']) if heavy else (cap['perAgentGb'], cap['perAgentLoad'])
    p90 = lambda xs: sorted(xs)[min(len(xs) - 1, math.ceil(.9 * len(xs)) - 1)]
    return max(.5, p90([r['gb'] for r in past])), max(.2, p90([r['load'] for r in past]))


def leases():
    now = time.time()
    active = []
    for path in sorted(LEASES.glob('*.json')) if LEASES.is_dir() else []:
        lease = load(path, None)
        if not lease or lease['expires'] < now:  # a crashed agent cannot hold room forever
            path.unlink(missing_ok=True)
        else:
            active.append(lease)
    return active


def free(host, m, active, cap):
    """Memory and load still free on a host once its leases reach their peaks."""
    mine = [l for l in active if l['host'] == host['name']]
    unspent_gb = unspent_load = 0.0
    if mine:
        first = min(mine, key=lambda l: l['start'])
        unspent_gb = max(0, sum(l['gb'] for l in mine) - max(0, m['usedGb'] - first['startUsed']))
        unspent_load = max(0, sum(l['load'] for l in mine) - max(0, m['load5'] - first['startLoad']))
    return m['availGb'] - unspent_gb - m['minAvailGb'], m['maxLoad5'] - m['load5'] - unspent_load, len(mine)


def survey(hosts):
    with concurrent.futures.ThreadPoolExecutor(len(hosts)) as pool:
        return dict(zip([h['name'] for h in hosts], pool.map(measure, hosts)))


def choose(hosts, seen, active, cap, gb, load_, heavy, owner_ok):
    fits = []
    for h in hosts:
        m = seen.get(h['name'])
        if not m or m['status'] == 'RED' or (m['status'] == 'YELLOW' and not owner_ok):
            continue
        fgb, fload, n = free(h, m, active, cap)
        if n < h['maxAgents'] and fgb >= gb and fload >= load_:
            remote_first = heavy and h['name'] != 'main'  # heavy work leaves the main machine light when it can
            fits.append((not remote_first, h['name'] != 'main', -min(fgb / gb, fload / load_), h['name']))
    return sorted(fits)[0][-1] if fits else None


def status(a):
    cap, hosts, ceiling = settings()
    active, seen = leases(), survey(hosts)
    gb, load_ = estimate(cap, 'developer', False)
    for h in hosts:
        m = seen[h['name']]
        if not m:
            print(f"{time.strftime('%H:%M')} RED {h['name']} unreachable")
            continue
        fgb, fload, n = free(h, m, active, cap)
        slots = max(0, min(math.floor(fgb / gb), math.floor(fload / load_), h['maxAgents'] - n))
        print(f"{time.strftime('%H:%M')} {m['status']} {h['name']} leases={n}/{h['maxAgents']} slots={slots} "
              f"freeG={fgb:.1f} freeLoad={fload:.1f} perAgent={gb:.1f}G/{load_:.1f}")
    pick = None if len(active) >= ceiling else choose(hosts, seen, active, cap, gb, load_, False, False)
    print(f"TEAM leases={len(active)}/{ceiling} PICK {pick or 'none'}")


def reserve(a):
    cap, hosts, ceiling = settings()
    if a.host:
        hosts = [h for h in hosts if h['name'] == a.host] or sys.exit(f'WAIT unknown host {a.host}')
    active = leases()
    if any(l['agent'] == a.agent for l in active):
        sys.exit(f'{a.agent} already holds a lease: release it first')
    if len(active) >= ceiling:
        print(f'WAIT team ceiling {ceiling} reached')
        sys.exit(4)
    gb, load_ = estimate(cap, a.role, a.heavy)
    seen = survey(hosts)
    host = choose(hosts, seen, active, cap, gb, load_, a.heavy, a.owner_ok)
    if not host:
        print(f'WAIT no host has {gb:.1f}G and load {load_:.1f} free (resource-lease.py status)')
        sys.exit(4)
    now, m = time.time(), seen[host]
    lease = {'agent': a.agent, 'role': a.role, 'heavy': a.heavy, 'host': host, 'gb': round(gb, 1), 'load': round(load_, 1),
             'start': now, 'expires': now + a.minutes * 60, 'startUsed': m['usedGb'], 'startLoad': m['load5'], 'agentId': ''}
    LEASES.mkdir(parents=True, exist_ok=True)
    (LEASES / f'{a.agent}.json').write_text(json.dumps(lease))
    print(f"HIRE {a.agent} on {host} (reserved {gb:.1f}G, load {load_:.1f}, expires {time.strftime('%H:%M', time.localtime(lease['expires']))})")


def release(a):
    for lease in leases():
        if lease['agent'] == a.agent or (a.id and lease['agentId'] == a.id):
            during = [r for r in rows(SAMPLES, lease['start']) if r['host'] == lease['host']]
            if lease['host'] == 'main':
                m = measure({'name': 'main'})
                during += [{'usedGb': m['usedGb'], 'load5': m['load5']}] if m else []
            if len(during) >= 3:  # what this agent really used, shared with the leases beside it; too few samples teach nothing
                others = 1 + sum(1 for l in leases() if l['host'] == lease['host'] and l['agent'] != lease['agent'])
                gb = max(0, max(r['usedGb'] for r in during) - lease['startUsed']) / others
                ld = max(0, max(r['load5'] for r in during) - lease['startLoad']) / others
                append(PEAKS, {'t': int(time.time()), 'role': lease['role'], 'heavy': lease['heavy'], 'gb': round(gb, 2), 'load': round(ld, 2)})
            (LEASES / f"{lease['agent']}.json").unlink(missing_ok=True)
            print(f"released {lease['agent']} on {lease['host']}")
            return
    print('no lease to release')


def bind(a):
    unbound = [l for l in leases() if l['host'] == 'main' and l['role'] == a.role and not l['agentId']]
    if any(l['agentId'] == a.id for l in leases()):
        print('bound')
    elif unbound:
        lease = max(unbound, key=lambda l: l['start'])
        lease['agentId'] = a.id
        (LEASES / f"{lease['agent']}.json").write_text(json.dumps(lease))
        print(f"bound {lease['agent']}")
    else:
        print('none')


def trim():
    """Keep a week of samples and the last 500 peaks."""
    for path, keep in ((SAMPLES, rows(SAMPLES, time.time() - WEEK)), (PEAKS, rows(PEAKS)[-500:])):
        if path.exists():
            path.write_text(''.join(json.dumps(r) + '\n' for r in keep))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('status')
    sub.add_parser('list')
    r = sub.add_parser('reserve')
    r.add_argument('agent'), r.add_argument('role')
    r.add_argument('--heavy', action='store_true'), r.add_argument('--owner-ok', action='store_true')
    r.add_argument('--host', default=''), r.add_argument('--minutes', type=int, default=90)
    rel = sub.add_parser('release')
    rel.add_argument('agent', nargs='?', default=''), rel.add_argument('--id', default='')
    b = sub.add_parser('bind')
    b.add_argument('role'), b.add_argument('id')
    a = p.parse_args()
    DIR.mkdir(parents=True, exist_ok=True)
    with (DIR / 'lock').open('w') as lock:  # one decision at a time: two hires never take the same room
        fcntl.flock(lock, fcntl.LOCK_EX)
        if a.cmd == 'list':
            for l in leases():
                print(f"{l['agent']} {l['role']} on {l['host']} {l['gb']}G load {l['load']} until {time.strftime('%H:%M', time.localtime(l['expires']))}")
        else:
            {'status': status, 'reserve': reserve, 'release': release, 'bind': bind}[a.cmd](a)
        trim()


if __name__ == '__main__':
    main()

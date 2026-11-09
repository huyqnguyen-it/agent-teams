#!/usr/bin/env python3
"""GitLab CI results for the team, read-only. Costs no tokens.

  gitlab-pipelines.py check <project> [<project> ...]   print pipelines finished since the last check, one per line
  gitlab-pipelines.py show <project> <ref>              print the latest pipeline of a branch or tag, and its failed jobs
  gitlab-pipelines.py whoami                            check the connection: prints the user the token belongs to

<project> is the path, e.g. group/service. GITLAB_URL and GITLAB_TOKEN (read_api only) come from the
environment, or else from ~/.config/agent-team/gitlab.env, which the owner writes with gitlab-setup.sh.
The token is never printed.
`check` is meant as a source "check" command (team operating model §6, Signals); it remembers what it
has printed in team/.ci-seen.json (ignored by git), so each result is reported once.
Exit codes: 0 ok, 1 GitLab could not be read, 2 bad input.
"""
import json, os, pathlib, sys, urllib.error, urllib.parse, urllib.request

def load_env_file():
    """Fill GITLAB_URL, GITLAB_TOKEN and SSL_CERT_FILE from the owner's file, unless already set."""
    path = pathlib.Path(os.environ.get('GITLAB_ENV_FILE', pathlib.Path.home() / '.config/agent-team/gitlab.env'))
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        key, sep, value = raw.strip().partition('=')
        if sep and key in ('GITLAB_URL', 'GITLAB_TOKEN', 'SSL_CERT_FILE') and not os.environ.get(key):
            os.environ[key] = value.strip()


load_env_file()
URL = os.environ.get('GITLAB_URL', 'https://gitlab.com').rstrip('/')
SEEN = pathlib.Path(os.environ.get('CI_SEEN', 'team/.ci-seen.json'))
FINISHED = {'success', 'failed', 'canceled'}


def api(path):
    """GET one GitLab API page; the token goes in a header, never in output."""
    token = os.environ.get('GITLAB_TOKEN')
    if not token:
        sys.exit('No GitLab token: the owner runs .team/tools/gitlab-setup.sh in their own terminal')
    req = urllib.request.Request(f'{URL}/api/v4/{path}', headers={'PRIVATE-TOKEN': token})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except (urllib.error.URLError, TimeoutError) as e:
        print(f'GitLab read failed for {path.split("?")[0]}: {getattr(e, "code", "")} {getattr(e, "reason", e)}', file=sys.stderr)
        sys.exit(1)


def project(path):
    return f'projects/{urllib.parse.quote(path, safe="")}'


def line(proj, p):
    return f"{proj} #{p['id']} {p['status']} ref={p['ref']} sha={p['sha'][:8]} {p.get('web_url', '')}"


def check(projects):
    seen = json.loads(SEEN.read_text()) if SEEN.exists() else {}
    for proj in projects:
        pipes = api(f'{project(proj)}/pipelines?order_by=id&sort=desc&per_page=50')
        done = [p for p in pipes if p['status'] in FINISHED]
        # Remember reported IDs, not the highest one: a slow pipeline can finish after a newer one.
        reported = set(seen.get(proj, []))
        if proj in seen:  # the first run only records history, so old results are not reported
            for p in sorted(done, key=lambda p: p['id']):
                if p['id'] not in reported:
                    print(line(proj, p))
        reported |= {p['id'] for p in done}
        seen[proj] = sorted(reported)[-200:]
    SEEN.parent.mkdir(parents=True, exist_ok=True)
    SEEN.write_text(json.dumps(seen, indent=2) + '\n')


def show(proj, ref):
    pipes = api(f'{project(proj)}/pipelines?ref={urllib.parse.quote(ref)}&order_by=id&sort=desc&per_page=1')
    if not pipes:
        print(f'{proj} ref={ref}: no pipeline')
        return
    p = pipes[0]
    print(line(proj, p))
    if p['status'] == 'failed':
        for j in api(f"{project(proj)}/pipelines/{p['id']}/jobs?scope[]=failed&per_page=50"):
            print(f"  failed job: {j['stage']}/{j['name']} {j.get('web_url', '')}")


def main():
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == 'check':
        check(args[1:])
    elif len(args) == 3 and args[0] == 'show':
        show(args[1], args[2])
    elif args == ['whoami']:
        print(f"GitLab {URL}: connected as {api('user').get('username', '?')}")
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Build a self-contained HTML page from a Markdown guide. The .md stays the source; rerun after each edit.
Usage: guide-md-to-html.py <guide.md> [out.html] [--config guide.config.json]
Without a config every `##` section sits in one menu group. Config keys, all optional:
  groups: [{"name": "Start", "sections": ["Revision"]}]   menu groups, by section heading
  rest:   "Services"     group for sections not listed; its place is the "rest" entry's position after `restAfter`
  restAfter: 2           how many groups come before the rest group
  checklist: "Runbook"   section whose first table gets checkboxes and a progress bar
A sibling <guide>.config.json is used when --config is absent."""
import html, json, pathlib, re, sys
import markdown

CSS = '''
:root{--bg:#f1f4f5;--surface:#fff;--raised:#f7f9fa;--ink:#17242a;--muted:#56666f;--line:#d5dee1;--accent:#0f6b78;--soft:#dff0f2;--on:#fff;--req:#a3480f;--req-soft:#fcecdd;--ok:#1f7a4d;--ok-soft:#e1f3e9;
--body:"Segoe UI",system-ui,-apple-system,Roboto,sans-serif;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,"DejaVu Sans Mono",monospace}
@media (prefers-color-scheme:dark){:root{--bg:#0e1417;--surface:#172126;--raised:#1d292f;--ink:#e2eaed;--muted:#9bacb5;--line:#2a373e;--accent:#62c4d4;--soft:#14323a;--on:#0e1417;--req:#f2a766;--req-soft:#3a2614;--ok:#6fd09b;--ok-soft:#163126;color-scheme:dark}}
*{box-sizing:border-box}html,body{height:100%;overflow:hidden}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 var(--body)}
/* The page scrolls inside <main>, not the window: the window does not scroll inside the Artifact viewer frame. */
.app{display:grid;grid-template-columns:272px minmax(0,1fr);height:100%}
nav{height:100%;overflow:auto;background:var(--surface);border-right:1px solid var(--line);padding:14px}
nav h1{font-size:1.05rem;margin:0}nav .ver{color:var(--muted);font-size:.78rem;margin-bottom:10px}
input[type=search]{width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink);font:inherit}
.toggle{display:flex;gap:6px;align-items:center;margin:8px 0;color:var(--muted);font-size:.82rem}
nav h2{font-size:.68rem;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin:14px 0 4px}
nav a{display:block;padding:3px 8px;border-radius:5px;color:var(--ink);text-decoration:none;font-size:.86rem;overflow-wrap:anywhere}
nav a:hover{background:var(--soft)}nav a.on{background:var(--accent);color:var(--on)}
main{height:100%;overflow:auto;padding:16px 22px 80px;min-width:0;display:grid;gap:14px;align-content:start}
section{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 18px;min-width:0}
section[hidden]{display:none}
section h2{font-size:1.2rem;margin:0 0 8px;overflow-wrap:anywhere}section h3{font-size:.98rem;margin:16px 0 6px}
p{margin:6px 0}ul{margin:6px 0;padding-left:20px}
code{font-family:var(--mono);font-size:.86em;background:var(--soft);padding:1px 4px;border-radius:4px;overflow-wrap:anywhere}
.tbl{overflow-x:auto;margin:8px 0}table{border-collapse:collapse;width:100%;font-size:.84rem}
th,td{text-align:left;vertical-align:top;padding:6px 9px;border-bottom:1px solid var(--line)}
th{position:sticky;top:0;background:var(--raised);font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);white-space:nowrap}
tr.req td:first-child{box-shadow:inset 3px 0 0 var(--req)}
tr[hidden]{display:none}
.y{display:inline-block;font-size:.68rem;font-weight:700;text-transform:uppercase;color:var(--req);background:var(--req-soft);padding:1px 7px;border-radius:999px}
.pre{position:relative}pre{font:12.5px/1.4 var(--mono);background:var(--raised);border:1px solid var(--line);border-radius:8px;padding:10px 12px;overflow-x:auto;margin:8px 0}
pre code{background:none;padding:0;font-size:inherit;overflow-wrap:normal}
.copy{position:absolute;top:6px;right:6px;font:inherit;font-size:.72rem;padding:2px 8px;border:1px solid var(--line);border-radius:5px;background:var(--surface);color:var(--ink);cursor:pointer}
#runbook tr.done td{color:var(--muted);text-decoration:line-through}#runbook tr.done td:first-child{text-decoration:none}
#runbook input{width:16px;height:16px;vertical-align:-3px;margin-right:6px}
.prog{height:6px;background:var(--line);border-radius:3px;overflow:hidden;margin:6px 0}.prog i{display:block;height:100%;width:0;background:var(--ok)}
.progt{color:var(--muted);font-size:.8rem}
.none{color:var(--muted);padding:20px}
del{color:var(--muted)}a{color:var(--accent)}:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (max-width:900px){.app{display:flex;flex-direction:column}nav{flex:none;height:auto;max-height:45vh;border-right:0;border-bottom:1px solid var(--line)}main{flex:1;min-height:0;height:auto;padding:12px}}
@media print{html,body{height:auto;overflow:visible}nav,.copy{display:none}.app{display:block;height:auto}main{height:auto;overflow:visible}section{break-inside:avoid;border:0}}
'''

JS = r'''
const $$=(s,r=document)=>[...r.querySelectorAll(s)];
const store={get(k){try{return JSON.parse(localStorage.getItem(k))}catch(e){return null}},set(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}};
$$('table').forEach(t=>{const w=document.createElement('div');w.className='tbl';t.replaceWith(w);w.append(t);
  const hs=$$('th',t).map(h=>h.textContent.trim().toLowerCase());const i=hs.indexOf('required');
  if(i>=0)$$('tbody tr',t).forEach(r=>{const c=r.cells[i];if(c&&/^yes/i.test(c.textContent.trim())){r.classList.add('req');c.innerHTML='<span class="y">yes</span>'}})});
$$('pre').forEach(p=>{const w=document.createElement('div');w.className='pre';p.replaceWith(w);w.append(p);
  if(p.textContent.split('\n').length>30&&/[┌│]/.test(p.textContent))return;
  const b=document.createElement('button');b.className='copy';b.type='button';b.textContent='Copy';
  b.onclick=async()=>{try{await navigator.clipboard.writeText(p.textContent);b.textContent='Copied'}catch(e){b.textContent='Select text'}setTimeout(()=>b.textContent='Copy',1500)};w.append(b)});
const secs=$$('main section'),links=$$('nav a[href^="#"]');
const byName={};secs.forEach(s=>byName[s.querySelector('h2').textContent.trim().toLowerCase()]=s.id);
const rb=$('#__CHECKLIST__');
function $(s){return document.querySelector(s)}
if(rb){const key='guide-runbook-'+document.title;const saved=store.get(key)||{};const rows=$$('tbody tr',rb);
  const bar=document.createElement('div');bar.innerHTML='<div class="prog"><i></i></div><div class="progt"></div>';rb.querySelector('.tbl').before(bar);
  const up=()=>{const n=rows.filter(r=>r.classList.contains('done')).length;bar.querySelector('i').style.width=(100*n/rows.length)+'%';bar.querySelector('.progt').textContent=n+' of '+rows.length+' steps done (saved in this browser)'};
  rows.forEach(r=>{const n=r.cells[0].textContent.trim(),c=document.createElement('input');c.type='checkbox';c.id='step-'+n;c.setAttribute('aria-label','Step '+n+' done');c.checked=!!saved[n];r.classList.toggle('done',c.checked);
    c.onchange=()=>{saved[n]=c.checked;r.classList.toggle('done',c.checked);store.set(key,saved);up()};r.cells[0].prepend(c);
    const cell=r.cells[r.cells.length-1];const parts=cell.textContent.split(',').map(x=>x.trim());
    if(parts.some(p=>byName[p.toLowerCase()])){cell.replaceChildren();parts.forEach((p,i)=>{if(i)cell.append(', ');const id=byName[p.toLowerCase()];if(id){const a=document.createElement('a');a.href='#'+id;a.textContent=p;cell.append(a)}else cell.append(p)})}});
  up()}
const q=$('#q'),ro=$('#ro'),none=$('#none');
function apply(){const t=q.value.trim().toLowerCase(),r=ro.checked;let any=false;
  secs.forEach(s=>{const name=s.textContent.toLowerCase();let hit=!t||name.includes(t);
    const tr=$$('tbody tr',s);let rowHit=false;
    tr.forEach(x=>{const isEnv=x.closest('table').querySelector('th')&&$$('th',x.closest('table')).some(h=>/required/i.test(h.textContent));
      let show=true;if(t&&!s.querySelector('h2').textContent.toLowerCase().includes(t))show=x.textContent.toLowerCase().includes(t);
      if(r&&isEnv&&!x.classList.contains('req'))show=false;x.hidden=!show;if(show)rowHit=true});
    const vis=hit&&(!t||rowHit||!tr.length||name.includes(t));s.hidden=!vis;if(vis)any=true;
    const l=links.find(a=>a.hash==='#'+s.id);if(l)l.hidden=!vis});
  none.hidden=any}
q.oninput=apply;ro.onchange=apply;
// Menu: jump at once, mark the chosen item, and keep the mark in step with the scroll position.
const mark=id=>links.forEach(a=>{const on=a.hash==='#'+id;a.classList.toggle('on',on);if(on)a.scrollIntoView({block:'nearest'})});
let chosen=null;
const main=$('main');
const topOf=()=>main.getBoundingClientRect().top;
const current=()=>{const shown=secs.filter(s=>!s.hidden);let id=shown[0]&&shown[0].id;
  for(const s of shown){if(s.getBoundingClientRect().top-topOf()<=80)id=s.id;else break}
  return id};
let tick=false;
const onScroll=()=>{if(tick)return;tick=true;requestAnimationFrame(()=>{tick=false;
  if(chosen){const r=document.getElementById(chosen).getBoundingClientRect();if(Math.abs(r.top-topOf())>4&&main.scrollTop+main.clientHeight<main.scrollHeight-2)chosen=null}
  mark(chosen||current())})};
main.addEventListener('scroll',onScroll,{passive:true});addEventListener('scroll',onScroll,{passive:true});
links.forEach(a=>a.addEventListener('click',e=>{e.preventDefault();const id=a.hash.slice(1),t=document.getElementById(id);
  if(t.hidden){q.value='';ro.checked=false;apply()}
  main.scrollTop+=t.getBoundingClientRect().top-topOf();chosen=id;mark(id);history.replaceState(null,'','#'+id)}));
mark(location.hash?location.hash.slice(1):current());
'''

def slug(t): return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')

def main():
    args = sys.argv[1:]
    cfg_path = None
    if '--config' in args:
        i = args.index('--config')
        cfg_path = pathlib.Path(args[i + 1])
        del args[i:i + 2]
    src = pathlib.Path(args[0])
    out = pathlib.Path(args[1]) if len(args) > 1 else src.with_suffix('.html')
    sibling = src.with_suffix('.config.json')
    cfg_path = cfg_path or (sibling if sibling.exists() else None)
    cfg = json.loads(cfg_path.read_text()) if cfg_path else {}
    text = src.read_text()
    title = re.search(r'^# (.+)$', text, re.M).group(1)
    parts = re.split(r'^## (.+)$', text, flags=re.M)
    secs, used = [], set()
    for name, body in zip(parts[1::2], parts[2::2]):
        name = name.strip(); sid = slug(name); used.add(name)
        secs.append((name, sid, markdown.markdown(body, extensions=['tables', 'fenced_code', 'sane_lists'])))
    listed = [(g['name'], g['sections']) for g in cfg.get('groups', [])]
    known = {n for _, ns in listed for n in ns}
    rest = (cfg.get('rest', 'Sections'), [s[0] for s in secs if s[0] not in known])
    at = cfg.get('restAfter', len(listed))
    groups = listed[:at] + [rest] + listed[at:]
    # keep the guide's order inside the page; the nav groups by purpose
    nav = ''
    for g, names in groups:
        items = ''.join(f'<a href="#{slug(n)}">{html.escape(n)}</a>' for n in names if n in used)
        if items: nav += f'<h2>{html.escape(g)}</h2>{items}'
    body = ''.join(f'<section id="{i}"><h2>{html.escape(n)}</h2>{b}</section>' for n, i, b in secs)
    rev = re.findall(r'^\|\s*(\d+)\s*\|\s*(\d{4}-\d\d-\d\d)', text, re.M)
    ver = f'Rev {rev[-1][0]} · {rev[-1][1]}' if rev else ''
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head><body><div class="app">
<nav aria-label="Sections"><h1>{html.escape(title)}</h1><div class="ver">{ver}</div>
<input type="search" id="q" placeholder="Find a variable, service, path" aria-label="Find">
<label class="toggle"><input type="checkbox" id="ro"> Required variables only</label>{nav}</nav>
<main>{body}<div class="none" id="none" hidden>Nothing matches. Clear the search box.</div></main></div><script>{JS.replace('__CHECKLIST__', slug(cfg.get('checklist', 'Runbook')))}</script></body></html>'''
    out.write_text(page)
    print(out, len(page))

main()

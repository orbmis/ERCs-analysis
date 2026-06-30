#!/usr/bin/env python3
"""Pass A (frontmatter), A2 (body-structure flags), D (dependency graph).
No LLM. Reads ERCs/ERCS/erc-<int>.md (read-only), writes base_table.json + run_report fragments."""
import os, re, json, glob

SRC = "ERCs/ERCS"
OUT = "base_table.json"

def parse_frontmatter(text):
    """Return (dict, error_or_None). Simple line-based YAML for the --- block."""
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.S)
    if not m:
        return None, "no frontmatter block"
    block = m.group(1)
    data = {}
    cur = None
    for line in block.split('\n'):
        if not line.strip():
            continue
        km = re.match(r'^([A-Za-z][A-Za-z0-9_\-]*):\s?(.*)$', line)
        if km:
            cur = km.group(1).strip()
            data[cur] = km.group(2).strip()
        else:
            # continuation of previous value (e.g. multi-line author)
            if cur is not None:
                data[cur] = (data[cur] + " " + line.strip()).strip()
    return data, None

def split_authors(author):
    """Split multi-author string into discrete identities."""
    if not author:
        return []
    parts = re.split(r',\s*(?![^()<>]*[)>])', author)  # split on commas not inside () or <>
    # simpler: just split on commas; names with affiliations rarely contain commas inside
    parts = [p.strip() for p in author.split(',') if p.strip()]
    # rejoin fragments that are clearly continuations (no name char) - keep simple
    return parts

def parse_requires(req):
    if not req:
        return []
    nums = re.findall(r'\d+', req)
    return [int(n) for n in nums]

files = sorted(glob.glob(os.path.join(SRC, "erc-*.md")))
files = [f for f in files if re.match(r'^erc-\d+\.md$', os.path.basename(f))]

rows = {}
fm_failures = []

for f in files:
    base = os.path.basename(f)
    nm = re.match(r'^erc-(\d+)\.md$', base)
    erc_from_name = int(nm.group(1))
    with open(f, encoding='utf-8') as fh:
        text = fh.read()
    fm, err = parse_frontmatter(text)
    if err:
        fm_failures.append({"file": base, "error": err})
        fm = {}

    # frontmatter uses 'eip:' as the number key
    erc_num = fm.get('eip') or fm.get('erc')
    try:
        erc_num = int(re.search(r'\d+', str(erc_num)).group()) if erc_num else erc_from_name
    except Exception:
        erc_num = erc_from_name
    if erc_num != erc_from_name:
        fm_failures.append({"file": base, "error": f"eip {erc_num} != filename {erc_from_name}"})

    created = fm.get('created', '').strip()
    cm = re.search(r'\d{4}-\d{2}-\d{2}', created)
    created_iso = cm.group(0) if cm else created

    requires = parse_requires(fm.get('requires', ''))
    author = fm.get('author', '').strip()

    # missing required fields -> log but continue
    missing = [k for k in ('title','status','created') if not fm.get(k)]
    if missing or not fm:
        fm_failures.append({"file": base, "error": f"missing/empty: {missing or 'whole frontmatter'}"})

    # Pass A2 — body structure flags (body after frontmatter)
    body_m = re.match(r'^---\s*\n.*?\n---\s*\n(.*)$', text, re.S)
    body = body_m.group(1) if body_m else text
    low = body.lower()
    has_sec = bool(re.search(r'#+\s*security considerations', low))
    has_test = bool(re.search(r'#+\s*test cases?', low))
    has_ref = bool(re.search(r'#+\s*(reference implementation)', low))
    spec_word_count = len(re.findall(r'\S+', body))
    section_count = len(re.findall(r'^#{1,6}\s', body, re.M))

    rows[erc_num] = {
        "erc": erc_num,
        "title": fm.get('title','').strip(),
        "description": fm.get('description','').strip(),
        "status": fm.get('status','').strip(),
        "type": fm.get('type','').strip(),
        "category": fm.get('category','').strip(),
        "created": created_iso,
        "last_call_deadline": fm.get('last-call-deadline','').strip(),
        "withdrawal_reason": fm.get('withdrawal-reason','').strip(),
        "author": author,
        "authors_normalized": split_authors(author),
        "requires": requires,
        "discussions_to": fm.get('discussions-to','').strip(),
        "has_security_considerations": has_sec,
        "has_test_cases": has_test,
        "has_reference_impl": has_ref,
        "spec_word_count": spec_word_count,
        "section_count": section_count,
    }

# Pass D — dependency graph over `requires` (restricted to ERCs present in dataset)
present = set(rows.keys())
required_by = {e: [] for e in rows}
out_edges = {}
for e, r in rows.items():
    deps = [d for d in r['requires'] if d in present]
    out_edges[e] = deps
    for d in deps:
        required_by[d].append(e)

for e, r in rows.items():
    r['required_by'] = sorted(required_by[e])
    r['out_degree'] = len(out_edges[e])
    r['in_degree'] = len(required_by[e])

# dependency_depth = longest upstream requires chain (memoized DFS, cycle-safe)
depth_cache = {}
def depth(e, stack):
    if e in depth_cache:
        return depth_cache[e]
    if e in stack:
        return 0
    stack = stack | {e}
    best = 0
    for d in out_edges.get(e, []):
        best = max(best, 1 + depth(d, stack))
    depth_cache[e] = best
    return best
for e in rows:
    rows[e]['dependency_depth'] = depth(e, set())

# pagerank over the dependency DAG (edge e -> d, d is depended upon)
# power iteration; damping 0.85
N = len(rows)
pr = {e: 1.0/N for e in rows}
nodes = list(rows.keys())
for _ in range(100):
    new = {e: (1-0.85)/N for e in rows}
    dangling = 0.0
    for e in nodes:
        outs = out_edges[e]
        if not outs:
            dangling += pr[e]
        else:
            share = 0.85 * pr[e] / len(outs)
            for d in outs:
                new[d] += share
    # distribute dangling mass uniformly
    for e in nodes:
        new[e] += 0.85 * dangling / N
    diff = sum(abs(new[e]-pr[e]) for e in nodes)
    pr = new
    if diff < 1e-9:
        break
for e in rows:
    rows[e]['pagerank'] = round(pr[e], 8)

with open(OUT, 'w') as f:
    json.dump({"rows": rows, "fm_failures": fm_failures, "file_count": len(files)}, f, indent=0)

print(f"files_processed={len(files)}")
print(f"rows={len(rows)}")
print(f"frontmatter_failures={len(fm_failures)}")
for x in fm_failures:
    print("  FAIL", x)

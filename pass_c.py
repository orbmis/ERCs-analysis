#!/usr/bin/env python3
"""Pass C — git-derived temporal fields (deterministic, no LLM).
Read-only on the ERCs git repo. Writes erc_temporal.csv + pass_c.json.
For each erc-<N>.md: commit_count, distinct_committers, first/last commit dates,
status-transition dates parsed from diffs to the `status:` line, and time_to_final."""
import subprocess, glob, os, re, json, csv, datetime, collections

REPO = "ERCs"
SUBPATH = "ERCS"

files = sorted(glob.glob(os.path.join(REPO, SUBPATH, "erc-*.md")))
files = [f for f in files if re.match(r'^erc-\d+\.md$', os.path.basename(f))]

# frontmatter `created` per erc (from base table, for time_to_final start)
base = json.load(open("base_table.json"))
created_map = {int(k): v["created"] for k, v in base["rows"].items()}

def git(args):
    return subprocess.run(["git", "-C", REPO] + args, capture_output=True, text=True).stdout

def parse_date(s):
    # %aI -> ISO8601 with tz; take date part
    m = re.match(r'(\d{4}-\d{2}-\d{2})', s)
    return m.group(1) if m else ""

results = {}
for f in files:
    base_name = os.path.basename(f)
    erc = int(re.match(r'erc-(\d+)\.md', base_name).group(1))
    rel = os.path.join(SUBPATH, base_name)

    # commit metadata (author name + ISO date). NOTE: do NOT combine --follow with
    # --reverse (git truncates rename history); fetch newest-first and sort in python.
    meta = git(["log", "--follow", "--format=%aI|%an", "--", rel])
    commits = [ln for ln in meta.splitlines() if ln.strip()]
    dates = sorted(parse_date(c.split("|", 1)[0]) for c in commits)
    committers = set(c.split("|", 1)[1].strip() for c in commits if "|" in c)
    first_commit = dates[0] if dates else ""
    last_commit = dates[-1] if dates else ""
    commit_count = len(commits)

    # status transitions: collect every (+status value, commit date); take the EARLIEST
    # date each status first appears. Newest-first patch, min() per status in python.
    patch = git(["log", "--follow", "--format=@@@COMMIT|%aI", "-p",
                 "--unified=0", "--", rel])
    cur_date = ""
    status_dates = {}  # status_value -> earliest ISO date seen
    for ln in patch.splitlines():
        if ln.startswith("@@@COMMIT|"):
            cur_date = parse_date(ln.split("|", 1)[1])
            continue
        m = re.match(r'^\+status:\s*(.+?)\s*$', ln)
        if m:
            sv = m.group(1).strip()
            if sv and cur_date:
                if sv not in status_dates or cur_date < status_dates[sv]:
                    status_dates[sv] = cur_date

    date_final = status_dates.get("Final", "")
    created = created_map.get(erc, "")
    time_to_final = ""
    if date_final and re.match(r'\d{4}-\d{2}-\d{2}', created or ""):
        try:
            d0 = datetime.date.fromisoformat(created)
            d1 = datetime.date.fromisoformat(date_final)
            time_to_final = (d1 - d0).days
        except Exception:
            time_to_final = ""

    results[erc] = {
        "erc": erc,
        "first_commit_date": first_commit,
        "last_modified": last_commit,
        "commit_count": commit_count,
        "distinct_committers": len(committers),
        "date_draft": status_dates.get("Draft", ""),
        "date_review": status_dates.get("Review", ""),
        "date_last_call": status_dates.get("Last Call", ""),
        "date_final": date_final,
        "date_stagnant": status_dates.get("Stagnant", ""),
        "date_withdrawn": status_dates.get("Withdrawn", ""),
        "time_to_final": time_to_final,
        "status_transitions": status_dates,
    }

# write JSON (full, incl transitions) and flat CSV
json.dump(results, open("pass_c.json", "w"), indent=0)

COLS = ["erc","first_commit_date","last_modified","commit_count","distinct_committers",
        "date_draft","date_review","date_last_call","date_final","date_stagnant",
        "date_withdrawn","time_to_final"]
with open("erc_temporal.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=COLS)
    w.writeheader()
    for erc in sorted(results):
        w.writerow({k: results[erc][k] for k in COLS})

# summary
ttf = [r["time_to_final"] for r in results.values() if isinstance(r["time_to_final"], int)]
cc = [r["commit_count"] for r in results.values()]
print("files", len(files))
print("with_final_date", sum(1 for r in results.values() if r["date_final"]))
print("with_time_to_final", len(ttf))
if ttf:
    ttf_sorted = sorted(ttf)
    print("time_to_final days: min", min(ttf), "median", ttf_sorted[len(ttf)//2], "max", max(ttf))
print("commit_count: min", min(cc), "max", max(cc), "total", sum(cc))
print("no-commit files (sanity, should be 0):", sum(1 for r in results.values() if r["commit_count"]==0))

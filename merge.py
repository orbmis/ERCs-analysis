#!/usr/bin/env python3
"""Merge Pass A/A2/D base table with Pass B subagent JSON into erc_dataset.csv + _run_report.md."""
import json, glob, csv, re, os, collections

VOCAB = {"account-abstraction","agentic-workflows","reputation-identity","nft","rwa",
         "defi","tokens-fungible","governance","security-permissions","infrastructure-meta","other"}

base = json.load(open("base_table.json"))
rows = {int(k): v for k, v in base["rows"].items()}
fm_failures = base["fm_failures"]
file_count = base["file_count"]

# load Pass B
passb = {}
loaded_batches = 0
for bf in sorted(glob.glob("passb/batch_*.json"), key=lambda f:int(re.search(r'\d+',os.path.basename(f)).group())):
    try:
        data = json.load(open(bf))
        loaded_batches += 1
    except Exception as e:
        print("WARN could not parse", bf, e)
        continue
    for k, v in data.items():
        passb[int(k)] = v

pb_missing = []
bad_topic = []
flagged = []  # topic==other or confidence low or non-empty secondary

def norm_list(v):
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if v is None or v == "":
        return []
    return [s.strip() for s in re.split(r'[;,]', str(v)) if s.strip()]

COLUMNS = ["erc","title","description","topic","topic_secondary","topic_confidence","topic_other",
           "status","type","category","created","last_call_deadline","withdrawal_reason","author",
           "authors_normalized","requires","required_by","referenced_ercs","in_degree","out_degree",
           "pagerank","dependency_depth","has_security_considerations","has_test_cases",
           "has_reference_impl","spec_word_count","section_count","discussions_to","one_line_summary","notes"]

out_rows = []
topic_dist = collections.Counter()
for erc in sorted(rows.keys()):
    r = rows[erc]
    pb = passb.get(erc)
    if pb is None:
        pb_missing.append(erc)
        pb = {}
    topic = str(pb.get("topic","")).strip()
    if topic and topic not in VOCAB:
        bad_topic.append((erc, topic))
    topic_sec = str(pb.get("topic_secondary","")).strip()
    if topic_sec and topic_sec not in VOCAB:
        topic_sec = ""  # drop invalid secondary
    conf = str(pb.get("topic_confidence","")).strip()
    topic_other = str(pb.get("topic_other","")).strip()
    ref = norm_list(pb.get("referenced_ercs"))
    topic_dist[topic or "(missing)"] += 1
    if topic == "other" or conf == "low" or topic_sec:
        flagged.append({"erc":erc,"topic":topic,"topic_secondary":topic_sec,
                        "topic_confidence":conf,"topic_other":topic_other})

    out = {
        "erc": erc,
        "title": r["title"],
        "description": r["description"],
        "topic": topic,
        "topic_secondary": topic_sec,
        "topic_confidence": conf,
        "topic_other": topic_other,
        "status": r["status"],
        "type": r["type"],
        "category": r["category"],
        "created": r["created"],
        "last_call_deadline": r["last_call_deadline"],
        "withdrawal_reason": r["withdrawal_reason"],
        "author": r["author"],
        "authors_normalized": ";".join(r["authors_normalized"]),
        "requires": ";".join(str(x) for x in r["requires"]),
        "required_by": ";".join(str(x) for x in r["required_by"]),
        "referenced_ercs": ";".join(str(x) for x in ref),
        "in_degree": r["in_degree"],
        "out_degree": r["out_degree"],
        "pagerank": r["pagerank"],
        "dependency_depth": r["dependency_depth"],
        "has_security_considerations": r["has_security_considerations"],
        "has_test_cases": r["has_test_cases"],
        "has_reference_impl": r["has_reference_impl"],
        "spec_word_count": r["spec_word_count"],
        "section_count": r["section_count"],
        "discussions_to": r["discussions_to"],
        "one_line_summary": str(pb.get("one_line_summary","")).strip(),
        "notes": str(pb.get("notes","")).strip(),
    }
    out_rows.append(out)

with open("erc_dataset.csv","w",newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLUMNS)
    w.writeheader()
    for o in out_rows:
        w.writerow(o)

# required-column null exceptions
req_cols = ["erc","title","status","created"]
null_exceptions = []
date_bad = []
for o in out_rows:
    for c in req_cols:
        if o[c] is None or str(o[c]).strip() == "":
            null_exceptions.append((o["erc"], c))
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(o["created"])):
        date_bad.append((o["erc"], o["created"]))

# write run report
with open("_run_report.md","w") as f:
    f.write("# ERC dataset run report\n\n")
    f.write(f"- Files processed (matched `erc-<int>.md`): **{file_count}**\n")
    f.write(f"- CSV rows written: **{len(out_rows)}**\n")
    f.write(f"- Frontmatter failures: **{len(fm_failures)}**\n")
    f.write(f"- Pass B subagents: **40** (batch size 15; loaded {loaded_batches} batch files)\n")
    f.write(f"- ERCs missing a Pass B classification: **{len(pb_missing)}**" + (f" {pb_missing}" if pb_missing else "") + "\n")
    f.write(f"- Out-of-vocabulary topics: **{len(bad_topic)}**" + (f" {bad_topic}" if bad_topic else "") + "\n")
    f.write(f"- Required-column nulls (erc/title/status/created): **{len(null_exceptions)}**" + (f" {null_exceptions}" if null_exceptions else "") + "\n")
    f.write(f"- Non-ISO created values: **{len(date_bad)}**" + (f" {date_bad}" if date_bad else "") + "\n\n")

    f.write("## Frontmatter failures\n")
    if fm_failures:
        for x in fm_failures:
            f.write(f"- `{x['file']}`: {x['error']}\n")
    else:
        f.write("None.\n")
    f.write("\n")

    f.write("## Topic distribution\n\n")
    for t, c in topic_dist.most_common():
        f.write(f"- `{t}`: {c}\n")
    f.write("\n")

    f.write(f"## Rows flagged for review ({len(flagged)})\n")
    f.write("Criteria: `topic = other`, `topic_confidence = low`, or non-empty `topic_secondary`.\n\n")
    f.write("| erc | topic | secondary | confidence | topic_other |\n|---|---|---|---|---|\n")
    for x in sorted(flagged, key=lambda d:d["erc"]):
        f.write(f"| {x['erc']} | {x['topic']} | {x['topic_secondary']} | {x['topic_confidence']} | {x['topic_other']} |\n")
    f.write("\n")

print("=== MERGE COMPLETE ===")
print("csv_rows", len(out_rows))
print("pb_missing", len(pb_missing), pb_missing)
print("bad_topic", len(bad_topic), bad_topic)
print("null_exceptions", len(null_exceptions))
print("date_bad", len(date_bad))
print("flagged_for_review", len(flagged))
print("topic_dist", dict(topic_dist))

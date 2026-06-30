#!/usr/bin/env python3
"""Compute all analysis metrics + charts from erc_dataset.csv + erc_temporal.csv.
Deterministic. Writes analysis/metrics.json, analysis/tables/*.csv, analysis/figures/*.png."""
import csv, json, os, collections, statistics, datetime, itertools

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

os.makedirs("analysis/figures", exist_ok=True)
os.makedirs("analysis/tables", exist_ok=True)

SNAPSHOT = datetime.date(2026, 6, 30)
PALETTE = "#3b6ea5"
ACCENT = "#c0504d"

# ---------- load + join ----------
main = {int(r["erc"]): r for r in csv.DictReader(open("erc_dataset.csv"))}
temp = {int(r["erc"]): r for r in csv.DictReader(open("erc_temporal.csv"))}
ercs = sorted(main)
for e in ercs:
    main[e].update({f"t_{k}": v for k, v in temp.get(e, {}).items()})

def col(name): return [main[e].get(name, "") for e in ercs]
def int_or(v, d=0):
    try: return int(v)
    except: return d
def year(e): return main[e]["created"][:4]
def is_true(v): return str(v) == "True"

M = {}  # metrics bucket
def save_table(name, header, rows):
    with open(f"analysis/tables/{name}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)

def barh(path, labels, values, title, xlabel, color=PALETTE, figsize=(8,5), fmt="{:.0f}"):
    fig, ax = plt.subplots(figsize=figsize)
    y = range(len(labels))
    ax.barh(list(y), values, color=color)
    ax.set_yticks(list(y)); ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis(); ax.set_title(title, fontsize=12, weight="bold"); ax.set_xlabel(xlabel)
    for i, v in enumerate(values):
        ax.text(v, i, " "+fmt.format(v), va="center", fontsize=8)
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)

def bar(path, labels, values, title, ylabel, color=PALETTE, figsize=(9,4.5), rot=0):
    fig, ax = plt.subplots(figsize=figsize)
    ax.bar(range(len(labels)), values, color=color)
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=rot, ha="right" if rot else "center", fontsize=9)
    ax.set_title(title, fontsize=12, weight="bold"); ax.set_ylabel(ylabel)
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)

TOPICS = ["infrastructure-meta","nft","tokens-fungible","security-permissions","account-abstraction",
          "reputation-identity","defi","rwa","governance","other","agentic-workflows"]
STATUS_ORDER = ["Draft","Review","Last Call","Final","Stagnant","Withdrawn"]

# ---------- A. Overview ----------
M["total"] = len(ercs)
M["status_dist"] = dict(collections.Counter(col("status")))
M["topic_dist"] = dict(collections.Counter(col("topic")))
M["confidence_dist"] = dict(collections.Counter(col("topic_confidence")))
M["year_range"] = [min(col("created"))[:4], max(col("created"))[:4]]
M["flagged_for_review"] = sum(1 for e in ercs if main[e]["topic"]=="other" or main[e]["topic_confidence"]=="low" or main[e]["topic_secondary"])
M["constant_cols"] = {"type": list(set(col("type"))), "category": list(set(col("category")))}

# ---------- B. Temporal ----------
per_year = collections.Counter(year(e) for e in ercs)
years = sorted(per_year)
M["per_year"] = {y: per_year[y] for y in years}
bar("analysis/figures/erc_per_year.png", years, [per_year[y] for y in years],
    "New ERCs created per year", "count", rot=0)
save_table("per_year", ["year","count"], [[y, per_year[y]] for y in years])

# topic first-appearance year
first_seen = {}
for e in ercs:
    t = main[e]["topic"]
    if t and (t not in first_seen or year(e) < first_seen[t]):
        first_seen[t] = year(e)
M["topic_first_year"] = first_seen

# topic mix over time (share, stacked)
ty = collections.defaultdict(lambda: collections.Counter())
for e in ercs:
    ty[year(e)][main[e]["topic"]] += 1
fig, ax = plt.subplots(figsize=(10,5.5))
bottoms = [0]*len(years)
cmap = plt.get_cmap("tab20")
for i, t in enumerate(TOPICS):
    vals = [ty[y][t] for y in years]
    ax.bar(years, vals, bottom=bottoms, label=t, color=cmap(i))
    bottoms = [b+v for b,v in zip(bottoms, vals)]
ax.set_title("Topic composition of new ERCs per year", fontsize=12, weight="bold")
ax.set_ylabel("count"); ax.legend(fontsize=7, ncol=2, loc="upper left")
fig.tight_layout(); fig.savefig("analysis/figures/topic_mix_over_time.png", dpi=110); plt.close(fig)
save_table("topic_by_year", ["year"]+TOPICS, [[y]+[ty[y][t] for t in TOPICS] for y in years])

# ---------- C. Lifecycle ----------
status_ct = collections.Counter(col("status"))
M["funnel"] = {s: status_ct.get(s,0) for s in STATUS_ORDER}
barh("analysis/figures/status_funnel.png", STATUS_ORDER, [status_ct.get(s,0) for s in STATUS_ORDER],
     "ERC status distribution", "count", color=PALETTE)

# final rate / stagnation by cohort year
cohort = {}
for y in years:
    es = [e for e in ercs if year(e)==y]
    n=len(es)
    fin=sum(1 for e in es if main[e]["status"]=="Final")
    stag=sum(1 for e in es if main[e]["status"]=="Stagnant")
    cohort[y]={"n":n,"final":fin,"stagnant":stag,"final_rate":round(fin/n,3) if n else 0,"stagnant_rate":round(stag/n,3) if n else 0}
M["cohort"]=cohort
save_table("cohort_by_year", ["year","n","final","stagnant","final_rate","stagnant_rate"],
           [[y,cohort[y]["n"],cohort[y]["final"],cohort[y]["stagnant"],cohort[y]["final_rate"],cohort[y]["stagnant_rate"]] for y in years])
fig, ax = plt.subplots(figsize=(10,5))
ax.bar(years,[cohort[y]["final_rate"] for y in years], color=PALETTE, label="Final rate")
ax.plot(years,[cohort[y]["stagnant_rate"] for y in years], color=ACCENT, marker="o", label="Stagnant rate")
ax.set_title("Outcome by creation-year cohort", fontsize=12, weight="bold"); ax.set_ylabel("share of cohort"); ax.legend()
fig.tight_layout(); fig.savefig("analysis/figures/cohort_outcomes.png", dpi=110); plt.close(fig)

# time_to_final (Pass C)
ttf = [(e, int_or(main[e]["t_time_to_final"], None)) for e in ercs if main[e].get("t_time_to_final","") not in ("","None")]
ttf = [(e,v) for e,v in ttf if isinstance(v,int)]
ttf_pos = [v for e,v in ttf if v>=0]
M["time_to_final"] = {
    "n": len(ttf),
    "n_negative_anomalies": sum(1 for e,v in ttf if v<0),
    "negative_ercs": [e for e,v in ttf if v<0],
    "median_days": statistics.median(ttf_pos) if ttf_pos else None,
    "mean_days": round(statistics.mean(ttf_pos),1) if ttf_pos else None,
    "p25": sorted(ttf_pos)[len(ttf_pos)//4] if ttf_pos else None,
    "p75": sorted(ttf_pos)[3*len(ttf_pos)//4] if ttf_pos else None,
    "min": min(ttf_pos) if ttf_pos else None,
    "max": max(ttf_pos) if ttf_pos else None,
}
fig, ax = plt.subplots(figsize=(9,4.5))
ax.hist(ttf_pos, bins=24, color=PALETTE, edgecolor="white")
ax.axvline(statistics.median(ttf_pos), color=ACCENT, linestyle="--", label=f"median {int(statistics.median(ttf_pos))}d")
ax.set_title("Time from created to Final (days)", fontsize=12, weight="bold"); ax.set_xlabel("days"); ax.set_ylabel("ERCs"); ax.legend()
fig.tight_layout(); fig.savefig("analysis/figures/time_to_final_hist.png", dpi=110); plt.close(fig)

# ttf by topic (median)
ttf_topic = collections.defaultdict(list)
for e,v in ttf:
    if v>=0: ttf_topic[main[e]["topic"]].append(v)
ttf_topic_med = {t: int(statistics.median(vs)) for t,vs in ttf_topic.items() if len(vs)>=3}
ttf_topic_sorted = sorted(ttf_topic_med.items(), key=lambda kv: kv[1])
M["time_to_final_by_topic"] = {t:{"median_days":m,"n":len(ttf_topic[t])} for t,m in ttf_topic_med.items()}
if ttf_topic_sorted:
    barh("analysis/figures/time_to_final_by_topic.png", [t for t,_ in ttf_topic_sorted],
         [m for _,m in ttf_topic_sorted], "Median days to Final, by topic (n>=3)", "median days")

# withdrawals
M["withdrawals"] = [{"erc":e,"title":main[e]["title"],"reason":main[e]["withdrawal_reason"]} for e in ercs if main[e]["status"]=="Withdrawn"]

# stale drafts: Draft + last_modified older than 18 months before snapshot
def parse_d(s):
    try: return datetime.date.fromisoformat(s)
    except: return None
stale=[]
for e in ercs:
    if main[e]["status"]=="Draft":
        lm=parse_d(main[e]["t_last_modified"])
        if lm and (SNAPSHOT-lm).days>540:
            stale.append((e,(SNAPSHOT-lm).days))
M["stale_drafts_count"]=len(stale)
M["stale_drafts_top"]=sorted(stale,key=lambda x:-x[1])[:15]

# ---------- D. Topic landscape ----------
topic_ct=collections.Counter(col("topic"))
barh("analysis/figures/topic_distribution.png",[t for t,_ in topic_ct.most_common()],
     [c for _,c in topic_ct.most_common()],"ERCs per topic","count")
# straddle pairs
straddle=collections.Counter()
for e in ercs:
    s=main[e]["topic_secondary"]
    if s: straddle[(main[e]["topic"],s)]+=1
M["top_straddles"]=[{"primary":a,"secondary":b,"count":c} for (a,b),c in straddle.most_common(12)]
M["straddle_total"]=sum(straddle.values())
# confidence by topic
conf_topic={}
for t in TOPICS:
    es=[e for e in ercs if main[e]["topic"]==t]
    if es:
        conf_topic[t]={c:sum(1 for e in es if main[e]["topic_confidence"]==c) for c in ["high","medium","low"]}
M["confidence_by_topic"]=conf_topic

# ---------- E. Dependency / influence ----------
def pr(e): return float(main[e]["pagerank"])
top_pr=sorted(ercs,key=pr,reverse=True)[:15]
M["top_pagerank"]=[{"erc":e,"title":main[e]["title"],"pagerank":round(pr(e),4),"in_degree":int_or(main[e]["in_degree"]),"topic":main[e]["topic"]} for e in top_pr]
barh("analysis/figures/pagerank_top.png",[f'{e} {main[e]["title"][:24]}' for e in top_pr[:12]],
     [pr(e) for e in top_pr[:12]],"Most foundational ERCs (PageRank over requires-graph)","PageRank",fmt="{:.3f}")
top_indeg=sorted(ercs,key=lambda e:int_or(main[e]["in_degree"]),reverse=True)[:15]
M["top_required_by"]=[{"erc":e,"title":main[e]["title"],"in_degree":int_or(main[e]["in_degree"])} for e in top_indeg]
# depth dist
depth_ct=collections.Counter(int_or(main[e]["dependency_depth"]) for e in ercs)
bar("analysis/figures/dependency_depth.png",[str(d) for d in sorted(depth_ct)],
    [depth_ct[d] for d in sorted(depth_ct)],"Dependency depth (longest upstream requires chain)","ERCs")
M["depth_dist"]={str(d):depth_ct[d] for d in sorted(depth_ct)}
M["isolated_count"]=sum(1 for e in ercs if int_or(main[e]["in_degree"])==0 and int_or(main[e]["out_degree"])==0)
# formal vs informal: referenced_ercs (body mentions) frequency
ref_ct=collections.Counter()
for e in ercs:
    for r in (main[e]["referenced_ercs"] or "").split(";"):
        r=r.strip()
        if r.isdigit(): ref_ct[int(r)]+=1
M["top_referenced"]=[{"erc":n,"title":main.get(n,{}).get("title","(external EIP)"),"mentions":c} for n,c in ref_ct.most_common(15)]
req_ct=collections.Counter()
for e in ercs:
    for r in (main[e]["requires"] or "").split(";"):
        if r.strip().isdigit(): req_ct[int(r.strip())]+=1
_fi_nums = sorted({n for n,_ in (req_ct+ref_ct).most_common(15)},
                  key=lambda n: -(req_ct.get(n,0)+ref_ct.get(n,0)))
M["formal_vs_informal"]=[{"erc":n,"requires_edges":req_ct.get(n,0),"body_mentions":ref_ct.get(n,0),
                          "title":main.get(n,{}).get("title","(external EIP)")} for n in _fi_nums]
# influence by topic
infl_topic={}
for t in TOPICS:
    es=[e for e in ercs if main[e]["topic"]==t]
    if es:
        infl_topic[t]={"mean_in_degree":round(statistics.mean(int_or(main[e]["in_degree"]) for e in es),2),
                       "sum_in_degree":sum(int_or(main[e]["in_degree"]) for e in es),"n":len(es)}
M["influence_by_topic"]=infl_topic

# ---------- F. Authorship ----------
author_ct=collections.Counter()
for e in ercs:
    for a in (main[e]["authors_normalized"] or "").split(";"):
        a=a.strip()
        if a: author_ct[a]+=1
M["top_authors"]=[{"author":a,"erc_count":c} for a,c in author_ct.most_common(15)]
barh("analysis/figures/top_authors.png",[a.split(" (")[0] for a,_ in author_ct.most_common(12)],
     [c for _,c in author_ct.most_common(12)],"Most prolific ERC authors","ERCs authored")
team_sizes=[len([a for a in (main[e]["authors_normalized"] or "").split(";") if a.strip()]) for e in ercs]
M["team_size"]={"mean":round(statistics.mean(team_sizes),2),"median":statistics.median(team_sizes),"max":max(team_sizes),
                "solo":sum(1 for s in team_sizes if s==1),"dist":dict(collections.Counter(team_sizes))}
bar("analysis/figures/team_size_hist.png",[str(s) for s in sorted(set(team_sizes)) if s<=12],
    [team_sizes.count(s) for s in sorted(set(team_sizes)) if s<=12],"Author team size","ERCs")
# solo vs team final rate
solo=[e for e,s in zip(ercs,team_sizes) if s==1]; team=[e for e,s in zip(ercs,team_sizes) if s>1]
def fr(es): return round(sum(1 for e in es if main[e]["status"]=="Final")/len(es),3) if es else 0
M["final_rate_solo_vs_team"]={"solo":{"n":len(solo),"final_rate":fr(solo)},"team":{"n":len(team),"final_rate":fr(team)}}
# committers
committers=[int_or(main[e]["t_distinct_committers"]) for e in ercs if main[e].get("t_distinct_committers","")]
M["distinct_committers"]={"mean":round(statistics.mean(committers),2),"max":max(committers)} if committers else {}
# co-authorship connectors
co_deg=collections.defaultdict(set)
for e in ercs:
    auths=[a.strip() for a in (main[e]["authors_normalized"] or "").split(";") if a.strip()]
    for a,b in itertools.combinations(auths,2):
        co_deg[a].add(b); co_deg[b].add(a)
M["top_connectors"]=[{"author":a,"distinct_coauthors":len(s)} for a,s in sorted(co_deg.items(),key=lambda kv:-len(kv[1]))[:12]]

# ---------- G. Maturity / rigor ----------
def rate(es,c): return round(sum(1 for e in es if is_true(main[e][c]))/len(es),3) if es else 0
flags=["has_security_considerations","has_test_cases","has_reference_impl"]
M["maturity_overall"]={c:rate(ercs,c) for c in flags}
final_es=[e for e in ercs if main[e]["status"]=="Final"]
nonfinal=[e for e in ercs if main[e]["status"]!="Final"]
M["maturity_by_status"]={"Final":{c:rate(final_es,c) for c in flags},"non-Final":{c:rate(nonfinal,c) for c in flags}}
M["final_missing_security"]=[{"erc":e,"title":main[e]["title"]} for e in final_es if not is_true(main[e]["has_security_considerations"])]
M["final_missing_tests"]=sum(1 for e in final_es if not is_true(main[e]["has_test_cases"]))
fig, ax = plt.subplots(figsize=(8,4.5))
x=range(len(flags)); w=0.38
ax.bar([i-w/2 for i in x],[rate(final_es,c) for c in flags],width=w,label="Final",color=PALETTE)
ax.bar([i+w/2 for i in x],[rate(nonfinal,c) for c in flags],width=w,label="non-Final",color=ACCENT)
ax.set_xticks(list(x)); ax.set_xticklabels(["security\nconsiderations","test\ncases","reference\nimpl"],fontsize=9)
ax.set_title("Rigor signals: Final vs non-Final",fontsize=12,weight="bold"); ax.set_ylabel("share present"); ax.legend()
fig.tight_layout(); fig.savefig("analysis/figures/maturity_by_status.png",dpi=110); plt.close(fig)
# test cases by topic
M["tests_by_topic"]={t:rate([e for e in ercs if main[e]["topic"]==t],"has_test_cases") for t in TOPICS if [e for e in ercs if main[e]["topic"]==t]}

# ---------- H. Complexity ----------
wc=[int_or(main[e]["spec_word_count"]) for e in ercs]
sc=[int_or(main[e]["section_count"]) for e in ercs]
M["complexity"]={"word_median":statistics.median(wc),"word_mean":round(statistics.mean(wc)),"word_max":max(wc),
                 "section_median":statistics.median(sc)}
fig, ax = plt.subplots(figsize=(9,4.5))
ax.hist([w for w in wc if w<8000],bins=30,color=PALETTE,edgecolor="white")
ax.axvline(statistics.median(wc),color=ACCENT,linestyle="--",label=f"median {int(statistics.median(wc))}")
ax.set_title("Spec word count distribution (<8000 shown)",fontsize=12,weight="bold");ax.set_xlabel("words");ax.set_ylabel("ERCs");ax.legend()
fig.tight_layout(); fig.savefig("analysis/figures/wordcount_hist.png",dpi=110); plt.close(fig)
wc_topic={t:int(statistics.median([int_or(main[e]["spec_word_count"]) for e in ercs if main[e]["topic"]==t]))
          for t in TOPICS if [e for e in ercs if main[e]["topic"]==t]}
wc_topic_s=sorted(wc_topic.items(),key=lambda kv:-kv[1])
barh("analysis/figures/wordcount_by_topic.png",[t for t,_ in wc_topic_s],[v for _,v in wc_topic_s],
     "Median spec word count by topic","median words")
M["wordcount_by_topic"]=wc_topic
top_long=sorted(ercs,key=lambda e:int_or(main[e]["spec_word_count"]),reverse=True)[:10]
M["longest_specs"]=[{"erc":e,"title":main[e]["title"],"words":int_or(main[e]["spec_word_count"]),"topic":main[e]["topic"]} for e in top_long]

# ---------- I. Synthesis: hot vs maturing quadrant ----------
quad={}
for t in TOPICS:
    es=[e for e in ercs if main[e]["topic"]==t]
    if len(es)<5: continue
    recent=sum(1 for e in es if year(e)>="2024")
    quad[t]={"recent_count":recent,"total":len(es),"final_rate":fr(es),"recent_share":round(recent/len(es),3)}
M["quadrant"]=quad
fig, ax = plt.subplots(figsize=(9,6))
for t,d in quad.items():
    ax.scatter(d["recent_count"],d["final_rate"],s=d["total"]*4,color=PALETTE,alpha=0.6,edgecolor="black")
    ax.annotate(t,(d["recent_count"],d["final_rate"]),fontsize=8,xytext=(4,4),textcoords="offset points")
ax.set_xlabel("recent activity (ERCs created 2024+)"); ax.set_ylabel("Final rate (all-time)")
ax.set_title("Hot vs maturing: topic activity vs consolidation",fontsize=12,weight="bold")
ax.axhline(fr(ercs),color=ACCENT,linestyle=":",alpha=0.7)
fig.tight_layout(); fig.savefig("analysis/figures/hot_vs_maturing.png",dpi=110); plt.close(fig)

# velocity over time: median ttf by final cohort year
final_year_ttf=collections.defaultdict(list)
for e,v in ttf:
    if v>=0 and main[e]["t_date_final"]:
        final_year_ttf[main[e]["t_date_final"][:4]].append(v)
M["velocity_by_final_year"]={y:int(statistics.median(vs)) for y,vs in sorted(final_year_ttf.items()) if len(vs)>=3}
vy=sorted(M["velocity_by_final_year"].items())
if vy:
    bar("analysis/figures/velocity_by_year.png",[y for y,_ in vy],[v for _,v in vy],
        "Median days-to-Final by year reached Final (n>=3)","median days")

json.dump(M, open("analysis/metrics.json","w"), indent=1, default=str)
print("metrics computed. figures:", len(os.listdir("analysis/figures")), "tables:", len(os.listdir("analysis/tables")))
print("key:", "ttf_median", M["time_to_final"]["median_days"], "| flagged", M["flagged_for_review"],
      "| stale_drafts", M["stale_drafts_count"], "| final_missing_sec", len(M["final_missing_security"]))

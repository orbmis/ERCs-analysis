#!/usr/bin/env python3
"""#10 On-chain adoption. Joins Dune-sourced adoption metrics (analysis/adoption_raw.json) onto
the ERC dataset for the marquee standards with measurable footprints, and cross-references
adoption against influence / status / discussion. Outputs erc_adoption.csv, figures, metrics."""
import csv, json, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

main={int(r["erc"]):r for r in csv.DictReader(open("erc_dataset.csv"))}
disc={int(r["erc"]):r for r in csv.DictReader(open("erc_discussions.csv"))} if os.path.exists("erc_discussions.csv") else {}
raw=json.load(open("analysis/adoption_raw.json"))

# primary adoption metric per marquee standard (Ethereum mainnet)
ADOPT={
 20:  {"standard":"ERC-20","metric":"token contracts deployed","value":1582182},
 721: {"standard":"ERC-721","metric":"NFT collections deployed","value":276994},
 1155:{"standard":"ERC-1155","metric":"multi-token collections deployed","value":130262},
 4337:{"standard":"ERC-4337","metric":"user operations","value":4650036,
       "extra":{"smart_accounts":986466,"bundlers":837}},
}
def views(e):
    try: return int(disc.get(e,{}).get("views") or 0)
    except: return 0

# write joined CSV
with open("erc_adoption.csv","w",newline="") as f:
    w=csv.writer(f)
    w.writerow(["erc","standard","title","status","in_degree","forum_views","primary_metric","primary_value","extra"])
    for e in sorted(ADOPT):
        a=ADOPT[e]; m=main.get(e,{})
        w.writerow([e,a["standard"],m.get("title",""),m.get("status",""),m.get("in_degree",""),
                    views(e),a["metric"],a["value"],json.dumps(a.get("extra",{}))])

# ---- figure 1: adoption magnitude (log) ----
labels=[ADOPT[e]["standard"]+"\n"+ADOPT[e]["metric"] for e in [20,4337,721,1155]]
vals=[ADOPT[20]["value"],ADOPT[4337]["value"],ADOPT[721]["value"],ADOPT[1155]["value"]]
fig,ax=plt.subplots(figsize=(9,5))
bars=ax.bar(range(len(vals)),vals,color=["#3b6ea5","#c0504d","#3b6ea5","#3b6ea5"])
ax.set_yscale("log"); ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels,fontsize=9)
ax.set_ylabel("count (log scale)"); ax.set_title("On-chain adoption of marquee ERC standards (Ethereum mainnet)",fontsize=12,weight="bold")
for b,v in zip(bars,vals): ax.text(b.get_x()+b.get_width()/2,v,f"{v:,}",ha="center",va="bottom",fontsize=8)
fig.tight_layout(); fig.savefig("analysis/figures/adoption_marquee.png",dpi=120); plt.close(fig)

# ---- figure 2: ERC-4337 adoption growth ----
yr=raw["queries"]["erc4337_by_year"]["rows"]
years=[r["yr"] for r in yr]
fig,ax=plt.subplots(figsize=(9,5))
ax.bar(years,[r["userops"] for r in yr],color="#3b6ea5",label="user operations")
ax2=ax.twinx()
ax2.plot(years,[r["active_accounts"] for r in yr],color="#c0504d",marker="o",lw=2,label="active smart accounts")
ax.set_ylabel("user operations"); ax2.set_ylabel("active smart accounts")
ax.set_title("ERC-4337 account-abstraction adoption by year (Ethereum mainnet)\n2026 is partial (to Jun 30)",fontsize=12,weight="bold")
ax.legend(loc="upper left"); ax2.legend(loc="lower right")
fig.tight_layout(); fig.savefig("analysis/figures/adoption_erc4337_growth.png",dpi=120); plt.close(fig)

# ---- metrics + cross-reference ----
M={"as_of":raw["as_of"],"chain":"ethereum","coverage_note":
   "Direct on-chain adoption is measurable only for standards that emit standardized events/contracts. "
   "4 marquee standards have mass footprints; the other 596 ERCs have no directly-measurable mainnet adoption.",
   "marquee":[]}
for e in sorted(ADOPT):
    a=ADOPT[e]; m=main.get(e,{})
    M["marquee"].append({"erc":e,"standard":a["standard"],"status":m.get("status"),
        "in_degree":int(m.get("in_degree",0) or 0),"forum_views":views(e),
        "primary_metric":a["metric"],"primary_value":a["value"],"extra":a.get("extra",{})})
M["erc4337_growth"]=yr
M["adopted_are_foundational"]={
  "all_four_status":[main[e]["status"] for e in ADOPT],
  "all_four_in_degree":{e:int(main[e]["in_degree"]) for e in ADOPT},
  "note":"All four adopted standards are Final and rank in the top of the dependency graph."}
json.dump(M,open("analysis/adoption_metrics.json","w"),indent=1)
print("wrote erc_adoption.csv + 2 figures + adoption_metrics.json")
for e in sorted(ADOPT):
    m=main[e]; print(f"  ERC-{e}: {ADOPT[e]['value']:>10,} {ADOPT[e]['metric']:<30} status={m['status']:<8} in_deg={m['in_degree']:>3} views={views(e)}")

#!/usr/bin/env python3
"""Analyze discussion engagement (erc_discussions.csv) vs status / topic / finalization /
influence / time-to-Final. Focuses cross-analysis on the magicians set (views/posts/participants).
Outputs analysis/figures/*, analysis/discussion_metrics.json, analysis/DISCUSSION_ANALYSIS.md inputs."""
import csv, json, statistics, collections, math
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr, pointbiserialr

main={int(r["erc"]):r for r in csv.DictReader(open("erc_dataset.csv"))}
temp={int(r["erc"]):r for r in csv.DictReader(open("erc_temporal.csv"))}
disc={int(r["erc"]):r for r in csv.DictReader(open("erc_discussions.csv"))}
ercs=sorted(main)
def I(v,d=None):
    try: return int(v)
    except: return d
def is_final(e): return main[e]["status"]=="Final"

TOPICS=["infrastructure-meta","nft","tokens-fungible","security-permissions","account-abstraction",
        "reputation-identity","defi","rwa","governance","other","agentic-workflows"]
STATUS=["Draft","Review","Last Call","Final","Stagnant","Withdrawn"]
M={}

# coverage
src=collections.Counter(disc[e]["source"] for e in ercs if e in disc)
mag_ok=[e for e in ercs if disc.get(e,{}).get("source")=="magicians" and disc[e].get("ok")=="True"]
mag_fail=[e for e in ercs if disc.get(e,{}).get("source")=="magicians" and disc[e].get("ok")!="True"]
gh_ok=[e for e in ercs if disc.get(e,{}).get("source")=="github" and disc[e].get("ok")=="True"]
M["coverage"]={"sources":dict(src),"magicians_ok":len(mag_ok),"magicians_fail":len(mag_fail),
               "github_ok":len(gh_ok)}

def val(e,k): return I(disc.get(e,{}).get(k))
# magicians analysis frame: e -> views/posts/participants
D=[e for e in mag_ok if val(e,"views") is not None]
views={e:val(e,"views") for e in D}
posts={e:val(e,"posts") or 0 for e in D}
parts={e:val(e,"participants") or 0 for e in D}

def med(xs): return statistics.median(xs) if xs else None
M["distributions"]={
 "n":len(D),
 "views":{"median":med(list(views.values())),"mean":round(statistics.mean(views.values())) if D else None,"max":max(views.values()) if D else None},
 "posts":{"median":med(list(posts.values())),"max":max(posts.values()) if D else None},
 "participants":{"median":med(list(parts.values())),"max":max(parts.values()) if D else None},
}

# by status
M["by_status"]={}
for s in STATUS:
    es=[e for e in D if main[e]["status"]==s]
    if es: M["by_status"][s]={"n":len(es),"median_views":med([views[e] for e in es]),
                              "median_posts":med([posts[e] for e in es]),"median_participants":med([parts[e] for e in es])}
fig,ax=plt.subplots(figsize=(9,4.8))
ss=[s for s in STATUS if s in M["by_status"]]
ax.bar(ss,[M["by_status"][s]["median_views"] for s in ss],color="#3b6ea5")
ax.set_ylabel("median thread views"); ax.set_title("Discussion engagement by ERC status (median forum views)",fontsize=12,weight="bold")
fig.tight_layout(); fig.savefig("analysis/figures/discussion_by_status.png",dpi=110); plt.close(fig)

# by topic
M["by_topic"]={}
for t in TOPICS:
    es=[e for e in D if main[e]["topic"]==t]
    if es: M["by_topic"][t]={"n":len(es),"median_views":med([views[e] for e in es]),"median_posts":med([posts[e] for e in es])}
tt=sorted(M["by_topic"].items(),key=lambda kv:-(kv[1]["median_views"] or 0))
fig,ax=plt.subplots(figsize=(9,5))
ax.barh([t for t,_ in tt],[v["median_views"] for _,v in tt],color="#3b6ea5"); ax.invert_yaxis()
ax.set_xlabel("median thread views"); ax.set_title("Discussion engagement by topic (median forum views)",fontsize=12,weight="bold")
fig.tight_layout(); fig.savefig("analysis/figures/discussion_by_topic.png",dpi=110); plt.close(fig)

# Final vs non-Final
fin=[e for e in D if is_final(e)]; nonfin=[e for e in D if not is_final(e)]
M["final_vs_nonfinal"]={"Final":{"n":len(fin),"median_views":med([views[e] for e in fin]),"median_posts":med([posts[e] for e in fin]),"median_participants":med([parts[e] for e in fin])},
                        "non_Final":{"n":len(nonfin),"median_views":med([views[e] for e in nonfin]),"median_posts":med([posts[e] for e in nonfin]),"median_participants":med([parts[e] for e in nonfin])}}
# point-biserial: log views vs is_final
lv=np.array([math.log1p(views[e]) for e in D]); yf=np.array([1 if is_final(e) else 0 for e in D])
pb=pointbiserialr(yf,lv)
M["corr_logviews_final"]={"r":round(float(pb.correlation),3),"p":round(float(pb.pvalue),4)}
fig,ax=plt.subplots(figsize=(8,4.8)); x=range(3); w=0.35
grp=["median_views","median_posts","median_participants"]
ax.bar([i-w/2 for i in x],[M["final_vs_nonfinal"]["Final"][g] for g in grp],width=w,label="Final",color="#3b6ea5")
ax.bar([i+w/2 for i in x],[M["final_vs_nonfinal"]["non_Final"][g] for g in grp],width=w,label="non-Final",color="#c0504d")
ax.set_xticks(list(x)); ax.set_xticklabels(["views","posts","participants"]); ax.set_yscale("log")
ax.set_title("Discussion engagement: Final vs non-Final (log scale)",fontsize=12,weight="bold"); ax.legend()
fig.tight_layout(); fig.savefig("analysis/figures/discussion_final_vs_nonfinal.png",dpi=110); plt.close(fig)

# vs time-to-final
ttf=[(e,I(temp.get(e,{}).get("time_to_final"))) for e in D]
ttf=[(e,v) for e,v in ttf if isinstance(v,int) and v>=0]
if len(ttf)>=10:
    sp=spearmanr([posts[e] for e,_ in ttf],[v for _,v in ttf])
    M["corr_posts_ttf"]={"rho":round(float(sp.correlation),3),"p":round(float(sp.pvalue),4),"n":len(ttf)}
    fig,ax=plt.subplots(figsize=(8,5))
    ax.scatter([posts[e] for e,_ in ttf],[v for _,v in ttf],alpha=0.5,color="#3b6ea5",edgecolor="black",linewidth=0.3)
    ax.set_xlabel("forum posts (discussion volume)"); ax.set_ylabel("days to Final")
    ax.set_title(f"Discussion volume vs time-to-Final (Spearman ρ={sp.correlation:.2f})",fontsize=12,weight="bold")
    fig.tight_layout(); fig.savefig("analysis/figures/discussion_vs_ttf.png",dpi=110); plt.close(fig)

# vs influence (in_degree)
indeg={e:I(main[e]["in_degree"],0) for e in D}
sp2=spearmanr([views[e] for e in D],[indeg[e] for e in D])
M["corr_views_indegree"]={"rho":round(float(sp2.correlation),3),"p":round(float(sp2.pvalue),6)}

# top discussed + most contentious (posts per participant)
top_views=sorted(D,key=lambda e:views[e],reverse=True)[:15]
M["most_viewed"]=[{"erc":e,"title":main[e]["title"],"views":views[e],"posts":posts[e],"status":main[e]["status"],"topic":main[e]["topic"]} for e in top_views]
top_posts=sorted(D,key=lambda e:posts[e],reverse=True)[:15]
M["most_discussed"]=[{"erc":e,"title":main[e]["title"],"posts":posts[e],"participants":parts[e],"status":main[e]["status"]} for e in top_posts]
# silent proposals
silent=[e for e in D if views[e]<300 or posts[e]<=1]
M["silent"]={"n":len(silent),"final_rate":round(sum(1 for e in silent if is_final(e))/len(silent),3) if silent else None,
             "stagnant_rate":round(sum(1 for e in silent if main[e]["status"]=="Stagnant")/len(silent),3) if silent else None}

json.dump(M,open("analysis/discussion_metrics.json","w"),indent=1,default=str)
print("coverage:",M["coverage"])
print("median views",M["distributions"]["views"]["median"],"| Final vs nonFinal views",
      M["final_vs_nonfinal"]["Final"]["median_views"],"vs",M["final_vs_nonfinal"]["non_Final"]["median_views"])
print("corr logviews~final r=",M["corr_logviews_final"],"| views~indegree",M["corr_views_indegree"])
print("corr posts~ttf",M.get("corr_posts_ttf"))
print("figures done")

#!/usr/bin/env python3
"""Time-series analysis of ERC topics (semantic categories) over time.
Quarter/half-year trajectories, per-topic temporal clustering (creation-date percentiles),
and data-driven 'era' detection by clustering periods on their topic mix.
Input: erc_dataset.csv (created, topic). Outputs: analysis/figures/*, tables/*, timeseries_metrics.json."""
import csv, json, collections, datetime, statistics
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

rows=list(csv.DictReader(open("erc_dataset.csv")))
TOPICS=["tokens-fungible","infrastructure-meta","reputation-identity","security-permissions","nft",
        "defi","rwa","account-abstraction","governance","agentic-workflows","other"]
TCOLOR={t:plt.get_cmap("tab20")(i) for i,t in enumerate(TOPICS)}

def d(r): return datetime.date.fromisoformat(r["created"])
def ord_frac(dt): return dt.year + (dt.timetuple().tm_yday-1)/365.25  # decimal year
def q(dt): return f"{dt.year}Q{(dt.month-1)//3+1}"
def h(dt): return f"{dt.year}H{1 if dt.month<=6 else 2}"

for r in rows: r["_d"]=d(r); r["_q"]=q(r["_d"]); r["_h"]=h(r["_d"]); r["_yf"]=ord_frac(r["_d"])

# ---------- per-topic temporal clustering (how tightly each topic clusters in time) ----------
stats=[]
for t in TOPICS:
    ds=sorted(r["_yf"] for r in rows if r["topic"]==t)
    if not ds: continue
    n=len(ds)
    p25=ds[int(0.25*(n-1))]; med=ds[int(0.5*(n-1))]; p75=ds[int(0.75*(n-1))]
    yrs=collections.Counter(int(r["_d"].year) for r in rows if r["topic"]==t)
    peak_year,peak_n=yrs.most_common(1)[0]
    recent=sum(1 for r in rows if r["topic"]==t and r["_d"].year>=2024)
    stats.append({"topic":t,"n":n,"first":round(min(ds),2),"p25":round(p25,2),"median":round(med,2),
                  "p75":round(p75,2),"iqr_years":round(p75-p25,2),"peak_year":peak_year,
                  "peak_count":peak_n,"recent_share":round(recent/n,3)})
stats.sort(key=lambda s:s["median"])
with open("analysis/tables/topic_temporal_stats.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["topic","n","first","p25","median","p75","iqr_years","peak_year","peak_count","recent_share"])
    for s in stats: w.writerow([s[k] for k in ["topic","n","first","p25","median","p75","iqr_years","peak_year","peak_count","recent_share"]])

# wave chart: IQR spans of creation dates per topic (sorted by median)
fig,ax=plt.subplots(figsize=(11,6))
for i,s in enumerate(stats):
    ax.plot([s["p25"],s["p75"]],[i,i],lw=8,color=TCOLOR[s["topic"]],alpha=0.55,solid_capstyle="round")
    ax.plot(s["median"],i,"o",color="black",ms=6)
    ax.plot(s["first"],i,"|",color=TCOLOR[s["topic"]],ms=14,mew=2)
    ax.text(s["p75"]+0.1,i,f'{s["topic"]} (n={s["n"]})',va="center",fontsize=9)
ax.set_yticks([]); ax.set_xlabel("year")
ax.set_title("When each topic clustered: creation-date middle-50% span (bar), median (●), first (│)",fontsize=12,weight="bold")
ax.set_xlim(2014.5,2027.5); ax.grid(axis="x",alpha=0.3)
fig.tight_layout(); fig.savefig("analysis/figures/topic_era_spans.png",dpi=120); plt.close(fig)

# ---------- half-year topic matrix ----------
halves=sorted({r["_h"] for r in rows}, key=lambda s:(int(s[:4]), s[-1]))
quarters=sorted({r["_q"] for r in rows}, key=lambda s:(int(s[:4]), s[-1]))
def matrix(periods, pkey):
    counts=np.zeros((len(TOPICS),len(periods)))
    pidx={p:i for i,p in enumerate(periods)}
    for r in rows: counts[TOPICS.index(r["topic"])][pidx[r[pkey]]]+=1
    return counts
Hc=matrix(halves,"_h")
# topic order by median date for heatmap rows
row_order=[TOPICS.index(s["topic"]) for s in stats]
Hc_ord=Hc[row_order]; labels_ord=[TOPICS[i] for i in row_order]
# normalized share within each half-year
col_tot=Hc_ord.sum(axis=0); col_tot[col_tot==0]=1
Hshare=Hc_ord/col_tot
fig,ax=plt.subplots(figsize=(15,6))
im=ax.imshow(Hshare,aspect="auto",cmap="YlOrRd")
ax.set_yticks(range(len(labels_ord))); ax.set_yticklabels(labels_ord,fontsize=9)
ax.set_xticks(range(len(halves))); ax.set_xticklabels(halves,rotation=90,fontsize=7)
ax.set_title("Topic share of new ERCs per half-year (rows ordered by median date)",fontsize=12,weight="bold")
fig.colorbar(im,ax=ax,shrink=0.7,label="share of half-year")
fig.tight_layout(); fig.savefig("analysis/figures/topic_halfyear_heatmap.png",dpi=110); plt.close(fig)
with open("analysis/tables/topic_by_quarter.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["quarter"]+TOPICS)
    Qc=matrix(quarters,"_q")
    for j,p in enumerate(quarters): w.writerow([p]+[int(Qc[i][j]) for i in range(len(TOPICS))])

# normalized stacked area by half-year
fig,ax=plt.subplots(figsize=(13,6))
x=range(len(halves)); bottoms=np.zeros(len(halves))
share_full=Hc/ (Hc.sum(axis=0)+1e-9)
for i,t in enumerate(TOPICS):
    ax.fill_between(x,bottoms,bottoms+share_full[i],label=t,color=TCOLOR[t],alpha=0.85,step="mid")
    bottoms=bottoms+share_full[i]
ax.set_xticks(list(x)); ax.set_xticklabels(halves,rotation=90,fontsize=7); ax.set_ylim(0,1)
ax.set_title("Topic composition of new ERCs over time (normalized, half-year)",fontsize=12,weight="bold")
ax.legend(fontsize=7,ncol=2,loc="upper left"); ax.set_ylabel("share")
fig.tight_layout(); fig.savefig("analysis/figures/topic_share_area.png",dpi=110); plt.close(fig)

# ---------- data-driven ERA detection: CONTIGUOUS optimal segmentation (respects time order) ----------
# Segment the ordered half-year share-vectors into K consecutive eras via dynamic programming,
# minimizing within-segment weighted variance (weight = #ERCs in the half-year).
T=len(halves)
w=Hc.sum(axis=0)                                   # ERCs per half-year (weights)
S=(Hc/(w+1e-9)).T                                  # T x 11 share vectors
# precompute weighted segment cost cost[i][j] for span [i..j]
cost=np.full((T,T),0.0)
for i in range(T):
    for j in range(i,T):
        ws=w[i:j+1]; xs=S[i:j+1]
        if ws.sum()==0: cost[i][j]=0; continue
        mean=(xs*ws[:,None]).sum(0)/ws.sum()
        cost[i][j]=float((ws[:,None]*(xs-mean)**2).sum())
def segment(K):
    DP=np.full((K+1,T+1),np.inf); DP[0][0]=0; BT=[[None]*(T+1) for _ in range(K+1)]
    for k_ in range(1,K+1):
        for j in range(1,T+1):
            for i in range(k_-1,j):
                c=DP[k_-1][i]+cost[i][j-1]
                if c<DP[k_][j]: DP[k_][j]=c; BT[k_][j]=i
    bounds=[]; j=T
    for k_ in range(K,0,-1):
        i=BT[k_][j]; bounds.append((i,j-1)); j=i
    return DP[K][T], list(reversed(bounds))
costs={K:segment(K)[0] for K in range(1,7)}
# elbow: pick K where marginal gain falls below 20% of the first gain
gains={K:costs[K-1]-costs[K] for K in range(2,7)}
g1=gains[2]; k=2
for K in range(3,7):
    if gains[K] < 0.20*g1: k=K-1; break
    k=K
_,bounds=segment(k)
period_era={}; eras=[]
for era,(i,j) in enumerate(bounds):
    for p in range(i,j+1): period_era[halves[p]]=era
    sub=Hc[:,i:j+1].sum(axis=1); n=int(sub.sum())
    top=sorted(((TOPICS[m],int(sub[m])) for m in range(len(TOPICS))),key=lambda kv:-kv[1])[:3]
    share_top=[f"{t} ({c}, {round(100*c/max(n,1))}%)" for t,c in top]
    eras.append({"era":era+1,"span":f"{halves[i]}–{halves[j]}","n_ercs":n,"dominant":share_top})
sil=0.0  # not applicable to DP segmentation
# timeline plot colored by era
fig,ax=plt.subplots(figsize=(14,5))
era_cmap=plt.get_cmap("Set2")
heights=Hc.sum(axis=0)
colors=[]
for j,p in enumerate(halves):
    e=period_era.get(p, None)
    colors.append(era_cmap(e) if e is not None else "#cccccc")
ax.bar(range(len(halves)),heights,color=colors)
ax.set_xticks(range(len(halves))); ax.set_xticklabels(halves,rotation=90,fontsize=7)
ax.set_ylabel("new ERCs"); ax.set_title(f"Data-driven eras (optimal contiguous segmentation of topic mix, K={k})",fontsize=12,weight="bold")
handles=[plt.Rectangle((0,0),1,1,color=era_cmap(i)) for i in range(k)]
ax.legend(handles,[f"Era {e['era']}: {e['span']}" for e in eras],fontsize=8,loc="upper left")
fig.tight_layout(); fig.savefig("analysis/figures/eras_timeline.png",dpi=110); plt.close(fig)

# peak quarter per topic
peakq={}
Qc=matrix(quarters,"_q")
for i,t in enumerate(TOPICS):
    j=int(np.argmax(Qc[i])); peakq[t]={"quarter":quarters[j],"count":int(Qc[i][j])}

M={"n":len(rows),"topic_temporal_stats":stats,"eras":{"k":k,"silhouette":round(float(sil),3),"detail":eras},
   "peak_quarter":peakq,"period_era":period_era}
json.dump(M,open("analysis/timeseries_metrics.json","w"),indent=1,default=str)
print("eras k=",k,"silhouette=",round(sil,3))
for e in eras: print(f"  Era {e['era']} {e['span']}: n={e['n_ercs']}  dominant={e['dominant']}")
print("\ntightest-clustered topics (smallest IQR):")
for s in sorted(stats,key=lambda s:s['iqr_years'])[:5]:
    print(f"  {s['topic']:<20} IQR={s['iqr_years']}y  median={s['median']}  peak={s['peak_year']}")

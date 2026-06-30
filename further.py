#!/usr/bin/env python3
"""Further analyses: dependency-graph viz, co-authorship network, author scorecard,
topic-convergence, finalization predictor, survival analysis, churn & retention.
Inputs: erc_dataset.csv + erc_temporal.csv. Outputs: analysis/figures/*, analysis/tables/*,
analysis/further_metrics.json."""
import csv, json, os, collections, statistics, datetime, itertools
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import make_pipeline

np.random.seed(42)
os.makedirs("analysis/figures", exist_ok=True)
os.makedirs("analysis/tables", exist_ok=True)
SNAPSHOT = datetime.date(2026, 6, 30)

main = {int(r["erc"]): r for r in csv.DictReader(open("erc_dataset.csv"))}
temp = {int(r["erc"]): r for r in csv.DictReader(open("erc_temporal.csv"))}
ercs = sorted(main)
for e in ercs:
    main[e].update({f"t_{k}": v for k, v in temp.get(e, {}).items()})

def I(v, d=0):
    try: return int(v)
    except: return d
def is_t(v): return str(v) == "True"
def yr(e): return main[e]["created"][:4]
def pdate(s):
    try: return datetime.date.fromisoformat(s)
    except: return None

TOPICS = ["infrastructure-meta","nft","tokens-fungible","security-permissions","account-abstraction",
          "reputation-identity","defi","rwa","governance","other","agentic-workflows"]
TCOLOR = {t: plt.get_cmap("tab20")(i) for i, t in enumerate(TOPICS)}
M = {}
def tbl(name, header, rows):
    with open(f"analysis/tables/{name}.csv","w",newline="") as f:
        w=csv.writer(f); w.writerow(header); w.writerows(rows)

# =================================================================== 1. DEP GRAPH VIZ
present=set(ercs)
G=nx.DiGraph(); G.add_nodes_from(ercs)
for e in ercs:
    for r in (main[e]["requires"] or "").split(";"):
        if r.strip().isdigit() and int(r) in present:
            G.add_edge(e, int(r))  # e requires r
conn=[n for n in G.nodes if G.in_degree(n)+G.out_degree(n)>0]
H=G.subgraph(conn)
pos=nx.spring_layout(H, k=0.5, iterations=60, seed=42)
fig,ax=plt.subplots(figsize=(15,15))
indeg={n:G.in_degree(n) for n in conn}
sizes=[30+indeg[n]*14 for n in conn]
colors=[TCOLOR.get(main[n]["topic"],"#999") for n in conn]
nx.draw_networkx_edges(H,pos,ax=ax,alpha=0.12,width=0.5,arrows=False)
nx.draw_networkx_nodes(H,pos,ax=ax,nodelist=conn,node_size=sizes,node_color=colors,alpha=0.85,linewidths=0.3,edgecolors="white")
labels={n:f"ERC-{n}" for n in conn if indeg[n]>=8}
nx.draw_networkx_labels(H,pos,labels=labels,ax=ax,font_size=11,font_weight="bold")
handles=[plt.Line2D([0],[0],marker='o',color='w',markerfacecolor=TCOLOR[t],markersize=9,label=t) for t in TOPICS]
ax.legend(handles=handles,loc="lower left",fontsize=9,title="topic")
ax.set_title("ERC dependency graph (formal `requires` edges; node size = how many ERCs require it)",fontsize=15,weight="bold")
ax.axis("off"); fig.tight_layout(); fig.savefig("analysis/figures/dependency_graph.png",dpi=95); plt.close(fig)
M["dep_graph"]={"nodes_total":len(ercs),"nodes_connected":len(conn),"edges":G.number_of_edges(),
                "isolated":len(ercs)-len(conn),
                "weakly_connected_components":nx.number_weakly_connected_components(H),
                "largest_component":len(max(nx.weakly_connected_components(H),key=len))}

# =================================================================== 2. CO-AUTHORSHIP NETWORK
authors_of={e:[a.strip() for a in (main[e]["authors_normalized"] or "").split(";") if a.strip()] for e in ercs}
acount=collections.Counter(a for e in ercs for a in authors_of[e])
CA=nx.Graph()
for e in ercs:
    for a in authors_of[e]: CA.add_node(a)
    for a,b in itertools.combinations(sorted(set(authors_of[e])),2):
        if CA.has_edge(a,b): CA[a][b]["weight"]+=1
        else: CA.add_edge(a,b,weight=1)
core=[a for a in CA.nodes if acount[a]>=2]          # recurring authors only, for legibility
CC=CA.subgraph(core).copy()
CC.remove_nodes_from(list(nx.isolates(CC)))
comms=list(nx.algorithms.community.greedy_modularity_communities(CC, weight="weight"))
mod=nx.algorithms.community.modularity(CC, comms, weight="weight")
node2c={};
for i,c in enumerate(comms):
    for n in c: node2c[n]=i
pos2=nx.spring_layout(CC, k=0.45, iterations=70, seed=7, weight="weight")
fig,ax=plt.subplots(figsize=(15,15))
cmap=plt.get_cmap("tab20")
nx.draw_networkx_edges(CC,pos2,ax=ax,alpha=0.10,width=0.5)
deg=dict(CC.degree())
nx.draw_networkx_nodes(CC,pos2,ax=ax,node_size=[40+acount[n]*30 for n in CC.nodes],
                       node_color=[cmap(node2c[n]%20) for n in CC.nodes],alpha=0.85,linewidths=0.3,edgecolors="white")
lab={n:n.split(" (")[0] for n in CC.nodes if acount[n]>=5}
nx.draw_networkx_labels(CC,pos2,labels=lab,ax=ax,font_size=9)
ax.set_title(f"ERC co-authorship network (authors with ≥2 ERCs)\n{len(comms)} communities, modularity={mod:.2f}",fontsize=15,weight="bold")
ax.axis("off"); fig.tight_layout(); fig.savefig("analysis/figures/coauthor_network.png",dpi=95); plt.close(fig)
big=sorted(comms,key=len,reverse=True)[:6]
M["coauthor"]={"authors_total":len(acount),"recurring_authors":len(core),"network_nodes":CC.number_of_nodes(),
               "communities":len(comms),"modularity":round(mod,3),
               "top_communities":[{"size":len(c),"members":[m for m in sorted(c,key=lambda a:-acount[a])[:6]]} for c in big]}

# =================================================================== 3. AUTHOR SUCCESS SCORECARD
def auth_stats(a):
    es=[e for e in ercs if a in authors_of[e]]
    fin=[e for e in es if main[e]["status"]=="Final"]
    stag=[e for e in es if main[e]["status"]=="Stagnant"]
    ttf=[I(main[e]["t_time_to_final"],None) for e in fin if main[e].get("t_time_to_final","") not in ("","None")]
    ttf=[x for x in ttf if isinstance(x,int) and x>=0]
    tops=collections.Counter(main[e]["topic"] for e in es)
    return {"author":a,"n":len(es),"final":len(fin),"final_rate":round(len(fin)/len(es),3),
            "stagnant_rate":round(len(stag)/len(es),3),
            "median_ttf":int(statistics.median(ttf)) if ttf else "",
            "top_topic":tops.most_common(1)[0][0] if tops else ""}
score=[auth_stats(a) for a,c in acount.items() if c>=3]
score.sort(key=lambda d:(-d["n"],-d["final_rate"]))
tbl("author_scorecard",["author","n","final","final_rate","stagnant_rate","median_ttf","top_topic"],
    [[s["author"],s["n"],s["final"],s["final_rate"],s["stagnant_rate"],s["median_ttf"],s["top_topic"]] for s in score])
M["scorecard_n_authors"]=len(score)
M["scorecard_top"]=score[:20]
# scatter volume vs final rate
fig,ax=plt.subplots(figsize=(11,7))
xs=[s["n"] for s in score]; ys=[s["final_rate"] for s in score]
ax.scatter(xs,ys,s=60,alpha=0.5,color="#3b6ea5",edgecolor="black",linewidth=0.3)
for s in score:
    if s["n"]>=7 or (s["n"]>=4 and s["final_rate"]>=0.6):
        ax.annotate(s["author"].split(" (")[0],(s["n"],s["final_rate"]),fontsize=7.5,xytext=(3,3),textcoords="offset points")
ax.axhline(0.23,color="#c0504d",linestyle=":",label="corpus Final rate 23%")
ax.set_xlabel("ERCs authored (≥3)"); ax.set_ylabel("Final rate"); ax.legend()
ax.set_title("Author success: output volume vs finalization rate",fontsize=13,weight="bold")
fig.tight_layout(); fig.savefig("analysis/figures/author_scorecard.png",dpi=110); plt.close(fig)

# =================================================================== 4. TOPIC CONVERGENCE
mat=np.zeros((len(TOPICS),len(TOPICS)))
ti={t:i for i,t in enumerate(TOPICS)}
straddle_pairs=collections.Counter()
for e in ercs:
    p=main[e]["topic"]; s=main[e]["topic_secondary"]
    if p in ti and s in ti and s:
        mat[ti[p]][ti[s]]+=1; mat[ti[s]][ti[p]]+=1
        straddle_pairs[tuple(sorted((p,s)))]+=1
fig,ax=plt.subplots(figsize=(9,8))
im=ax.imshow(mat,cmap="YlOrRd")
ax.set_xticks(range(len(TOPICS))); ax.set_xticklabels(TOPICS,rotation=45,ha="right",fontsize=8)
ax.set_yticks(range(len(TOPICS))); ax.set_yticklabels(TOPICS,fontsize=8)
for i in range(len(TOPICS)):
    for j in range(len(TOPICS)):
        if mat[i][j]>0: ax.text(j,i,int(mat[i][j]),ha="center",va="center",fontsize=8,color="black")
ax.set_title("Topic convergence: ERCs straddling two domains\n(primary↔secondary co-occurrence)",fontsize=12,weight="bold")
fig.colorbar(im,ax=ax,shrink=0.7,label="# ERCs"); fig.tight_layout()
fig.savefig("analysis/figures/topic_convergence.png",dpi=110); plt.close(fig)
# straddle trend over time
years=sorted({yr(e) for e in ercs})
strad_yr={}
for y in years:
    es=[e for e in ercs if yr(e)==y]
    strad_yr[y]=round(sum(1 for e in es if main[e]["topic_secondary"])/len(es),3) if es else 0
fig,ax=plt.subplots(figsize=(10,4.5))
ax.plot(years,[strad_yr[y] for y in years],marker="o",color="#3b6ea5")
ax.set_title("Share of new ERCs that straddle two topics, by year",fontsize=12,weight="bold")
ax.set_ylabel("straddle share"); fig.tight_layout()
fig.savefig("analysis/figures/straddle_trend.png",dpi=110); plt.close(fig)
M["convergence"]={"top_bridges":[{"pair":list(p),"count":c} for p,c in straddle_pairs.most_common(10)],
                  "straddle_share_by_year":strad_yr}

# =================================================================== 5. FINALIZATION PREDICTOR
num_feats=["team_size","requires_count","required_by","has_tests","has_security","has_refimpl",
           "log_words","section_count","age_years"]
rows_X=[]; y=[]; topic_oh_cols=[t for t in TOPICS]
for e in ercs:
    created=pdate(main[e]["created"])
    age=(SNAPSHOT-created).days/365.25 if created else 0
    feat=[len(authors_of[e]), I(main[e]["out_degree"]), I(main[e]["in_degree"]),
          1 if is_t(main[e]["has_test_cases"]) else 0,
          1 if is_t(main[e]["has_security_considerations"]) else 0,
          1 if is_t(main[e]["has_reference_impl"]) else 0,
          np.log1p(I(main[e]["spec_word_count"])), I(main[e]["section_count"]), age]
    oh=[1 if main[e]["topic"]==t else 0 for t in topic_oh_cols]
    rows_X.append(feat+oh); y.append(1 if main[e]["status"]=="Final" else 0)
X=np.array(rows_X,float); y=np.array(y)
allcols=num_feats+[f"topic={t}" for t in topic_oh_cols]
scaler=StandardScaler().fit(X); Xs=scaler.transform(X)
lr=LogisticRegression(max_iter=2000,C=1.0).fit(Xs,y)
auc=cross_val_score(make_pipeline(StandardScaler(),LogisticRegression(max_iter=2000)),X,y,cv=5,scoring="roc_auc")
coefs=sorted(zip(allcols,lr.coef_[0]),key=lambda kv:-abs(kv[1]))
M["predictor"]={"n":len(y),"final":int(y.sum()),"cv_auc_mean":round(float(auc.mean()),3),"cv_auc_std":round(float(auc.std()),3),
                "standardized_coefficients":[{"feature":c,"coef":round(float(w),3),"odds_ratio":round(float(np.exp(w)),3)} for c,w in coefs]}
# decision tree (interpretable)
dt=DecisionTreeClassifier(max_depth=3,min_samples_leaf=20,random_state=0).fit(X,y)
M["predictor"]["tree_rules"]=export_text(dt,feature_names=allcols,max_depth=3).split("\n")
# plot top coefficients
top=coefs[:12][::-1]
fig,ax=plt.subplots(figsize=(9,6))
cols=["#3b6ea5" if w>0 else "#c0504d" for _,w in top]
ax.barh([c for c,_ in top],[w for _,w in top],color=cols)
ax.axvline(0,color="black",lw=0.6)
ax.set_title(f"What predicts reaching Final (standardized logistic coef; CV AUC={auc.mean():.2f})",fontsize=12,weight="bold")
ax.set_xlabel("← less likely Final     |     more likely Final →")
fig.tight_layout(); fig.savefig("analysis/figures/finalization_predictors.png",dpi=110); plt.close(fig)

# =================================================================== 6. SURVIVAL ANALYSIS (Kaplan-Meier)
def km(durations,events):
    data=sorted(zip(durations,events))
    n=len(data); times=[]; surv=[]; S=1.0; at_risk=n; i=0
    uniq=sorted(set(d for d,_ in data))
    for t in uniq:
        d=sum(1 for dd,ev in data if dd==t and ev==1)
        c=sum(1 for dd,ev in data if dd==t)
        if at_risk>0 and d>0:
            S*=(1-d/at_risk)
        times.append(t/365.25); surv.append(S)
        at_risk-=c
    return times,surv
def build_surv(es):
    dur=[];ev=[]
    for e in es:
        created=pdate(main[e]["created"])
        if not created: continue
        if main[e]["t_date_final"]:
            t=I(main[e]["t_time_to_final"],None)
            if isinstance(t,int) and t>=0: dur.append(t); ev.append(1)
        else:
            lm=pdate(main[e]["t_last_modified"]) or SNAPSHOT
            d=(lm-created).days
            if d>0: dur.append(d); ev.append(0)
    return dur,ev
def median_surv(times,surv):
    for t,s in zip(times,surv):
        if s<=0.5: return round(t,2)
    return None
dur,ev=build_surv(ercs)
t_all,s_all=km(dur,ev)
fig,ax=plt.subplots(figsize=(10,5.5))
ax.step(t_all,s_all,where="post",color="#3b6ea5",lw=2)
ax.axhline(0.5,color="grey",ls=":")
ax.set_xlabel("years since created"); ax.set_ylabel("P(not yet Final)")
ax.set_title("Kaplan–Meier: survival until Final (censored = not-yet-Final)",fontsize=12,weight="bold")
ax.set_ylim(0,1); fig.tight_layout(); fig.savefig("analysis/figures/km_overall.png",dpi=110); plt.close(fig)
# fraction finalized by horizon
def frac_final_by(times,surv,yrs):
    last=1.0
    for t,s in zip(times,surv):
        if t<=yrs: last=s
    return round(1-last,3)
M["survival"]={"n":len(dur),"events_final":sum(ev),"censored":len(ev)-sum(ev),
               "median_years_to_final":median_surv(t_all,s_all),
               "finalized_by_1y":frac_final_by(t_all,s_all,1),"finalized_by_2y":frac_final_by(t_all,s_all,2),
               "finalized_by_3y":frac_final_by(t_all,s_all,3)}
# by topic
fig,ax=plt.subplots(figsize=(10,6))
bytopic={}
for t in ["nft","infrastructure-meta","tokens-fungible","account-abstraction","security-permissions","defi"]:
    es=[e for e in ercs if main[e]["topic"]==t]
    d,e2=build_surv(es)
    if sum(e2)>=4:
        tt,ss=km(d,e2); ax.step(tt,ss,where="post",lw=1.8,label=f"{t} (n={len(d)})")
        bytopic[t]={"median_years":median_surv(tt,ss),"finalized_by_2y":frac_final_by(tt,ss,2)}
ax.axhline(0.5,color="grey",ls=":"); ax.set_ylim(0,1)
ax.set_xlabel("years since created"); ax.set_ylabel("P(not yet Final)"); ax.legend(fontsize=8)
ax.set_title("Kaplan–Meier survival to Final, by topic",fontsize=12,weight="bold")
fig.tight_layout(); fig.savefig("analysis/figures/km_by_topic.png",dpi=110); plt.close(fig)
M["survival"]["by_topic"]=bytopic

# =================================================================== 7. CHURN & RETENTION
cc={e:I(main[e]["t_commit_count"]) for e in ercs}
dcm={e:I(main[e]["t_distinct_committers"]) for e in ercs}
by_status_churn={}
for s in ["Final","Stagnant","Draft","Review","Last Call","Withdrawn"]:
    es=[e for e in ercs if main[e]["status"]==s]
    if es: by_status_churn[s]={"median_commits":statistics.median([cc[e] for e in es]),
                               "median_committers":statistics.median([dcm[e] for e in es]),"n":len(es)}
M["churn_by_status"]=by_status_churn
top_churn=sorted(ercs,key=lambda e:cc[e],reverse=True)[:12]
M["most_revised"]=[{"erc":e,"title":main[e]["title"],"commits":cc[e],"committers":dcm[e],"status":main[e]["status"]} for e in top_churn]
fig,ax=plt.subplots(figsize=(9,4.8))
ss=["Final","Last Call","Review","Draft","Stagnant","Withdrawn"]
ax.bar(ss,[by_status_churn.get(s,{}).get("median_commits",0) for s in ss],color="#3b6ea5")
ax.set_ylabel("median commit count"); ax.set_title("Churn by status: median commits per ERC",fontsize=12,weight="bold")
fig.tight_layout(); fig.savefig("analysis/figures/churn_by_status.png",dpi=110); plt.close(fig)
# retention
author_years={a:sorted(int(yr(e)) for e in ercs if a in authors_of[e]) for a in acount}
tenure={a:(ys[-1]-ys[0]) for a,ys in author_years.items()}
one_and_done=sum(1 for a,c in acount.items() if c==1)
recurring=sum(1 for a,c in acount.items() if c>=2)
# debut-cohort retention: of authors whose first ERC is year Y, share who authored again in a LATER year
debut=collections.defaultdict(list)
for a,ys in author_years.items(): debut[ys[0]].append(a)
cohort_ret={}
for y,al in sorted(debut.items()):
    if len(al)>=5:
        ret=sum(1 for a in al if author_years[a][-1]>y)/len(al)
        cohort_ret[str(y)]=round(ret,3)
M["retention"]={"total_authors":len(acount),"one_and_done":one_and_done,"one_and_done_share":round(one_and_done/len(acount),3),
                "recurring":recurring,"median_tenure_years_recurring":statistics.median([tenure[a] for a in acount if acount[a]>=2]),
                "most_tenured":[{"author":a,"years_active":tenure[a],"first":author_years[a][0],"last":author_years[a][-1],"ercs":acount[a]}
                                for a in sorted(acount,key=lambda a:(-tenure[a],-acount[a]))[:10]],
                "debut_cohort_retention":cohort_ret}
fig,ax=plt.subplots(figsize=(10,4.5))
ks=sorted(cohort_ret); ax.bar(ks,[cohort_ret[k] for k in ks],color="#3b6ea5")
ax.set_ylabel("share authoring again later"); ax.set_title("Author retention by debut-year cohort",fontsize=12,weight="bold")
fig.tight_layout(); fig.savefig("analysis/figures/author_retention.png",dpi=110); plt.close(fig)
# distribution of ercs-per-author
fig,ax=plt.subplots(figsize=(8,4.5))
cnts=collections.Counter(acount.values())
ks=sorted(k for k in cnts if k<=10); ax.bar([str(k) for k in ks],[cnts[k] for k in ks],color="#3b6ea5")
ax.set_xlabel("ERCs authored"); ax.set_ylabel("# authors"); ax.set_title("How many ERCs each author writes (≤10)",fontsize=12,weight="bold")
fig.tight_layout(); fig.savefig("analysis/figures/ercs_per_author.png",dpi=110); plt.close(fig)

json.dump(M,open("analysis/further_metrics.json","w"),indent=1,default=str)
print("OK")
print("dep:",M["dep_graph"]["nodes_connected"],"connected /",M["dep_graph"]["largest_component"],"in largest comp")
print("coauthor communities:",M["coauthor"]["communities"],"modularity",M["coauthor"]["modularity"])
print("predictor CV AUC:",M["predictor"]["cv_auc_mean"],"top:",[c["feature"] for c in M["predictor"]["standardized_coefficients"][:5]])
print("survival median yrs:",M["survival"]["median_years_to_final"],"by2y",M["survival"]["finalized_by_2y"])
print("retention one&done share:",M["retention"]["one_and_done_share"])
print("figures:",len([f for f in os.listdir('analysis/figures')]))

#!/usr/bin/env python3
"""#12 External-EIP graph completion. Adds the 36 referenced Core/other EIPs (outside the
600-ERC corpus) as real nodes, recomputes the dependency graph + influence, redraws it,
and reports how the influence ranking changes. Inputs: erc_dataset.csv + ext_eips/*.md."""
import csv, json, os, re, glob, collections
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
np.random.seed(42)

TOPICS=["infrastructure-meta","nft","tokens-fungible","security-permissions","account-abstraction",
        "reputation-identity","defi","rwa","governance","other","agentic-workflows"]
TCOLOR={t:plt.get_cmap("tab20")(i) for i,t in enumerate(TOPICS)}

rows={int(r["erc"]):r for r in csv.DictReader(open("erc_dataset.csv"))}
present=set(rows)

def parse_fm(text):
    m=re.match(r'^---\s*\n(.*?)\n---\s*\n',text,re.S)
    if not m: return {}
    d={};cur=None
    for ln in m.group(1).split("\n"):
        km=re.match(r'^([A-Za-z][\w\-]*):\s?(.*)$',ln)
        if km: cur=km.group(1); d[cur]=km.group(2).strip()
        elif cur: d[cur]=(d[cur]+" "+ln.strip()).strip()
    return d

# external EIP metadata (resolved) + their own requires edges
ext_meta={}
ext_requires={}
for f in glob.glob("ext_eips/eip-*.md"):
    n=int(re.search(r'eip-(\d+)\.md',f).group(1))
    fm=parse_fm(open(f,encoding="utf-8").read())
    ext_meta[n]={"title":fm.get("title","").strip(),"status":fm.get("status","").strip(),
                 "type":fm.get("type","").strip(),"category":fm.get("category","").strip()}
    ext_requires[n]=[int(x) for x in re.findall(r'\d+',fm.get("requires","")) ]

# full external set referenced from ERCs
ext_referenced=set()
for e,r in rows.items():
    for c in ("requires","referenced_ercs"):
        for x in (r[c] or "").split(";"):
            if x.strip().isdigit() and int(x) not in present:
                ext_referenced.add(int(x))
unresolved=sorted(ext_referenced-set(ext_meta))

# ---- build FORMAL requires graph: edge e->d means "e requires d" ----
G=nx.DiGraph()
for e in rows: G.add_node(e, kind="erc", topic=rows[e]["topic"])
for n,m in ext_meta.items(): G.add_node(n, kind="eip", topic=None)
for n in unresolved: G.add_node(n, kind="eip_unresolved", topic=None)
allnodes=set(G.nodes)

edges=0
for e,r in rows.items():
    for x in (r["requires"] or "").split(";"):
        if x.strip().isdigit() and int(x) in allnodes:
            G.add_edge(e,int(x)); edges+=1
# external EIPs' own formal requires, if target is in our node set
for n,reqs in ext_requires.items():
    for d in reqs:
        if d in allnodes: G.add_edge(n,d)

indeg={n:G.in_degree(n) for n in G}
pr=nx.pagerank(G, alpha=0.85)

def label(n):
    if n in present: return rows[n]["title"]
    if n in ext_meta: return ext_meta[n]["title"] or "(EIP)"
    return "(unresolved)"
def kind(n):
    return "ERC" if n in present else ("EIP" if n in ext_meta else "EIP?")

# combined influence ranking
rank=sorted(allnodes,key=lambda n:indeg[n],reverse=True)
combined=[{"id":n,"kind":kind(n),"title":label(n),"in_degree":indeg[n],"pagerank":round(pr[n],4),
           "status":ext_meta.get(n,{}).get("status","") or rows.get(n,{}).get("status","")} for n in rank[:25]]

# how external EIPs rank among everything
ext_rank=[{"eip":n,"title":ext_meta.get(n,{}).get("title","(unresolved)"),"in_degree":indeg[n],
           "pagerank":round(pr[n],4),"overall_rank":rank.index(n)+1,"status":ext_meta.get(n,{}).get("status","")}
          for n in sorted(ext_referenced,key=lambda n:indeg[n],reverse=True)]

with open("analysis/tables/combined_influence.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["id","kind","title","in_degree","pagerank","status"])
    for c in combined: w.writerow([c["id"],c["kind"],c["title"],c["in_degree"],c["pagerank"],c["status"]])

M={"erc_nodes":len(present),"external_eip_nodes":len(ext_referenced),
   "external_resolved":len(ext_meta),"external_unresolved":len(unresolved),"unresolved_list":unresolved,
   "total_edges":G.number_of_edges(),"combined_top25":combined,"external_eip_ranking":ext_rank}
json.dump(M,open("analysis/external_eip_metrics.json","w"),indent=1)

# ---- redraw: connected subgraph, external EIPs distinguished ----
conn=[n for n in G.nodes if G.in_degree(n)+G.out_degree(n)>0]
H=G.subgraph(conn)
pos=nx.spring_layout(H,k=0.5,iterations=60,seed=42)
fig,ax=plt.subplots(figsize=(16,16))
nx.draw_networkx_edges(H,pos,ax=ax,alpha=0.12,width=0.5,arrows=False)
erc_n=[n for n in conn if n in present]
eip_n=[n for n in conn if n in ext_meta]
unr_n=[n for n in conn if n not in present and n not in ext_meta]
nx.draw_networkx_nodes(H,pos,nodelist=erc_n,ax=ax,node_size=[30+indeg[n]*14 for n in erc_n],
                       node_color=[TCOLOR.get(rows[n]["topic"],"#999") for n in erc_n],alpha=0.85,linewidths=0.3,edgecolors="white")
nx.draw_networkx_nodes(H,pos,nodelist=eip_n,ax=ax,node_shape="s",node_size=[60+indeg[n]*14 for n in eip_n],
                       node_color="#111111",alpha=0.9,linewidths=0.6,edgecolors="yellow")
if unr_n:
    nx.draw_networkx_nodes(H,pos,nodelist=unr_n,ax=ax,node_shape="^",node_size=70,node_color="#888",alpha=0.7)
lab={n:(f"EIP-{n}" if n in ext_meta else f"ERC-{n}") for n in conn if indeg[n]>=8}
nx.draw_networkx_labels(H,pos,labels=lab,ax=ax,font_size=10,font_weight="bold")
handles=[plt.Line2D([0],[0],marker='o',color='w',markerfacecolor=TCOLOR[t],markersize=9,label=t) for t in TOPICS]
handles.append(plt.Line2D([0],[0],marker='s',color='w',markerfacecolor="#111",markeredgecolor="yellow",markersize=10,label="external EIP"))
handles.append(plt.Line2D([0],[0],marker='^',color='w',markerfacecolor="#888",markersize=10,label="unresolved EIP"))
ax.legend(handles=handles,loc="lower left",fontsize=9,title="node type")
ax.set_title("ERC + external-EIP dependency graph (squares = Core/other EIPs referenced by ERCs)",fontsize=15,weight="bold")
ax.axis("off"); fig.tight_layout(); fig.savefig("analysis/figures/dependency_graph_full.png",dpi=95); plt.close(fig)

print("erc_nodes",len(present),"ext_referenced",len(ext_referenced),"resolved",len(ext_meta),"unresolved",len(unresolved))
print("edges",G.number_of_edges())
print("\nTop external EIPs by in-degree (overall rank in parens):")
for r in ext_rank[:8]:
    print(f"  EIP-{r['eip']:<5} in={r['in_degree']:<4} pr={r['pagerank']:<7} #{r['overall_rank']:<3} {r['title'][:42]} [{r['status']}]")

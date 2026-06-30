#!/usr/bin/env python3
"""#11 FULL RUN: fetch discussion-thread engagement for every ERC.
- ethereum-magicians (Discourse): topic JSON (posts, replies, views, participants, likes, dates)
- github.com issues/PRs: comments + reactions via `gh api`
Resumable: each result cached under analysis/discussions/; reruns skip cached ERCs.
Polite: 1.8s throttle + 429 backoff on magicians. Writes erc_discussions.csv."""
import csv, re, json, time, os, subprocess, urllib.request, urllib.error

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ERC-research-bot/1.0 (polite; ~1 req/2s)"
CACHE="analysis/discussions"; os.makedirs(CACHE+"/mag",exist_ok=True); os.makedirs(CACHE+"/gh",exist_ok=True)
rows=list(csv.DictReader(open("erc_dataset.csv")))

def topic_id(url):
    parts=url.split("/")
    if "t" in parts:
        for seg in parts[parts.index("t")+1:]:
            if seg.isdigit(): return seg
    nums=re.findall(r"/(\d+)",url); return nums[0] if nums else None

def gh_ref(url):
    m=re.search(r"github\.com/([^/]+)/([^/]+)/(issues|pull)/(\d+)",url)
    return (m.group(1),m.group(2),m.group(4)) if m else None

def fetch_mag(tid):
    url=f"https://ethereum-magicians.org/t/{tid}.json"
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
            with urllib.request.urlopen(req,timeout=25) as resp:
                j=json.loads(resp.read().decode("utf-8","replace"))
                det=j.get("details",{}) or {}
                return {"ok":True,"http":resp.status,"title":j.get("title",""),
                        "posts":j.get("posts_count"),"replies":j.get("reply_count"),
                        "views":j.get("views"),"participants":len(det.get("participants",[])) or None,
                        "likes":j.get("like_count"),"created_at":(j.get("created_at") or "")[:10],
                        "last_activity":(j.get("last_posted_at") or "")[:10]}
        except urllib.error.HTTPError as e:
            if e.code==429: time.sleep(60); continue
            return {"ok":False,"http":e.code,"note":f"HTTP {e.code}"}
        except Exception as e:
            return {"ok":False,"note":str(e)[:80]}
    return {"ok":False,"note":"429 after retries"}

def fetch_gh(owner,repo,num):
    try:
        out=subprocess.run(["gh","api",f"repos/{owner}/{repo}/issues/{num}",
            "--jq",'{comments,reactions:.reactions.total_count,created_at,updated_at,state}'],
            capture_output=True,text=True,timeout=30)
        if out.returncode!=0: return {"ok":False,"note":out.stderr.strip()[:80]}
        d=json.loads(out.stdout)
        return {"ok":True,"posts":d.get("comments"),"replies":d.get("comments"),
                "reactions":d.get("reactions"),"created_at":(d.get("created_at") or "")[:10],
                "last_activity":(d.get("updated_at") or "")[:10],"state":d.get("state")}
    except Exception as e:
        return {"ok":False,"note":str(e)[:80]}

results=[]; n_mag=n_gh=done=skip=0
for i,r in enumerate(rows):
    erc=r["erc"]; url=(r["discussions_to"] or "").strip()
    rec={"erc":erc,"source":"none","url":url}
    if "ethereum-magicians.org" in url:
        cf=f"{CACHE}/mag/{erc}.json"
        if os.path.exists(cf): rec=json.load(open(cf)); skip+=1
        else:
            tid=topic_id(url); rec.update({"source":"magicians","topic_id":tid})
            rec.update(fetch_mag(tid) if tid else {"ok":False,"note":"no id"})
            json.dump(rec,open(cf,"w")); n_mag+=1; time.sleep(1.8)
            if n_mag%50==0: print(f"  magicians {n_mag} fetched...",flush=True)
    elif "github.com" in url and gh_ref(url):
        cf=f"{CACHE}/gh/{erc}.json"
        if os.path.exists(cf): rec=json.load(open(cf)); skip+=1
        else:
            o,rp,num=gh_ref(url); rec.update({"source":"github"})
            rec.update(fetch_gh(o,rp,num)); json.dump(rec,open(cf,"w")); n_gh+=1; time.sleep(0.2)
    elif url:
        rec["source"]="other"
    results.append(rec); done+=1

COLS=["erc","source","url","title","posts","replies","views","participants","likes","reactions",
      "created_at","last_activity","ok","note"]
with open("erc_discussions.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=COLS,extrasaction="ignore"); w.writeheader()
    for rec in results: w.writerow(rec)

okm=sum(1 for r in results if r["source"]=="magicians" and r.get("ok"))
okg=sum(1 for r in results if r["source"]=="github" and r.get("ok"))
failm=sum(1 for r in results if r["source"]=="magicians" and not r.get("ok"))
print(f"DONE. magicians ok={okm} fail={failm} | github ok={okg} | other={sum(1 for r in results if r['source']=='other')} | none={sum(1 for r in results if r['source']=='none')}")
print(f"(this run fetched {n_mag} magicians + {n_gh} github; {skip} from cache)")

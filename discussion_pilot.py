#!/usr/bin/env python3
"""#11 PILOT: test whether ethereum-magicians (Discourse/Cloudflare) serves topic JSON
to a polite, throttled client. Samples 15 threads across years; reports success vs block."""
import csv, re, json, time, urllib.request, urllib.error

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ERC-research-bot/1.0 (polite; 1 req/2s)"
rows=list(csv.DictReader(open("erc_dataset.csv")))
mag=[r for r in rows if "ethereum-magicians.org" in (r["discussions_to"] or "")]
mag.sort(key=lambda r:r["created"])
# spread 15 across the timeline
idx=[round(i*(len(mag)-1)/14) for i in range(15)]
sample=[mag[i] for i in sorted(set(idx))]

def topic_id(url):
    parts=url.split("/")
    if "t" in parts:
        after=parts[parts.index("t")+1:]
        for seg in after:
            if seg.isdigit(): return seg
    nums=re.findall(r"/(\d+)", url)
    return nums[0] if nums else None

results=[]
for r in sample:
    tid=topic_id(r["discussions_to"])
    if not tid:
        results.append({"erc":r["erc"],"status":"no-id"}); continue
    url=f"https://ethereum-magicians.org/t/{tid}.json"
    rec={"erc":r["erc"],"topic_id":tid}
    for attempt in (1,2):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
            with urllib.request.urlopen(req,timeout=25) as resp:
                body=resp.read().decode("utf-8","replace")
                rec["http"]=resp.status
                try:
                    j=json.loads(body)
                    rec["ok"]=True
                    rec["title"]=j.get("title","")[:50]
                    rec["posts_count"]=j.get("posts_count")
                    rec["reply_count"]=j.get("reply_count")
                    rec["views"]=j.get("views")
                    rec["participants"]=len(j.get("details",{}).get("participants",[])) if j.get("details") else None
                    rec["like_count"]=j.get("like_count")
                    rec["created_at"]=j.get("created_at","")[:10]
                    rec["last_posted_at"]=j.get("last_posted_at","")[:10]
                except json.JSONDecodeError:
                    rec["ok"]=False
                    rec["block_signal"]="non-JSON (cloudflare?)" if ("cloudflare" in body.lower() or "just a moment" in body.lower()) else "non-JSON"
            break
        except urllib.error.HTTPError as e:
            rec["http"]=e.code
            if e.code==429:
                rec["note"]="429 rate-limited"; time.sleep(30); continue
            rec["ok"]=False; rec["note"]=f"HTTP {e.code}"; break
        except Exception as e:
            rec["ok"]=False; rec["note"]=str(e)[:60]; break
    results.append(rec)
    time.sleep(2.0)

ok=[r for r in results if r.get("ok")]
json.dump(results,open("analysis/discussion_pilot.json","w"),indent=1)
print(f"PILOT: {len(ok)}/{len(results)} succeeded")
print(f"{'erc':>6} {'http':>5} {'posts':>6} {'replies':>7} {'views':>7} {'parts':>6}  title")
for r in results:
    if r.get("ok"):
        print(f"{r['erc']:>6} {r.get('http',''):>5} {str(r.get('posts_count')):>6} {str(r.get('reply_count')):>7} {str(r.get('views')):>7} {str(r.get('participants')):>6}  {r.get('title','')}")
    else:
        print(f"{r['erc']:>6} {str(r.get('http','')):>5}  FAIL: {r.get('note') or r.get('block_signal') or r.get('status')}")

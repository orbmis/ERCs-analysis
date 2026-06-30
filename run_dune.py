#!/usr/bin/env python3
"""Minimal Dune API runner. Reuses ONE query (id in .dune_qid or default) by updating its SQL,
executing on the default tier, polling, and printing result rows as JSON.
Key read from .dune_key (gitignored) or env DUNE_API_KEY. Usage: run_dune.py <sql-file>"""
import sys, json, time, os, urllib.request

KEY=(open(".dune_key").read().strip() if os.path.exists(".dune_key") else os.environ.get("DUNE_API_KEY",""))
QID=int(open(".dune_qid").read().strip()) if os.path.exists(".dune_qid") else 7848931
BASE="https://api.dune.com/api/v1"

def req(method, path, body=None):
    r=urllib.request.Request(BASE+path, method=method,
        headers={"X-Dune-API-Key":KEY,"Content-Type":"application/json"},
        data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode())

def run_sql(sql):
    req("PATCH", f"/query/{QID}", {"query_sql": sql})
    ex=req("POST", f"/query/{QID}/execute", {})
    eid=ex["execution_id"]
    for _ in range(60):
        time.sleep(3)
        st=req("GET", f"/execution/{eid}/status")
        state=st.get("state","")
        if state=="QUERY_STATE_COMPLETED": break
        if state in ("QUERY_STATE_FAILED","QUERY_STATE_CANCELLED","QUERY_STATE_EXPIRED"):
            raise RuntimeError(f"execution {state}: {st}")
    res=req("GET", f"/execution/{eid}/results")
    meta=res.get("result",{}).get("metadata",{})
    return res.get("result",{}).get("rows",[]), meta

if __name__=="__main__":
    sql=open(sys.argv[1]).read()
    rows,meta=run_sql(sql)
    print(json.dumps({"rows":rows,"datapoints":meta.get("datapoint_count"),"row_count":meta.get("total_row_count")},indent=1))

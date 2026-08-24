#!/usr/bin/env python3
"""Language-neutral, dependency-free HTTP behavioral verifier."""
import argparse,concurrent.futures,json,sys,time,urllib.error,urllib.request
p=argparse.ArgumentParser();p.add_argument("--base-url",required=True);p.add_argument("--visibility",choices=["developer","hidden","all"],default="all");p.add_argument("--output");a=p.parse_args();base=a.base_url.rstrip("/");counter=0
def request(method,path,body=None,headers=None):
 data=None if body is None else json.dumps(body).encode();req=urllib.request.Request(base+path,data=data,headers={"content-type":"application/json",**(headers or {})},method=method)
 try:
  with urllib.request.urlopen(req,timeout=5) as r:return r.status,dict(r.headers),json.loads(r.read() or b"null")
 except urllib.error.HTTPError as e:return e.code,dict(e.headers),json.loads(e.read() or b"null")
def header(h,n):return next((v for k,v in h.items() if k.lower()==n.lower()),None)
def create(title="case"):
 global counter;counter+=1;s,_,b=request("POST","/tasks",{"title":f"{title}-{counter}","done":False});assert s==201;return b["id"]
def regression_crud():
 i=create("crud");s,_,b=request("GET",f"/tasks/{i}");return s==200 and b["id"]==i and b["done"] is False
def etag_stable():
 i=create("etag");s,h,_=request("GET",f"/tasks/{i}");s2,h2,_=request("GET",f"/tasks/{i}");return s==s2==200 and (header(h,"etag")or"").startswith('"') and header(h,"etag")==header(h2,"etag")
def if_match_required():i=create("required");return request("PATCH",f"/tasks/{i}",{"done":True})[0]==428
def matching_tag_changes():
 i=create("change");_,h,_=request("GET",f"/tasks/{i}");old=header(h,"etag");s,h2,b=request("PATCH",f"/tasks/{i}",{"done":True},{"If-Match":old});return s==200 and b["done"] is True and header(h2,"etag")!=old
def stale_write():
 i=create("stale");_,h,_=request("GET",f"/tasks/{i}");old=header(h,"etag");s,_,_=request("PATCH",f"/tasks/{i}",{"done":True},{"If-Match":old});s2,_,_=request("PATCH",f"/tasks/{i}",{"title":"lost"},{"If-Match":old});return s==200 and s2==412
def concurrent_conflict():
 i=create("race");_,h,_=request("GET",f"/tasks/{i}");old=header(h,"etag")
 def write(n):return request("PUT",f"/tasks/{i}",{"title":f"winner-{n}","done":False},{"If-Match":old})[0]
 with concurrent.futures.ThreadPoolExecutor(2) as ex:statuses=list(ex.map(write,[1,2]))
 return sorted(statuses)==[200,412]
def deleted_stale():
 i=create("delete");_,h,_=request("GET",f"/tasks/{i}");old=header(h,"etag");s,_,_=request("DELETE",f"/tasks/{i}",headers={"If-Match":old});s2,_,_=request("PUT",f"/tasks/{i}",{"title":"zombie","done":False},{"If-Match":old});return s==204 and s2==404
CASES=[("regression-crud","developer",regression_crud),("etag-stable","developer",etag_stable),("if-match-required","hidden",if_match_required),("matching-tag-changes","hidden",matching_tag_changes),("stale-write","hidden",stale_write),("concurrent-conflict","hidden",concurrent_conflict),("deleted-stale","hidden",deleted_stale)];results=[]
for ident,visibility,fn in CASES:
 if a.visibility not in("all",visibility):continue
 start=time.monotonic()
 try:passed=bool(fn());error=None
 except Exception as e:passed=False;error=f"{type(e).__name__}: {e}"
 results.append({"case_id":ident,"passed":passed,"duration_ms":round((time.monotonic()-start)*1000,2),**({"error":error}if error else{})})
report={"schema_version":"1.0.0","passed":all(x["passed"]for x in results),"case_results":results};text=json.dumps(report,indent=2);print(text)
if a.output:open(a.output,"w",encoding="utf-8").write(text+"\n")
sys.exit(0 if report["passed"]else 1)

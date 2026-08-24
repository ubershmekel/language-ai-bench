#!/usr/bin/env python3
"""Visible happy-path checks only; hidden semantics stay in tests/verify.py."""
import argparse,json,urllib.request
p=argparse.ArgumentParser();p.add_argument("--base-url",required=True);a=p.parse_args();base=a.base_url.rstrip("/")
def req(method,path,body=None):
 data=None if body is None else json.dumps(body).encode();r=urllib.request.Request(base+path,data=data,headers={"content-type":"application/json"},method=method)
 with urllib.request.urlopen(r,timeout=5) as response:return response.status,dict(response.headers),json.loads(response.read()or b"null")
s,_,created=req("POST","/tasks",{"title":"developer","done":False});assert s==201
s,h,body=req("GET",f"/tasks/{created['id']}");assert s==200 and body==created
etag=next((v for k,v in h.items()if k.lower()=="etag"),None);assert etag and etag.startswith('"')
_,h2,_=req("GET",f"/tasks/{created['id']}");etag2=next(v for k,v in h2.items()if k.lower()=="etag");assert etag==etag2
print("developer checks: PASS")

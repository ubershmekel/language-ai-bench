#!/usr/bin/env python3
import argparse,collections,json,pathlib
p=argparse.ArgumentParser();p.add_argument("results",nargs="?",default="results");a=p.parse_args();runs=[json.loads(p.read_text()) for p in pathlib.Path(a.results).rglob("run.json")];groups=collections.defaultdict(list)
for r in runs:groups[(r["task_family"],r["language"],r["typecheck_config"])].append(r)
out=[]
for key,items in sorted(groups.items()):
    passed=sum(x["terminal_stage"]=="passed" for x in items);out.append({"task_family":key[0],"language":key[1],"typecheck_config":key[2],"runs":len(items),"passed":passed,"pass_rate":passed/len(items),"total_cost_usd":sum(x["measured_cost_usd"] for x in items)})
print(json.dumps({"cells":out,"warning":"Do not collapse task families into one score."},indent=2))


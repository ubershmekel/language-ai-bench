#!/usr/bin/env python3
"""Create a secret-minimized GitHub Pages data file from validated run summaries."""
import argparse,collections,datetime,json,pathlib
p=argparse.ArgumentParser();p.add_argument("--results",default="results");p.add_argument("--output",default="docs/data/public-summary.json");a=p.parse_args()
runs=[json.loads(path.read_text()) for path in pathlib.Path(a.results).rglob("run.json")];groups=collections.defaultdict(list)
for run in runs:groups[(run["task_family"],run["language"],run["typecheck_config"],run["model"],run["scaffold"])].append(run)
cells=[]
for key,items in sorted(groups.items()):
 passed=sum(x["terminal_stage"]=="passed" for x in items);cost=sum(float(x["measured_cost_usd"]) for x in items)
 cells.append({"task_family":key[0],"language":key[1],"typecheck_config":key[2],"model":key[3],"scaffold":key[4],"runs":len(items),"passed":passed,"pass_rate":passed/len(items),"measured_cost_usd":round(cost,8),"input_tokens":sum(x["usage"]["input_tokens"] for x in items),"output_tokens":sum(x["usage"]["output_tokens"] for x in items)})
public={"schema_version":"1.0.0","generated_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"cells":cells,"warning":"One task family is pipeline evidence, not a language leaderboard."};text=json.dumps(public,indent=2)+"\n"
if "sk-or-" in text or "API_KEY" in text:raise SystemExit("secret-like content detected")
out=pathlib.Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(text.encode("utf-8"));print(f"wrote {out} ({len(cells)} cells)")

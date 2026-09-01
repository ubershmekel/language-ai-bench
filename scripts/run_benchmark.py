#!/usr/bin/env python3
"""Zero-cost pipeline runner; real model execution is delegated to Pier."""
import argparse,datetime,hashlib,json,pathlib,random,subprocess,sys,uuid
ROOT=pathlib.Path(__file__).resolve().parents[1]
def read(path):return json.loads(pathlib.Path(path).read_text())
def write(path,value):path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+"\n")
def git_rev():
 try:return subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()
 except Exception:return "unknown"
def image_digest(language,kind):
 try:return subprocess.run(["docker","image","inspect",f"language-ai-bench/{language}:{kind}","--format={{.Id}}"],text=True,capture_output=True,check=True).stdout.strip() or "local-image-no-repodigest"
 except Exception:return "unavailable"
def main():
 p=argparse.ArgumentParser();p.add_argument("--agent",choices=["mock-solve","mock-plausible-fail"],default="mock-solve");p.add_argument("--seeds",type=int,default=1);p.add_argument("--model",default="mock/no-model");p.add_argument("--reasoning-effort",default="none");p.add_argument("--dry-run",action="store_true");p.add_argument("--acknowledge-projection",action="store_true");p.add_argument("--measured-cost-per-rollout-usd",type=float,default=0);p.add_argument("--max-spend-usd",type=float,required=True);p.add_argument("--simulate-cost-usd",type=float,default=0);p.add_argument("--results-dir",default=str(ROOT/"results"));p.add_argument("--state-file",default=str(ROOT/".benchmark-state"/"spend.json"));a=p.parse_args()
 config=read(ROOT/"benchmark.json");cells=config["cells"]*a.seeds;projected=a.measured_cost_per_rollout_usd*len(cells);print(f"cells={len(cells)} projected_cost_usd={projected:.6f} max_spend_usd={a.max_spend_usd:.6f}")
 if a.dry_run:return 0
 if not a.acknowledge_projection:p.error("execution requires --acknowledge-projection after reviewing --dry-run")
 calibration=read(ROOT/"calibration"/"calibration_report.json");
 if not calibration["green"]:raise SystemExit("calibration is not green")
 state_path=pathlib.Path(a.state_file);state=read(state_path) if state_path.exists() else {"schema_version":"1.0.0","spent_usd":0.0,"completed_rollouts":0}
 if state["spent_usd"]>=a.max_spend_usd:raise SystemExit("persisted spend already meets/exceeds ceiling")
 random.Random(20260824).shuffle(cells);runs=[];date=datetime.date.today().isoformat();outroot=pathlib.Path(a.results_dir)/a.model.replace("/","_")/date
 for order,cell in enumerate(cells):
  language=cell["language"];source="reference" if a.agent=="mock-solve" else "null";cases=calibration["runs"][language][source]["case_results"];passed=all(x["passed"] for x in cases);run_id=str(uuid.uuid4());folder=outroot/run_id;folder.mkdir(parents=True,exist_ok=True);now=datetime.datetime.now(datetime.timezone.utc).isoformat();events=[]
  events.append({"schema_version":"1.0.0","index":0,"timestamp":now,"kind":"command","command":"inspect repository","tool":"shell","duration_ms":3,"output_bytes":120,"output_lines":4})
  if a.agent=="mock-solve":
   if language in("typescript","go"):
    events += [{"schema_version":"1.0.0","index":1,"timestamp":now,"kind":"diagnostic","tool":"compiler","diagnostic_id":"mock-type-1","location":"src/server","active_diagnostic_ids":["mock-type-1"]},{"schema_version":"1.0.0","index":2,"timestamp":now,"kind":"edit","locations":["src/server"],"bytes_changed":800},{"schema_version":"1.0.0","index":3,"timestamp":now,"kind":"diagnostic","tool":"compiler","diagnostic_id":"compiler-pass","location":"src/server","active_diagnostic_ids":[]}]
   else:events.append({"schema_version":"1.0.0","index":1,"timestamp":now,"kind":"edit","locations":["src/server"],"bytes_changed":800})
  events.append({"schema_version":"1.0.0","index":len(events),"timestamp":now,"kind":"verifier","case_results":cases})
  (folder/"events.jsonl").write_text("".join(json.dumps(e)+"\n" for e in events));cost=a.simulate_cost_usd;state["spent_usd"]+=cost;state["completed_rollouts"]+=1;write(state_path,state)
  usage={"input_tokens":0,"output_tokens":0,"cached_input_tokens":0,"max_context_occupancy":0,"tool_output_tokens":0};run={"schema_version":"1.0.0","benchmark_version":config["benchmark_version"],"task_family":config["task_family"],"language":language,"typecheck_config":cell["typecheck_config"],"repo_revision":git_rev(),"container_image_digest":image_digest(language,source),"model":a.model,"model_settings":{"reasoning_effort":a.reasoning_effort},"scaffold":"local-mock/bash-only-compatible","agent_version":a.agent,"pier_version":"not-invoked-local-mock","malformed_action_count":0,"run_id":run_id,"seed":order%a.seeds,"order_index":order,"toolchain_versions":{},"started_at":now,"ended_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"verifier_case_results":cases,"regression_results":[x for x in cases if x["case_id"].startswith("regression-")],"calibration_ref":"calibration/calibration_report.json","usage":usage,"cache_hit_rate":0,"measured_cost_usd":cost,"rate_card":{"input_per_million":0,"cached_input_per_million":0,"output_per_million":0,"currency":"USD"},"command_counts":{"shell":1,"edit":sum(e["kind"]=="edit" for e in events),"test":1,"build_or_typecheck":sum(e.get("tool")=="compiler" for e in events)},"feedback_to_fix_events":[],"patch_statistics":{"files_modified":1 if a.agent=="mock-solve" else 0,"lines_added":20 if a.agent=="mock-solve" else 0,"lines_deleted":0},"terminal_stage":"passed" if passed else "passed-dev-tests-failed-hidden","root_causes":[] if passed else [{"label":"incomplete implementation","evidence_event_index":len(events)-1}],"stopped_reason":"completed","exit_status":0 if passed else 1};write(folder/"run.json",run);runs.append(run)
  projected_live=state["spent_usd"]/(order+1)*len(cells);print(f"{language}: {'PASS' if passed else 'FAIL'} spend={state['spent_usd']:.6f} projected={projected_live:.6f} remaining={a.max_spend_usd-state['spent_usd']:.6f}")
  if state["spent_usd"]>a.max_spend_usd:print("spend ceiling crossed; aborting whole matrix",file=sys.stderr);break
 by_language={l:{"cost_usd":sum(x["measured_cost_usd"]for x in runs if x["language"]==l),"runs":sum(x["language"]==l for x in runs)}for l in sorted({x["language"]for x in runs})};by_outcome={o:sum(x["measured_cost_usd"]for x in runs if x["terminal_stage"]==o)for o in sorted({x["terminal_stage"]for x in runs})};write(outroot/"spend_report.json",{"schema_version":"1.0.0","total_cost_usd":sum(x["measured_cost_usd"]for x in runs),"by_language":by_language,"by_cell":{f"{x['language']}/{x['typecheck_config']}":x["measured_cost_usd"] for x in runs},"by_outcome":by_outcome})
 return 2 if len(runs)<len(cells) else 0
if __name__=="__main__":raise SystemExit(main())


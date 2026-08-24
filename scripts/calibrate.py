#!/usr/bin/env python3
"""Build and run the free, blocking four-language verifier-parity gate."""
import argparse, json, pathlib, subprocess, sys, tempfile, time, urllib.error, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];TASK=ROOT/"tasks"/"optimistic-concurrency";LANGUAGES=("javascript","typescript","python","go")
SABOTAGES=("off-by-one","missing-error-branch","wrong-status-code","unhandled-concurrent-update")
def run(cmd,check=True,capture=False):
    return subprocess.run(cmd,cwd=ROOT,check=check,text=True,capture_output=capture)
def build(language,kind):
    folder=TASK/language;dockerfile=folder/"environment"/("solution.Dockerfile" if kind=="reference" else "Dockerfile");tag=f"language-ai-bench/{language}:{kind}"
    print(f"building {tag}",flush=True);run(["docker","build","-f",str(dockerfile),"-t",tag,str(folder)]);return tag
def wait_ready(port,timeout=20):
    start=time.monotonic();url=f"http://127.0.0.1:{port}/tasks/1"
    while time.monotonic()-start<timeout:
        try:
            with urllib.request.urlopen(url,timeout=1):return round((time.monotonic()-start)*1000,2)
        except (OSError,urllib.error.URLError):time.sleep(.05)
    raise RuntimeError("readiness timeout")
def verify(tag,sabotage=None):
    cmd=["docker","run","-d","--rm","-P"]
    if sabotage:cmd += ["-e",f"LAB_SABOTAGE={sabotage}"]
    cid=run(cmd+[tag],capture=True).stdout.strip()
    try:
        deadline=time.monotonic()+10;port=None
        while time.monotonic()<deadline and not port:
            out=run(["docker","port",cid,"8080/tcp"],check=False,capture=True).stdout.strip()
            if out:port=int(out.rsplit(":",1)[1])
            else:time.sleep(.05)
        if not port:raise RuntimeError("Docker did not publish port")
        startup=wait_ready(port)
        with tempfile.NamedTemporaryFile(suffix=".json",delete=False) as f:path=pathlib.Path(f.name)
        proc=run([sys.executable,str(TASK/"verifier"/"verify.py"),"--base-url",f"http://127.0.0.1:{port}","--output",str(path)],check=False,capture=True)
        report=json.loads(path.read_text());path.unlink(missing_ok=True);report["startup_ms"]=startup;report["verifier_exit_status"]=proc.returncode;return report
    finally:run(["docker","rm","-f",cid],check=False,capture=True)
def failed(report):return sorted(x["case_id"] for x in report["case_results"] if not x["passed"])
def main():
    p=argparse.ArgumentParser();p.add_argument("--no-build",action="store_true");p.add_argument("--output",default=str(ROOT/"calibration_report.json"));args=p.parse_args();matrix={}
    for language in LANGUAGES:
        baseline=f"language-ai-bench/{language}:baseline";reference=f"language-ai-bench/{language}:reference"
        if not args.no_build:baseline=build(language,"baseline");reference=build(language,"reference")
        matrix[language]={"reference":verify(reference),"null":verify(baseline),"sabotages":{s:verify(reference,s) for s in SABOTAGES}}
    ref_green=all(v["reference"]["passed"] for v in matrix.values())
    null_sets={k:failed(v["null"]) for k,v in matrix.items()};null_parity=len({tuple(v) for v in null_sets.values()})==1 and bool(next(iter(null_sets.values())))
    sabotage_sets={s:{k:failed(v["sabotages"][s]) for k,v in matrix.items()} for s in SABOTAGES}
    sabotage_parity=all(len({tuple(x) for x in langs.values()})==1 and bool(next(iter(langs.values()))) for langs in sabotage_sets.values())
    report={"schema_version":"1.0.0","benchmark_version":"0.1.0","generated_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"green":ref_green and null_parity and sabotage_parity,"checks":{"reference_100_percent":ref_green,"null_failure_parity":null_parity,"sabotage_failure_parity":sabotage_parity},"null_failure_sets":null_sets,"sabotage_failure_sets":sabotage_sets,"runs":matrix}
    pathlib.Path(args.output).write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report["checks"],indent=2));return 0 if report["green"] else 1
if __name__=="__main__":raise SystemExit(main())


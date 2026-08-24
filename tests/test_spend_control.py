import pathlib,subprocess,sys,tempfile,json
ROOT=pathlib.Path(__file__).resolve().parents[1]
def test_persisted_spend_aborts_mid_matrix():
 with tempfile.TemporaryDirectory() as d:
  d=pathlib.Path(d);cmd=[sys.executable,str(ROOT/"scripts"/"run_benchmark.py"),"--agent","mock-solve","--max-spend-usd","0.015","--simulate-cost-usd","0.01","--acknowledge-projection","--state-file",str(d/"spend.json"),"--results-dir",str(d/"results")];first=subprocess.run(cmd,cwd=ROOT);assert first.returncode==2;assert json.loads((d/"spend.json").read_text())["spent_usd"]==0.02;second=subprocess.run(cmd,cwd=ROOT);assert second.returncode!=0

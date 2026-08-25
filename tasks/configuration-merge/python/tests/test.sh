#!/bin/sh
set -u
python /tests/verify.py --output /logs/verifier/details.json --command python src/config_merge.py
status=$?
python -c 'import json;d=json.load(open("/logs/verifier/details.json"));open("/logs/verifier/reward.txt","w").write("1\n" if d["passed"] else "0\n")'
exit $status

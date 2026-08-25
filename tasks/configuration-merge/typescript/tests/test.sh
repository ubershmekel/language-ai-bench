#!/bin/sh
set -u
npm run build
build_status=$?
if [ $build_status -ne 0 ]; then exit $build_status; fi
python3 /tests/verify.py --output /logs/verifier/details.json --command node dist/config_merge.js
status=$?
python3 -c 'import json;d=json.load(open("/logs/verifier/details.json"));open("/logs/verifier/reward.txt","w").write("1\n" if d["passed"] else "0\n")'
exit $status

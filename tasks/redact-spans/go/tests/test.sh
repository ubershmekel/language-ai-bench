#!/bin/sh
set -u
go build -o /tmp/redact-spans ./src
python3 /tests/verify.py --output /logs/verifier/details.json --command /tmp/redact-spans
status=$?
python3 -c 'import json;d=json.load(open("/logs/verifier/details.json"));open("/logs/verifier/reward.txt","w").write("1\n" if d["passed"] else "0\n")'
exit $status

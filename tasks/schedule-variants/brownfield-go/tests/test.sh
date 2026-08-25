#!/bin/sh
set -u
go build -o /tmp/task-server ./src || { mkdir -p /logs/verifier; echo 0 > /logs/verifier/reward.txt; exit 1; }
/tmp/task-server & pid=$!;trap 'kill $pid 2>/dev/null || true' EXIT
python3 /tests/wait_ready.py --url http://127.0.0.1:8080/jobs/1 || exit 1
python3 /tests/verify.py --base-url http://127.0.0.1:8080 --output /logs/verifier/details.json;status=$?
python3 -c 'import json;d=json.load(open("/logs/verifier/details.json"));open("/logs/verifier/reward.txt","w").write("1\n" if d["passed"] else "0\n")'
exit $status

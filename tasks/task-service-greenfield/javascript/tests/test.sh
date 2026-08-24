#!/bin/sh
set -u
node src/server.js & pid=$!;trap 'kill $pid 2>/dev/null || true' EXIT
python3 /tests/wait_ready.py --url http://127.0.0.1:8080/tasks/1 || exit 1
python3 /tests/verify.py --base-url http://127.0.0.1:8080 --output /logs/verifier/details.json;status=$?
python3 -c 'import json;d=json.load(open("/logs/verifier/details.json"));open("/logs/verifier/reward.txt","w").write("1\n" if d["passed"] else "0\n")'
exit $status

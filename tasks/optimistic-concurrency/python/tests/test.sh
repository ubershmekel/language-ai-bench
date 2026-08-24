#!/bin/sh
set -u
python src/server.py & pid=$!;trap 'kill $pid 2>/dev/null || true' EXIT
python /tests/wait_ready.py --url http://127.0.0.1:8080/tasks/1 || exit 1
python /tests/verify.py --base-url http://127.0.0.1:8080 --output /logs/verifier/details.json;status=$?
python -c 'import json;d=json.load(open("/logs/verifier/details.json"));open("/logs/verifier/reward.txt","w").write("1\n" if d["passed"] else "0\n")'
exit $status

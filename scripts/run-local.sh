#!/bin/sh
set -eu
python3 scripts/calibrate.py --languages javascript typescript python python-typed go
python3 scripts/run_benchmark.py --agent mock-solve --max-spend-usd 1 --dry-run
python3 scripts/run_benchmark.py --agent mock-solve --max-spend-usd 1 --acknowledge-projection
python3 scripts/run_benchmark.py --agent mock-plausible-fail --max-spend-usd 1 --acknowledge-projection
python3 analysis/aggregate.py results

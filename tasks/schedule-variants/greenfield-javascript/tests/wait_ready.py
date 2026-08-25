#!/usr/bin/env python3
import argparse, sys, time, urllib.error, urllib.request

p = argparse.ArgumentParser()
p.add_argument("--url", required=True)
p.add_argument("--timeout", type=float, default=15)
a = p.parse_args()
start = time.monotonic()
while time.monotonic() - start < a.timeout:
    try:
        with urllib.request.urlopen(a.url, timeout=1):
            print(f"ready_ms={int((time.monotonic()-start)*1000)}")
            sys.exit(0)
    except (OSError, urllib.error.URLError):
        time.sleep(0.05)
print("readiness timeout", file=sys.stderr)
sys.exit(1)

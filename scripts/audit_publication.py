#!/usr/bin/env python3
"""Fail publication when tracked files contain common secret material."""

from __future__ import annotations

import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATTERNS = {
    "OpenRouter key": re.compile(rb"sk-or-v1-[A-Za-z0-9_-]{20,}"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "assigned API key": re.compile(rb"(?:OPENROUTER_API_KEY|API_KEY)\s*=\s*[^<\s][^\r\n]*"),
}
ALLOW_ASSIGNED_KEY = {".env.example", "docs/RUNNING_PAID.md"}


def tracked_files() -> list[pathlib.Path]:
    result = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT, capture_output=True, check=True)
    return [ROOT / item.decode() for item in result.stdout.split(b"\0") if item]


def audit(paths: list[pathlib.Path]) -> list[str]:
    findings = []
    for path in paths:
        if not path.is_file():
            continue
        data = path.read_bytes()
        relative = path.relative_to(ROOT).as_posix()
        for label, pattern in PATTERNS.items():
            if label == "assigned API key" and relative in ALLOW_ASSIGNED_KEY:
                continue
            if pattern.search(data):
                findings.append(f"{relative}: {label}")
    return findings


def main() -> int:
    findings = audit(tracked_files())
    if findings:
        print("publication blocked:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("publication audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

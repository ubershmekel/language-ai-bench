#!/usr/bin/env python3
"""Patch Pier 0.3.1's Windows-generated Squid script to use Linux line endings."""

from __future__ import annotations

import importlib.metadata
import os
from pathlib import Path

PACKAGE = "datacurve-pier"
SUPPORTED_VERSION = "0.3.1"
OLD = '(proxy_dir / "start-squid.sh").write_text(squid_bootstrap_command())'
NEW = (
    '(proxy_dir / "start-squid.sh").write_bytes('
    'squid_bootstrap_command().encode("utf-8"))'
)


def main() -> None:
    if os.name != "nt":
        print("Pier proxy patch is unnecessary outside Windows.")
        return

    version = importlib.metadata.version(PACKAGE)
    if version != SUPPORTED_VERSION:
        raise SystemExit(
            f"Refusing to patch {PACKAGE} {version}; expected {SUPPORTED_VERSION}."
        )

    import pier.environments.agent_setup as agent_setup

    path = Path(agent_setup.__file__).resolve()
    source = path.read_text(encoding="utf-8")
    if NEW in source:
        print(f"Pier Windows proxy patch already applied: {path}")
        return
    if OLD not in source:
        raise SystemExit(f"Expected Pier source line not found: {path}")

    path.write_text(source.replace(OLD, NEW), encoding="utf-8", newline="\n")
    print(f"Applied Pier Windows proxy LF patch: {path}")


if __name__ == "__main__":
    main()

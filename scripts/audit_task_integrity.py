#!/usr/bin/env python3
"""Reject benchmark fixtures that are packed, divergent, or contaminated."""

from __future__ import annotations

import pathlib
import subprocess
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
TASKS = ROOT / "tasks"
SOURCE_SUFFIXES = {".js", ".ts", ".py", ".go"}
FORBIDDEN_PARTS = {"__pycache__", ".mypy_cache", "node_modules", "dist"}
MAX_LINE_LENGTH = 140


def task_directories() -> list[pathlib.Path]:
    return sorted(path.parent for path in TASKS.rglob("task.toml"))


def metadata(task_dir: pathlib.Path) -> dict:
    with (task_dir / "task.toml").open("rb") as handle:
        return tomllib.load(handle)["metadata"]


def tracked_task_paths() -> list[pathlib.Path]:
    output = subprocess.run(
        ["git", "ls-files", "tasks"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    return [ROOT / line for line in output.splitlines()]


def source_files(root: pathlib.Path) -> dict[pathlib.Path, pathlib.Path]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root): path
        for path in root.rglob("*")
        if path.is_file() and path.suffix in SOURCE_SUFFIXES
    }


def audit() -> list[str]:
    errors: list[str] = []
    tasks = task_directories()
    families: dict[tuple[str, str], list[pathlib.Path]] = {}

    for task_dir in tasks:
        item = metadata(task_dir)
        group = (item["task_family"], item["project_maturity"])
        families.setdefault(group, []).append(task_dir)
        visible = source_files(task_dir / "src")
        packaged = source_files(task_dir / "environment" / "src")
        if set(visible) != set(packaged):
            errors.append(
                f"{task_dir.relative_to(ROOT)}: src/environment source file sets differ"
            )
        for relative in sorted(set(visible) & set(packaged)):
            if visible[relative].read_bytes() != packaged[relative].read_bytes():
                errors.append(
                    f"{task_dir.relative_to(ROOT)}: environment/src/{relative} "
                    "differs from src"
                )

        for area in ("src", "solution"):
            for _, path in source_files(task_dir / area).items():
                for number, line in enumerate(
                    path.read_text(encoding="utf-8").splitlines(), 1
                ):
                    if len(line) > MAX_LINE_LENGTH:
                        errors.append(
                            f"{path.relative_to(ROOT)}:{number}: "
                            f"line length {len(line)} exceeds {MAX_LINE_LENGTH}"
                        )

    for (family, maturity), members in sorted(families.items()):
        prompt_bytes = {
            member.joinpath("instruction.md").read_bytes() for member in members
        }
        if len(prompt_bytes) != 1:
            errors.append(
                f"{family}/{maturity}: language instructions are not byte-identical"
            )

        # A family may put its contract in the workspace as SPEC.md instead of in
        # the instruction. It then has to be identical everywhere the agent can
        # read it, or the arms are not solving the same task.
        specs = {
            member.joinpath("SPEC.md").read_bytes()
            for member in members
            if member.joinpath("SPEC.md").exists()
        }
        if specs and len(specs) != 1:
            errors.append(f"{family}/{maturity}: language specs are not byte-identical")
        for member in members:
            outer = member / "SPEC.md"
            inner = member / "environment" / "SPEC.md"
            if outer.exists() != inner.exists():
                errors.append(f"{member.relative_to(ROOT)}: SPEC.md is not mirrored")
            elif outer.exists() and outer.read_bytes() != inner.read_bytes():
                errors.append(f"{member.relative_to(ROOT)}: SPEC.md copies differ")

        shared_verifier = TASKS / family / "verifier" / "verify.py"
        if shared_verifier.exists():
            expected = shared_verifier.read_bytes()
            for member in members:
                task_verifier = member / "tests" / "verify.py"
                if not task_verifier.exists() or task_verifier.read_bytes() != expected:
                    errors.append(
                        f"{member.relative_to(ROOT)}: hidden verifier differs from shared verifier"
                    )

    for path in tracked_task_paths():
        if any(part in FORBIDDEN_PARTS for part in path.parts):
            errors.append(f"forbidden generated path: {path.relative_to(ROOT)}")
        if path.is_file() and path.suffix in {".pyc", ".class", ".exe"}:
            errors.append(f"forbidden generated file: {path.relative_to(ROOT)}")

    return errors


def main() -> int:
    errors = audit()
    if errors:
        print("\n".join(errors))
        return 1
    print(
        f"task integrity audit passed: {len(task_directories())} task variants, "
        f"max source line {MAX_LINE_LENGTH}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

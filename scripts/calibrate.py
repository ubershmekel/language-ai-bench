#!/usr/bin/env python3
"""Build and run the free, blocking verifier-parity calibration gate."""

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_TASK = ROOT / "tasks" / "optimistic-concurrency"
DEFAULT_LANGUAGES = ("javascript", "typescript", "python", "go")
DEFAULT_SABOTAGES = (
    "off-by-one",
    "missing-error-branch",
    "wrong-status-code",
    "unhandled-concurrent-update",
)


def run(cmd, *, check=True, capture=False):
    return subprocess.run(
        cmd, cwd=ROOT, check=check, text=True, capture_output=capture
    )


def build(task_dir, language, kind):
    folder = task_dir / language
    dockerfile = folder / "environment" / (
        "solution.Dockerfile" if kind == "reference" else "Dockerfile"
    )
    tag = f"language-ai-bench/{task_dir.name}-{language}:{kind}"
    print(f"building {tag}", flush=True)
    run(["docker", "build", "-f", str(dockerfile), "-t", tag, str(folder)])
    return tag


def wait_ready(port, readiness_path="/tasks/1", timeout=20):
    start = time.monotonic()
    url = f"http://127.0.0.1:{port}{readiness_path}"
    while time.monotonic() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return round((time.monotonic() - start) * 1000, 2)
        except (OSError, urllib.error.URLError):
            time.sleep(0.05)
    raise RuntimeError("readiness timeout")


def verify_http(task_dir, tag, sabotage=None, readiness_path="/tasks/1"):
    cmd = ["docker", "run", "-d", "--rm", "-P"]
    if sabotage:
        cmd += ["-e", f"LAB_SABOTAGE={sabotage}"]
    cid = run(cmd + [tag], capture=True).stdout.strip()
    try:
        deadline = time.monotonic() + 10
        port = None
        while time.monotonic() < deadline and not port:
            output = run(
                ["docker", "port", cid, "8080/tcp"], check=False, capture=True
            ).stdout.strip()
            if output:
                port = int(output.rsplit(":", 1)[1])
            else:
                time.sleep(0.05)
        if not port:
            raise RuntimeError("Docker did not publish port")
        startup = wait_ready(port, readiness_path)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
            report_path = pathlib.Path(handle.name)
        proc = run(
            [
                sys.executable,
                str(task_dir / "verifier" / "verify.py"),
                "--base-url",
                f"http://127.0.0.1:{port}",
                "--output",
                str(report_path),
            ],
            check=False,
            capture=True,
        )
        report = json.loads(report_path.read_text())
        report_path.unlink(missing_ok=True)
        report["startup_ms"] = startup
        report["verifier_exit_status"] = proc.returncode
        return report
    finally:
        run(["docker", "rm", "-f", cid], check=False, capture=True)


def verify_command(task_dir, tag, sabotage=None):
    cmd = [
        sys.executable,
        str(task_dir / "verifier" / "verify.py"),
        "--docker-image",
        tag,
    ]
    if sabotage:
        cmd += ["--sabotage", sabotage]
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
        report_path = pathlib.Path(handle.name)
    proc = run(cmd + ["--output", str(report_path)], check=False, capture=True)
    report = json.loads(report_path.read_text())
    report_path.unlink(missing_ok=True)
    report["verifier_exit_status"] = proc.returncode
    return report


def failed(report):
    return sorted(item["case_id"] for item in report["case_results"] if not item["passed"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--task-dir", type=pathlib.Path, default=DEFAULT_TASK)
    parser.add_argument("--languages", nargs="+", default=list(DEFAULT_LANGUAGES))
    parser.add_argument("--readiness-path", default="/tasks/1")
    parser.add_argument("--output", default=str(ROOT / "calibration_report.json"))
    args = parser.parse_args()
    task_dir = args.task_dir.resolve()
    calibration_config_path = task_dir / "calibration" / "config.json"
    calibration_config = (
        json.loads(calibration_config_path.read_text())
        if calibration_config_path.exists()
        else {"mode": "http", "sabotages": list(DEFAULT_SABOTAGES)}
    )
    mode = calibration_config.get("mode", "http")
    sabotages = tuple(calibration_config.get("sabotages", DEFAULT_SABOTAGES))
    if mode not in ("http", "command"):
        raise SystemExit(f"unsupported calibration mode: {mode}")
    matrix = {}

    for language in args.languages:
        baseline = f"language-ai-bench/{task_dir.name}-{language}:baseline"
        reference = f"language-ai-bench/{task_dir.name}-{language}:reference"
        if not args.no_build:
            baseline = build(task_dir, language, "baseline")
            reference = build(task_dir, language, "reference")
        verify = verify_command if mode == "command" else verify_http
        verify_kwargs = {} if mode == "command" else {"readiness_path": args.readiness_path}
        matrix[language] = {
            "reference": verify(task_dir, reference, **verify_kwargs),
            "null": verify(task_dir, baseline, **verify_kwargs),
            "sabotages": {
                sabotage: verify(task_dir, reference, sabotage, **verify_kwargs)
                for sabotage in sabotages
            },
        }

    reference_green = all(value["reference"]["passed"] for value in matrix.values())
    null_sets = {key: failed(value["null"]) for key, value in matrix.items()}
    null_parity = (
        len({tuple(value) for value in null_sets.values()}) == 1
        and bool(next(iter(null_sets.values())))
    )
    sabotage_sets = {
        sabotage: {
            key: failed(value["sabotages"][sabotage])
            for key, value in matrix.items()
        }
        for sabotage in sabotages
    }
    sabotage_parity = all(
        len({tuple(value) for value in languages.values()}) == 1
        and bool(next(iter(languages.values())))
        for languages in sabotage_sets.values()
    )
    report = {
        "schema_version": "1.0.0",
        "benchmark_version": "0.2.0",
        "task_family": task_dir.name,
        "mode": mode,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "green": reference_green and null_parity and sabotage_parity,
        "checks": {
            "reference_100_percent": reference_green,
            "null_failure_parity": null_parity,
            "sabotage_failure_parity": sabotage_parity,
        },
        "null_failure_sets": null_sets,
        "sabotage_failure_sets": sabotage_sets,
        "runs": matrix,
    }
    output = pathlib.Path(args.output)
    output.write_bytes((json.dumps(report, indent=2) + "\n").encode("utf-8"))
    print(json.dumps(report["checks"], indent=2))
    return 0 if report["green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

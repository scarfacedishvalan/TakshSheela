"""
run_scenario.py — Run a materialized scenario workspace repeatedly to detect fault expression.

Usage:
    python tools/run_scenario.py --problem <problem_id> --scenario <scenario_id> [--runs N]

Reads workspace location from tools/config.json.

Runs run_batch.py N times (default 20) and reports how often the fault manifests
as a non-zero discrepancy in reporter_complete log events.

Output: JSON to stdout.

A mismatch_ratio of 0.0 means the fault never expressed — the scenario needs a stress
job file or more threads to reliably surface the race.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


CONFIG_PATH = Path(__file__).parent / "config.json"
DEFAULT_RUNS = 20


def load_config():
    if not CONFIG_PATH.exists():
        print(f"ERROR: config not found: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def build_env(workspace):
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    ws_str = str(workspace.resolve())
    env["PYTHONPATH"] = ws_str + os.pathsep + existing if existing else ws_str
    return env


def read_discrepancy_from_logs(workspace):
    """Read the last reporter_complete event from the log and return its discrepancy field."""
    log_path = workspace / "logs" / "nightproc.log"
    if not log_path.exists():
        return None

    discrepancy = None
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                if event.get("event") == "reporter_complete":
                    discrepancy = event.get("discrepancy")
            except Exception:
                continue
    return discrepancy


def run_once(workspace, env):
    sample_jobs = workspace / "jobs" / "sample_jobs.json"
    result = subprocess.run(
        [sys.executable, str(workspace / "run_batch.py"), str(sample_jobs)],
        cwd=workspace,
        env=env,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return {"crashed": True, "mismatch": False, "discrepancy": None}

    discrepancy = read_discrepancy_from_logs(workspace)
    return {
        "crashed": False,
        "mismatch": discrepancy is not None and discrepancy != 0,
        "discrepancy": discrepancy,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run a scenario workspace repeatedly to detect fault expression.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--problem",  required=True, help="Problem ID, e.g. prob-001")
    parser.add_argument("--scenario", required=True, help="Scenario ID, e.g. scen-001")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS, help=f"Number of runs (default {DEFAULT_RUNS})")
    args = parser.parse_args()

    cfg = load_config()
    workspace = Path(cfg["workspace_root"]) / args.problem

    if not workspace.exists():
        print(json.dumps({"error": f"workspace not found: {workspace}"}))
        sys.exit(1)

    env = build_env(workspace)
    mismatch_count = 0
    crash_count = 0
    discrepancies = []

    for _ in range(args.runs):
        r = run_once(workspace, env)
        if r["crashed"]:
            crash_count += 1
        if r["mismatch"]:
            mismatch_count += 1
        if r["discrepancy"] is not None:
            discrepancies.append(r["discrepancy"])

    output = {
        "problem":         args.problem,
        "scenario":        args.scenario,
        "runs":            args.runs,
        "crash_count":     crash_count,
        "mismatch_count":  mismatch_count,
        "mismatch_ratio":  round(mismatch_count / args.runs, 3),
        "discrepancies":   discrepancies,
        "fault_expressed": mismatch_count > 0,
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

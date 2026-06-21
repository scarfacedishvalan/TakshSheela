import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


TOTAL_RUNS = 20


def build_env(repo_root: Path):
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    repo_str = str(repo_root.resolve())

    if existing:
        env["PYTHONPATH"] = repo_str + os.pathsep + existing
    else:
        env["PYTHONPATH"] = repo_str

    return env


def read_report(repo_root: Path):
    report_path = repo_root / "report.json"

    if not report_path.exists():
        return None

    with open(report_path) as f:
        return json.load(f)


def detect_discrepancy_from_logs(repo_root: Path):
    log_path = repo_root / "logs" / "nightproc.log"

    if not log_path.exists():
        return None

    discrepancy = None

    with open(log_path, "r", encoding="utf-8") as f:
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


def run_once(repo_root: Path, env):
    sample_jobs = repo_root / "jobs" / "sample_jobs.json"

    proc = subprocess.run(
        [
            sys.executable,
            str(repo_root / "run_batch.py"),
            str(sample_jobs)
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True
    )

    if proc.returncode != 0:
        return {
            "crashed": True,
            "mismatch": False
        }

    discrepancy = detect_discrepancy_from_logs(repo_root)

    if discrepancy is not None:
        return {
            "crashed": False,
            "mismatch": discrepancy != 0
        }

    report = read_report(repo_root)

    if report is None:
        return {
            "crashed": True,
            "mismatch": False
        }

    return {
        "crashed": False,
        "mismatch": False
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--scenario", required=True)

    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    env = build_env(repo_root)

    mismatch_count = 0
    crash_count = 0

    for _ in range(TOTAL_RUNS):
        result = run_once(repo_root, env)

        if result["crashed"]:
            crash_count += 1

        if result["mismatch"]:
            mismatch_count += 1

    output = {
        "scenario": args.scenario,
        "runs": TOTAL_RUNS,
        "crash_count": crash_count,
        "mismatch_count": mismatch_count,
        "mismatch_ratio": mismatch_count / TOTAL_RUNS,
        "success": crash_count == 0
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
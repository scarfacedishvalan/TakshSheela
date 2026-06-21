"""
validate_patch.py — Validate a materialized scenario workspace.

Usage:
    python tools/validate_patch.py --problem <problem_id> --scenario <scenario_id>

Reads workspace location from tools/config.json.

Validation stages:
    1. Syntax check  — all .py files compile without error
    2. Import check  — top-level package imports without error
    3. Smoke run     — run_batch.py completes against sample_jobs.json

Output: JSON to stdout.

Exit codes:
    0 — all stages passed (smoke run completing with non-zero discrepancy is still a pass
        — the fault is expected to manifest; a crash is a fail)
    1 — one or more stages failed
"""

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path


CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config():
    if not CONFIG_PATH.exists():
        print(f"ERROR: config not found: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def check_syntax(workspace):
    """Compile every .py file. Returns list of error strings."""
    errors = []
    for py_file in workspace.rglob("*.py"):
        try:
            source = py_file.read_text(encoding="utf-8")
            ast.parse(source, filename=str(py_file))
        except SyntaxError as e:
            errors.append(f"{py_file.relative_to(workspace)}: {e}")
    return errors


def check_imports(workspace):
    """
    Attempt to import the top-level package by running a minimal import script
    in a subprocess. Avoids polluting the current interpreter's module cache.
    """
    package_name = next(
        (d.name for d in workspace.iterdir() if d.is_dir() and (d / "__init__.py").exists()),
        None,
    )
    if package_name is None:
        return None, "no package with __init__.py found in workspace root"

    script = f"import {package_name}"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, None


def check_smoke_run(workspace):
    """
    Run run_batch.py against sample_jobs.json.

    A non-zero discrepancy in the report is expected for fault scenarios and is
    NOT treated as a smoke failure. Only a non-zero exit code (crash) fails this stage.
    """
    entry = workspace / "run_batch.py"
    sample_jobs = workspace / "jobs" / "sample_jobs.json"

    if not entry.exists():
        return False, "run_batch.py not found in workspace root"
    if not sample_jobs.exists():
        return False, "jobs/sample_jobs.json not found in workspace"

    result = subprocess.run(
        [sys.executable, str(entry), str(sample_jobs)],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return False, result.stderr.strip() or result.stdout.strip()

    return True, None


def main():
    parser = argparse.ArgumentParser(
        description="Validate a materialized scenario workspace.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--problem",  required=True, help="Problem ID, e.g. prob-001")
    parser.add_argument("--scenario", required=True, help="Scenario ID, e.g. scen-001")
    args = parser.parse_args()

    cfg = load_config()
    workspace = Path(cfg["workspace_root"]) / args.problem
    if not workspace.exists():
        print(json.dumps({"error": f"workspace not found: {workspace}"}))
        sys.exit(1)

    result = {
        "problem":  args.problem,
        "scenario": args.scenario,
        "workspace": str(workspace),
        "syntax_check":  {"passed": False, "errors": []},
        "import_check":  {"passed": False, "error": None},
        "smoke_run":     {"passed": False, "error": None},
        "overall": False,
    }

    # Stage 1 — syntax
    syntax_errors = check_syntax(workspace)
    result["syntax_check"]["passed"] = len(syntax_errors) == 0
    result["syntax_check"]["errors"] = syntax_errors

    # Stage 2 — imports (only if syntax passed)
    if result["syntax_check"]["passed"]:
        import_ok, import_err = check_imports(workspace)
        result["import_check"]["passed"] = import_ok is True
        result["import_check"]["error"]  = import_err
    else:
        result["import_check"]["error"] = "skipped — syntax check failed"

    # Stage 3 — smoke run (only if imports passed)
    if result["import_check"]["passed"]:
        smoke_ok, smoke_err = check_smoke_run(workspace)
        result["smoke_run"]["passed"] = smoke_ok
        result["smoke_run"]["error"]  = smoke_err
    else:
        result["smoke_run"]["error"] = "skipped — import check failed"

    result["overall"] = (
        result["syntax_check"]["passed"]
        and result["import_check"]["passed"]
        and result["smoke_run"]["passed"]
    )

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["overall"] else 1)


if __name__ == "__main__":
    main()

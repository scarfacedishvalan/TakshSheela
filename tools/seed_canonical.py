"""
seed_canonical.py — Initialise a problem workspace git repo from a canonical codebase.

Usage:
    python tools/seed_canonical.py --problem <problem_id> [options]

    Options:
        --source PATH    Path to canonical codebase directory.
                         Defaults to <takshsheela_root>/codes/<problem_id>/canonical
        --name NAME      System name for the commit message, e.g. nightproc.
                         Defaults to problem_id.
        --force          Delete and reinitialise if workspace already exists.

Creates:
    <workspace_root>/<problem_id>/  as a git repo with a single orphan branch
    named 'canonical', containing the canonical codebase files flat at repo root.

Precondition:
    tools/config.json must exist with 'workspace_root' and 'takshsheela_root' keys.
"""

import argparse
import json
import shutil
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


def git(args, cwd):
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Seed a problem workspace git repo from a canonical codebase."
    )
    parser.add_argument("--problem", required=True, help="Problem ID, e.g. prob-001")
    parser.add_argument("--source", default=None, help="Path to canonical codebase directory")
    parser.add_argument("--name", default=None, help="System name for commit message, e.g. nightproc")
    parser.add_argument("--force", action="store_true", help="Reinitialise if workspace already exists")
    args = parser.parse_args()

    cfg = load_config()
    workspace_root = Path(cfg["workspace_root"])
    takshsheela_root = Path(cfg["takshsheela_root"])

    workspace = workspace_root / args.problem

    source = (
        Path(args.source).resolve()
        if args.source
        else (takshsheela_root / "codes" / args.problem / "canonical").resolve()
    )

    if not source.exists():
        print(f"ERROR: canonical source not found: {source}", file=sys.stderr)
        sys.exit(1)
    if not source.is_dir():
        print(f"ERROR: source is not a directory: {source}", file=sys.stderr)
        sys.exit(1)

    # Handle existing workspace
    if workspace.exists():
        if args.force:
            shutil.rmtree(workspace)
            print(f"Removed existing workspace: {workspace}")
        else:
            print(f"ERROR: workspace already exists: {workspace}", file=sys.stderr)
            print("Use --force to reinitialise.", file=sys.stderr)
            sys.exit(1)

    workspace.mkdir(parents=True)

    # Initialise git repo and create orphan canonical branch
    git(["init"], cwd=workspace)
    git(["checkout", "--orphan", "canonical"], cwd=workspace)

    # Copy canonical codebase contents flat into workspace root
    for item in source.iterdir():
        dest = workspace / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    # Initial commit
    git(["add", "-A"], cwd=workspace)
    system_name = args.name or args.problem
    git(["commit", "-m", f"Initial canonical state — {system_name}"], cwd=workspace)

    print(f"\nSeeded successfully.")
    print(f"  Workspace : {workspace}")
    print(f"  Branch    : canonical")
    print(f"  Source    : {source}")
    print(f"  System    : {system_name}")


if __name__ == "__main__":
    main()

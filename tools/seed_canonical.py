"""
seed_canonical.py — Seed a canonical branch in the shared workspace git repo.

Usage:
    python tools/seed_canonical.py --problem <problem_id> [options]

    Options:
        --source PATH    Path to canonical codebase directory.
                         Defaults to <takshsheela_root>/codes/<problem_id>/canonical
        --name NAME      System name for the commit message, e.g. nightproc.
                         Defaults to problem_id.
        --force          Delete and recreate the canonical branch if it already exists.

Creates:
    Branch <problem_id>--canonical in the shared workspace git repo at workspace_root.
    The branch is an orphan with no shared history with other problem branches.
    Canonical codebase files are placed flat at repo root (no subdirectory).

Branch naming convention:
    <problem_id>--canonical   e.g. prob-001--canonical
    <problem_id>--<scenario>  e.g. prob-001--scen-001  (created by apply_patch.py)

Precondition:
    tools/config.json must exist with 'workspace_root' and 'takshsheela_root' keys.
    workspace_root must be an existing git repo (git init once manually if needed).
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


def git_check(args, cwd):
    """Run a git command without exiting on failure. Returns result."""
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Seed a canonical branch in the shared workspace git repo."
    )
    parser.add_argument("--problem", required=True, help="Problem ID, e.g. prob-001")
    parser.add_argument("--source", default=None, help="Path to canonical codebase directory")
    parser.add_argument("--name", default=None, help="System name for commit message, e.g. nightproc")
    parser.add_argument("--force", action="store_true", help="Delete and recreate canonical branch if it exists")
    args = parser.parse_args()

    cfg = load_config()
    workspace = Path(cfg["workspace_root"])
    takshsheela_root = Path(cfg["takshsheela_root"])

    canonical_branch = f"{args.problem}--canonical"

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

    # Workspace must already be a git repo
    if not workspace.exists():
        print(f"ERROR: workspace not found: {workspace}", file=sys.stderr)
        print("Create the workspace repo manually: git init <path>", file=sys.stderr)
        sys.exit(1)
    if not (workspace / ".git").exists():
        print(f"ERROR: workspace is not a git repo: {workspace}", file=sys.stderr)
        print("Initialise it manually: git -C <path> init", file=sys.stderr)
        sys.exit(1)

    # Handle existing canonical branch
    existing = git_check(["branch", "--list", canonical_branch], cwd=workspace)
    if canonical_branch in existing.stdout:
        if args.force:
            # Switch away from the branch before deleting it
            git_check(["checkout", "--orphan", "_temp_detach"], cwd=workspace)
            git(["branch", "-D", canonical_branch], cwd=workspace)
            print(f"Deleted existing branch: {canonical_branch}")
        else:
            print(f"ERROR: branch '{canonical_branch}' already exists.", file=sys.stderr)
            print("Use --force to recreate.", file=sys.stderr)
            sys.exit(1)

    # Create orphan branch — no shared history with other problems
    git(["checkout", "--orphan", canonical_branch], cwd=workspace)

    # Clear any files inherited from the previous working tree
    git_check(["rm", "-rf", "."], cwd=workspace)

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
    print(f"  Branch    : {canonical_branch}")
    print(f"  Source    : {source}")
    print(f"  System    : {system_name}")


if __name__ == "__main__":
    main()

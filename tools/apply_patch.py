"""
apply_patch.py — Apply a scenario fault patch to the shared workspace git repo.

Usage:
    python tools/apply_patch.py \
        --problem  <problem_id> \
        --scenario <scenario_id> \
        --patch    <path_to_patch.diff> \
        --message  "<realistic commit message>" \
        [--force]

Branch naming convention:
    <problem_id>--canonical   source branch (must exist, created by seed_canonical.py)
    <problem_id>--<scenario>  new scenario branch created by this tool

    e.g. prob-001--canonical, prob-001--scen-001

Precondition:
    workspace_root (from tools/config.json) must be a git repo with branch
    <problem_id>--canonical already created by seed_canonical.py.

Checks performed before any git operation:
    1. Patch file exists and is non-empty
    2. Parseable as unified diff (has diff --git, ---, +++, @@ headers)
    3. All paths are repo-relative (no absolute paths, no codes/... prefix)
    4. File and hunk counts match patch_meta.json
    5. Every targeted file exists in the canonical working tree

Hard gate:
    6. git apply --check  — authoritative context-line verification
       Any failure exits 1 immediately. No retry, no LLM involvement.

On success:
    Creates branch <problem_id>--<scenario_id> off <problem_id>--canonical.
    Applies patch, removes patch.diff, commits with --message.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


CONFIG_PATH = Path(__file__).parent / "config.json"


# ---------------------------------------------------------------------------
# Config and git helpers
# ---------------------------------------------------------------------------

def load_config():
    if not CONFIG_PATH.exists():
        print(f"ERROR: config not found: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def git(args, cwd, check=True):
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    return result


def hard_stop(message):
    print(f"\nHARD STOP: {message}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

def check_1_exists_nonempty(patch_path):
    """Patch file must exist and be non-empty."""
    if not patch_path.exists():
        hard_stop(f"patch file not found: {patch_path}")
    if patch_path.stat().st_size == 0:
        hard_stop(f"patch file is empty: {patch_path}")
    return patch_path.read_text(encoding="utf-8")


def check_2_valid_diff_structure(patch_text):
    """Must contain at least one valid unified diff block."""
    lines = patch_text.splitlines()
    has_diff_header = any(l.startswith("diff --git ") for l in lines)
    has_hunk        = any(l.startswith("@@ ")         for l in lines)
    has_minus       = any(l.startswith("--- ")        for l in lines)
    has_plus        = any(l.startswith("+++ ")        for l in lines)

    if not has_diff_header:
        hard_stop(
            "patch contains no 'diff --git' header.\n"
            "The patch_injection agent may have returned prose or JSON instead of a diff."
        )
    if not (has_hunk and has_minus and has_plus):
        hard_stop(
            "patch is missing required diff headers (---, +++, @@).\n"
            "Patch appears to be malformed or truncated."
        )


def check_3_repo_relative_paths(patch_text):
    """All --- and +++ paths must be repo-relative with no forbidden prefixes."""
    FORBIDDEN = [
        (r"^[ab]/[A-Za-z]:[/\\]", "absolute Windows path"),
        (r"^[ab]//",               "absolute Unix path"),
        (r"^[ab]/codes/",          "full repo path — must be canonical-relative (e.g. a/nightproc/store.py)"),
        (r"_workspace",            "workspace path in diff — forbidden"),
        (r"_scratch",              "scratch path in diff — forbidden"),
        (r"\\",                    "backslash in path — git diff uses forward slashes only"),
    ]

    for line in patch_text.splitlines():
        if not (line.startswith("--- ") or line.startswith("+++ ")):
            continue
        path_part = line[4:].split("\t")[0].strip()
        if path_part in ("/dev/null", "dev/null"):
            continue
        for pattern, reason in FORBIDDEN:
            if re.search(pattern, path_part):
                hard_stop(
                    f"invalid path in patch: {path_part!r}\n"
                    f"  reason : {reason}\n"
                    f"  correct: a/nightproc/store.py  (repo-relative, forward slashes)"
                )


def check_4_hunk_count(patch_text, patch_path):
    """Actual file and hunk counts must match patch_meta.json."""
    meta_path = patch_path.parent / "patch_meta.json"
    if not meta_path.exists():
        hard_stop(
            f"patch_meta.json not found: {meta_path}\n"
            "The orchestrator must produce patch_meta.json alongside patch.diff."
        )

    with open(meta_path) as f:
        try:
            meta = json.load(f)
        except json.JSONDecodeError as e:
            hard_stop(f"patch_meta.json is not valid JSON: {e}")

    for field in ("expected_files_changed", "expected_hunks"):
        if field not in meta:
            hard_stop(f"patch_meta.json missing required field: {field!r}")

    lines = patch_text.splitlines()
    actual_files = sum(1 for l in lines if l.startswith("diff --git "))
    actual_hunks = sum(1 for l in lines if l.startswith("@@ "))

    if actual_files != meta["expected_files_changed"]:
        hard_stop(
            f"patch changes {actual_files} file(s); patch_meta.json expects {meta['expected_files_changed']}.\n"
            "This may be a multi-fault patch or an incomplete patch — regenerate."
        )
    if actual_hunks != meta["expected_hunks"]:
        hard_stop(
            f"patch has {actual_hunks} hunk(s); patch_meta.json expects {meta['expected_hunks']}.\n"
            "Patch structure does not match declared intent — regenerate."
        )

    return meta


def check_5_target_files_exist(patch_text, workspace):
    """Every file targeted by --- must exist in the canonical working tree."""
    missing = []
    for line in patch_text.splitlines():
        if not line.startswith("--- "):
            continue
        path_part = line[4:].split("\t")[0].strip()
        if path_part in ("/dev/null", "dev/null"):
            continue
        rel = path_part[2:] if path_part.startswith("a/") else path_part
        if not (workspace / rel).exists():
            missing.append(rel)

    if missing:
        hard_stop(
            "patch targets file(s) that do not exist in canonical:\n"
            + "\n".join(f"  {m}" for m in missing)
            + "\nCheck the injection site in scenario_spec.md and regenerate the patch."
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Apply a scenario fault patch to the shared workspace git repo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--problem",  required=True, help="Problem ID, e.g. prob-001")
    parser.add_argument("--scenario", required=True, help="Scenario ID, e.g. scen-001")
    parser.add_argument("--patch",    required=True, help="Path to patch.diff (absolute or relative to takshsheela_root)")
    parser.add_argument("--message",  required=True, help="Realistic commit message for the mutation commit")
    parser.add_argument("--force",    action="store_true", help="Delete and recreate scenario branch if it exists")
    args = parser.parse_args()

    cfg = load_config()
    workspace        = Path(cfg["workspace_root"])
    takshsheela_root = Path(cfg["takshsheela_root"])

    canonical_branch = f"{args.problem}--canonical"
    scenario_branch  = f"{args.problem}--{args.scenario}"

    # Resolve patch path
    patch_path = Path(args.patch)
    if not patch_path.is_absolute():
        patch_path = takshsheela_root / patch_path
    patch_path = patch_path.resolve()

    # --------------- Workspace validation ---------------

    if not workspace.exists():
        hard_stop(f"workspace not found: {workspace}")
    if not (workspace / ".git").exists():
        hard_stop(f"workspace is not a git repo: {workspace}")

    result = git(["branch", "--list", canonical_branch], cwd=workspace, check=False)
    if canonical_branch not in result.stdout:
        hard_stop(
            f"branch '{canonical_branch}' not found in workspace.\n"
            f"Run: python tools/seed_canonical.py --problem {args.problem}"
        )

    # --------------- Pre-flight checks 1–4 ---------------

    print("[ 1/6 ] Checking patch file exists and is non-empty...")
    patch_text = check_1_exists_nonempty(patch_path)
    print("        OK")

    print("[ 2/6 ] Checking unified diff structure...")
    check_2_valid_diff_structure(patch_text)
    print("        OK")

    print("[ 3/6 ] Checking path conventions...")
    check_3_repo_relative_paths(patch_text)
    print("        OK")

    print("[ 4/6 ] Checking hunk count against patch_meta.json...")
    meta = check_4_hunk_count(patch_text, patch_path)
    print(f"        OK  ({meta['expected_files_changed']} file(s), {meta['expected_hunks']} hunk(s))")

    # --------------- Checkout canonical for checks 5–6 ---------------

    print(f"\nChecking out {canonical_branch}...")
    git(["checkout", canonical_branch], cwd=workspace)

    print("[ 5/6 ] Checking target files exist in canonical...")
    check_5_target_files_exist(patch_text, workspace)
    print("        OK")

    # --------------- Scenario branch ---------------

    existing = git(["branch", "--list", scenario_branch], cwd=workspace, check=False)
    if scenario_branch in existing.stdout:
        if args.force:
            git(["branch", "-D", scenario_branch], cwd=workspace)
            print(f"\nDeleted existing branch: {scenario_branch}")
        else:
            hard_stop(
                f"branch '{scenario_branch}' already exists.\n"
                "Use --force to overwrite."
            )

    git(["checkout", "-b", scenario_branch], cwd=workspace)
    print(f"Created branch: {scenario_branch}")

    # Copy patch into workspace root (temporary — deleted before commit)
    patch_dest = workspace / "patch.diff"
    shutil.copy2(patch_path, patch_dest)

    # --------------- Check 6: git apply --check (hard gate) ---------------

    print("[ 6/6 ] Running git apply --check (authoritative gate)...")
    result = git(["apply", "--check", "patch.diff"], cwd=workspace, check=False)

    if result.returncode != 0:
        patch_dest.unlink(missing_ok=True)
        git(["checkout", canonical_branch], cwd=workspace)
        git(["branch", "-D", scenario_branch], cwd=workspace)
        print(file=sys.stderr)
        print(result.stderr.strip(), file=sys.stderr)
        hard_stop(
            "git apply --check failed — patch does not apply cleanly to canonical.\n"
            "The patch must be regenerated. Do not attempt LLM-based repair."
        )

    print("        OK")

    # --------------- Apply, clean up, commit ---------------

    print("\nApplying patch...")
    git(["apply", "patch.diff"], cwd=workspace)

    patch_dest.unlink()

    git(["add", "-A"], cwd=workspace)
    git(["commit", "-m", args.message], cwd=workspace)

    log = git(["log", "--oneline", "-1"], cwd=workspace, check=False)

    print(f"\nDone.")
    print(f"  Workspace : {workspace}")
    print(f"  Branch    : {scenario_branch}")
    print(f"  Commit    : {log.stdout.strip()}")


if __name__ == "__main__":
    main()

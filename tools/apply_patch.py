"""
apply_patch.py — Apply a mutation patch to create a workspace codebase.

Usage:
    python tools/apply_patch.py <patch_file> [--repo <repo_root>] [--force]

The patch file must use repository-relative paths produced by the Patch
Injection Agent (a/codes/<problem_id>/canonical/... → b/codes/_workspace/...).

Steps performed:
  1. Parse the patch to determine the canonical source and workspace destination.
  2. Copy the canonical directory to the workspace destination.
  3. Apply the diff hunks to the workspace files.
"""

import argparse
import shutil
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Unified-diff parser
# ---------------------------------------------------------------------------

def _parse_range(range_str):
    """Parse '-12,5' or '+12,5' into (start, count). Count defaults to 1."""
    s = range_str.lstrip("-+")
    if "," in s:
        start, count = s.split(",", 1)
        return int(start), int(count)
    return int(s), 1


def parse_unified_diff(patch_text):
    """
    Parse a unified diff (git format) into a list of file-patch dicts:

        {
            'a': 'codes/prob-001/canonical/nightproc/store.py',  # old path
            'b': 'codes/_workspace/prob-001-scen-001/nightproc/store.py',  # new path
            'hunks': [
                {
                    'old_start': 31,   # 1-indexed line in old file
                    'lines': [' ctx', '-removed', '+added', ...]
                },
                ...
            ]
        }
    """
    file_patches = []
    current = None
    hunk = None

    for raw_line in patch_text.splitlines():
        if raw_line.startswith("diff --git "):
            if current is not None:
                if hunk is not None:
                    current["hunks"].append(hunk)
                    hunk = None
                file_patches.append(current)
            current = {"a": None, "b": None, "hunks": []}

        elif raw_line.startswith("--- ") and current is not None:
            path = raw_line[4:].split("\t")[0].strip()
            current["a"] = path[2:] if path.startswith("a/") else (None if path == "/dev/null" else path)

        elif raw_line.startswith("+++ ") and current is not None:
            path = raw_line[4:].split("\t")[0].strip()
            current["b"] = path[2:] if path.startswith("b/") else (None if path == "/dev/null" else path)

        elif raw_line.startswith("@@ ") and current is not None:
            if hunk is not None:
                current["hunks"].append(hunk)
            # @@ -old_start[,old_count] +new_start[,new_count] @@
            at_parts = raw_line.split("@@")
            range_part = at_parts[1].strip()
            old_str, new_str = range_part.split(" ", 1)
            old_start, _ = _parse_range(old_str)
            hunk = {"old_start": old_start, "lines": []}

        elif hunk is not None:
            # Diff body line: space (context), - (removed), + (added)
            if raw_line and raw_line[0] in (" ", "-", "+"):
                hunk["lines"].append(raw_line)
            # Lines like 'index ...', 'new file mode', etc. are silently skipped.

    # Flush last patch
    if current is not None:
        if hunk is not None:
            current["hunks"].append(hunk)
        file_patches.append(current)

    return file_patches


# ---------------------------------------------------------------------------
# Hunk application
# ---------------------------------------------------------------------------

def apply_file_patch(file_path: Path, file_patch: dict) -> None:
    """
    Apply all hunks of *file_patch* to *file_path* in-place.

    All hunks are applied in a single pass over the original line list so that
    old_start values (which reference the original file) remain valid
    throughout.
    """
    if file_path.exists():
        # Normalise to LF so that line counts are predictable.
        lines = file_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    result = []
    old_pos = 0  # 0-indexed cursor into the original lines list

    for hunk in file_patch["hunks"]:
        hunk_old_start = hunk["old_start"] - 1  # convert to 0-indexed

        # Copy original lines that precede this hunk unchanged.
        result.extend(lines[old_pos:hunk_old_start])
        old_pos = hunk_old_start

        for hline in hunk["lines"]:
            if not hline:
                continue
            marker = hline[0]
            payload = hline[1:]
            if marker == " ":
                # Context line — take from original to preserve exact content.
                result.append(lines[old_pos] if old_pos < len(lines) else payload)
                old_pos += 1
            elif marker == "-":
                # Removed line — advance original cursor, emit nothing.
                old_pos += 1
            elif marker == "+":
                # Added line — emit payload, do not advance original cursor.
                result.append(payload)

    # Append any original lines that follow the last hunk.
    result.extend(lines[old_pos:])

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("\n".join(result) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _extract_segment(path_str: str, marker: str):
    """
    Return the Path prefix up to and including the component after *marker*.

    e.g. _extract_segment('codes/_workspace/prob-001-scen-001/foo.py', '_workspace')
         → PurePath('codes/_workspace/prob-001-scen-001')
    """
    parts = Path(path_str).parts
    for i, part in enumerate(parts):
        if part == marker and i + 1 < len(parts):
            return Path(*parts[: i + 2])
    return None


def _extract_canonical_root(path_str: str):
    """
    Return the Path prefix up to and including 'canonical'.

    e.g. 'codes/prob-001/canonical/nightproc/store.py'
         → PurePath('codes/prob-001/canonical')
    """
    parts = Path(path_str).parts
    for i, part in enumerate(parts):
        if part == "canonical":
            return Path(*parts[: i + 1])
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Apply a mutation patch to create a workspace codebase.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("patch", help="Path to the .patch file")
    parser.add_argument(
        "--repo",
        default=None,
        help=(
            "Repository root directory. "
            "Defaults to the parent of the directory containing this script."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Remove and recreate the workspace directory if it already exists.",
    )
    args = parser.parse_args()

    patch_path = Path(args.patch).resolve()
    if not patch_path.exists():
        print(f"ERROR: patch file not found: {patch_path}", file=sys.stderr)
        sys.exit(1)

    # Determine repository root.
    repo_root = (
        Path(args.repo).resolve()
        if args.repo
        else Path(__file__).resolve().parent.parent
    )

    patch_text = patch_path.read_text(encoding="utf-8")
    file_patches = parse_unified_diff(patch_text)

    if not file_patches:
        print("ERROR: no file patches found in patch file.", file=sys.stderr)
        sys.exit(1)

    # Derive workspace destination from the first b/ path.
    b_paths = [fp["b"] for fp in file_patches if fp.get("b")]
    a_paths = [fp["a"] for fp in file_patches if fp.get("a")]

    if not b_paths:
        print("ERROR: could not determine workspace destination from patch headers.", file=sys.stderr)
        sys.exit(1)
    if not a_paths:
        print("ERROR: could not determine canonical source from patch headers.", file=sys.stderr)
        sys.exit(1)

    workspace_rel = _extract_segment(b_paths[0], "_workspace")
    canonical_rel = _extract_canonical_root(a_paths[0])

    if workspace_rel is None:
        print(
            f"ERROR: expected '_workspace/<name>' in b/ path but got: {b_paths[0]}",
            file=sys.stderr,
        )
        sys.exit(1)
    if canonical_rel is None:
        print(
            f"ERROR: expected 'canonical' component in a/ path but got: {a_paths[0]}",
            file=sys.stderr,
        )
        sys.exit(1)

    workspace_dir = repo_root / workspace_rel
    canonical_dir = repo_root / canonical_rel

    if not canonical_dir.exists():
        print(f"ERROR: canonical directory not found: {canonical_dir}", file=sys.stderr)
        sys.exit(1)

    # Step 1 — copy canonical → workspace.
    if workspace_dir.exists():
        if args.force:
            shutil.rmtree(workspace_dir)
            print(f"Removed existing workspace: {workspace_rel}")
        else:
            print(f"ERROR: workspace already exists: {workspace_dir}", file=sys.stderr)
            print("Use --force to overwrite.", file=sys.stderr)
            sys.exit(1)

    shutil.copytree(canonical_dir, workspace_dir)
    print(f"Copied  {canonical_rel}  →  {workspace_rel}")

    # Step 2 — apply each file patch.
    errors = []
    for fp in file_patches:
        b_path = fp.get("b")
        if not b_path:
            continue  # deleted file — skip
        target = repo_root / b_path
        try:
            apply_file_patch(target, fp)
            print(f"Patched {b_path}")
        except Exception as exc:  # noqa: BLE001
            msg = f"FAILED to patch {b_path}: {exc}"
            print(msg, file=sys.stderr)
            errors.append(msg)

    if errors:
        print(f"\n{len(errors)} file(s) failed to patch.", file=sys.stderr)
        sys.exit(1)

    print(f"\nWorkspace ready: {workspace_dir}")


if __name__ == "__main__":
    main()

# TakshSheela Patch Contract (v2)

This document defines how scenario mutation patches are produced, validated, and applied.

Patches are the authoritative mutation artifacts. They transform a canonical codebase
into a fault-injected scenario codebase deterministically.

---

# Core Constraint

**No agent writes diff syntax directly.**

The diff is always produced by `git diff` against an actual edited file in a scratch
git repo. An LLM edits source code; `git diff` captures what changed. This eliminates
hallucinated diffs, path errors, and context-line drift.

---

# How a Patch is Produced

```
1. Orchestrator sets up scratch git repo
   codes/_scratch/<problem_id>-<scenario_id>/
   containing only the target file under a <problem_id>/ subdirectory,
   mirroring the workspace branch layout

2. Orchestrator commits the unmodified file: git commit -m "base"

3. Orchestrator hands off to Patch Injection Agent:
   — provides absolute scratch file path
   — provides exact mutation instruction
   — agent edits the file only, returns RETURN block

4. Orchestrator runs:
   git -C codes/_scratch/<problem_id>-<scenario_id> diff
   and captures stdout verbatim

5. Orchestrator validates the captured diff (see Validation Rules below)

6. Orchestrator saves diff output as:
   codes/<problem_id>/scenarios/<scenario_id>/patch.diff

7. Orchestrator generates patch_meta.json alongside patch.diff

8. Orchestrator deletes scratch repo
```

---

# Artifact Layout

```
codes/<problem_id>/scenarios/<scenario_id>/
    patch.diff          ← raw git diff output, never hand-written
    patch_meta.json     ← mutation metadata
```

---

# Patch Meta Schema

```json
{
  "scenario_id": "<scenario_id>",
  "problem_id": "<problem_id>",
  "canonical_version": "<version>",
  "expected_files_changed": 1,
  "expected_hunks": 1,
  "mutation_type": "<mutation_type>",
  "fault_family": "<fault_family>"
}
```

Required fields: all of the above.

`expected_files_changed` and `expected_hunks` are derived by counting `diff --git`
and `@@` lines in the captured diff — they are never estimated or guessed.

---

# Patch Path Rules

The scratch repo mirrors the workspace branch layout. Files go under a `<problem_id>/`
subdirectory. A file at `nightproc/store.py` in the canonical codebase must be placed at
`<problem_id>/nightproc/store.py` in the scratch repo, producing:

```diff
diff --git a/prob-001/nightproc/store.py b/prob-001/nightproc/store.py
```

Valid:
```
a/prob-001/nightproc/store.py
b/prob-001/nightproc/store.py
```

Invalid (scratch was set up without problem prefix):
```
a/nightproc/store.py
a/codes/prob-001/canonical/nightproc/store.py
a/codes/_scratch/prob-001-scen-001/nightproc/store.py
```

If invalid paths appear, the scratch repo was not set up with the `<problem_id>/`
subdirectory. Rebuild the scratch repo — do not edit the diff.

---

# Patch Scope Rules

One patch represents exactly one primary fault mutation.

- **One root cause** — a single change that introduces a single fault
- **Minimum files** — touch the fewest files possible (almost always 1)
- **Minimum lines** — change only lines required to introduce the fault
- **No noise** — no formatting changes, comment rewrites, import reordering, or cleanup

A patch that changes 2+ files or has 3+ hunks requires explicit justification.
Default hard limit: 1 file, 1–2 hunks.

---

# Validation Rules

`apply_patch.py` enforces six checks before any file is written to the workspace.
Checks run in order. Any failure exits immediately — no retry, no LLM repair.

| Check | What is verified |
|---|---|
| 1. Exists and non-empty | `patch.diff` file is present and has content |
| 2. Valid diff structure | Contains `diff --git`, `---`, `+++`, `@@` headers |
| 3. Repo-relative paths | No absolute paths, no `codes/` prefix, forward slashes only |
| 4. Hunk count vs meta | Actual file and hunk counts match `patch_meta.json` |
| 5. Target files exist | Every `---` path exists in the canonical working tree |
| 6. `git apply --check` | Authoritative gate — context lines verified by git |

Check 6 is the hard barrier. It is equivalent to `git apply` dry-run. If it passes,
the patch is guaranteed to apply cleanly. If it fails, git's error output names the
exact file, line number, and mismatched content. This is the complete diagnostic — no
further analysis is needed.

---

# How a Patch is Applied

`apply_patch.py` applies the patch to the workspace:

```
1. Run checks 1–5 (Python pre-flight)
2. git checkout canonical  (in workspace repo)
3. git checkout -b <scenario_id>
4. Copy patch.diff into workspace root (temporary)
5. git apply --check patch.diff  ← HARD STOP on failure
6. git apply patch.diff
7. rm patch.diff  ← no evidence of injection
8. git add -A && git commit -m "<realistic message>"
```

The workspace is an independent git repo at `<workspace_root>/<problem_id>/`
(outside TakshSheela). The `canonical` branch is seeded once by `seed_canonical.py`.
Each scenario is a branch with two commits: canonical baseline + mutation commit.

The mutation commit message is authored by the orchestrator (derived from
`scenario_spec.md`) and must read as a plausible engineering decision, not as a
test or injection artifact.

---

# Workspace Repo Layout

```
<workspace_root>/              ← single shared git repo for all problems
  branch: prob-001--canonical  ← prob-001 codebase under prob-001/ subdirectory
  branch: prob-001--scen-001   ← canonical + mutation commit
  branch: prob-001--scen-002   ← canonical + mutation commit
  branch: prob-002--canonical  ← prob-002 codebase under prob-002/ subdirectory
  ...
```

Each problem's files live under a `<problem_id>/` subdirectory within its branches.
Patch paths carry the problem prefix (e.g. `a/prob-001/nightproc/store.py`), so
`git apply` resolves them correctly without `--directory` flags.

---

# Anti-Patterns

Forbidden:

* agents writing `diff --git`, `---`, `+++`, or `@@` lines directly
* editing patch.diff after it is captured from `git diff`
* patches generated from inferred or remembered code (not from actual files)
* multi-fault patches
* patches containing formatting or comment changes unrelated to the fault
* workspace paths or absolute paths in diff headers
* LLM-based repair of a failed `git apply --check`

---

# Design Philosophy

The LLM's role is to understand the mutation and edit source code correctly.
`git diff` is the only mechanism that produces the patch artifact.
`git apply --check` is the only mechanism that validates patch applicability.
Deterministic tools own execution. Agents own reasoning and code editing.

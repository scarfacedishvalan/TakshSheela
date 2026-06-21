# TakshSheela Patch Contract (v1)

This document defines the required format, constraints, and validation rules for all scenario mutation patches.

Patches are used to deterministically transform a canonical codebase into a fault-injected scenario codebase.

Patches are considered source-of-truth mutation artifacts.

---

# Purpose

A patch must satisfy all of the following:

1. Human inspectable
2. Deterministically applicable
3. Minimal
4. Semantically targeted
5. Compatible with automated validation

Patches must represent code mutations only.

They must not contain scenario metadata.

Scenario metadata belongs elsewhere.

---

# Artifact Layout

Each scenario stores:

```text
codes/<problem_id>/scenarios/<scenario_id>/
    patch.diff
    patch_meta.json
```

---

# Patch Meta Schema

`patch_meta.json`

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

Required fields:

* scenario_id
* problem_id
* canonical_version
* expected_files_changed
* expected_hunks
* mutation_type
* fault_family

---

# Allowed Patch Format

Patch must use standard unified diff / git diff format.

Example:

```diff
diff --git a/nightproc/store.py b/nightproc/store.py
index 15203e7..b2fb869 100644
--- a/nightproc/store.py
+++ b/nightproc/store.py
@@ -31,13 +31,12 @@ def update(accumulator, category, value, failed=False):
-    with _lock:
-        if failed:
-            key = f"{category}_failed"
-            accumulator[key] = accumulator.get(key, 0) + 1
+    if failed:
+        key = f"{category}_failed"
+        accumulator[key] = accumulator.get(key, 0) + 1
```

---

# Patch Path Rules

## Rule 1 — Repo Relative Paths Only

Paths MUST be relative to canonical repo root.

Valid:

```diff
a/nightproc/store.py
b/nightproc/store.py
```

Invalid:

```diff
a/codes/prob-001/canonical/nightproc/store.py
```

Invalid:

```diff
b/codes/_workspace/prob-001-scen-001/nightproc/store.py
```

Workspace paths are forbidden.

Absolute paths are forbidden.

---

# Patch Scope Rules

## Rule 2 — Single Root Cause

One patch must represent exactly one primary fault mutation.

Allowed:

* lock removal
* retry logic modification
* stale cache insertion

Not allowed:

Single patch containing multiple unrelated fault families.

---

## Rule 3 — Minimize Blast Radius

Touch the smallest number of files possible.

Recommended:
1–3 files

Hard limit:
5 files unless explicitly approved

---

## Rule 4 — Minimal Changes

Change only lines necessary to introduce the fault.

Avoid:

* formatting changes
* comment rewrites
* import reordering
* unrelated cleanup

Patch noise is forbidden.

---

# Context Rules

## Rule 5 — Adequate Context

Patch hunks must include enough context lines to apply reliably.

Use standard git diff context.

Avoid manually constructed hunks with insufficient context.

---

# Agent Generation Rules

Before generating a patch, the agent MUST:

1. Read actual target files
2. Confirm target symbol exists
3. Confirm mutation location exists
4. Explain intended mutation
5. Generate patch only after verification

The agent must never generate a patch from inferred code.

It must operate on actual repository files.

---

# Validation Rules

Every patch must pass all validation stages.

---

## Stage 1 — Applicability Check

Must pass:

```bash
git apply --check patch.diff
```

Failure invalidates patch.

---

## Stage 2 — Structural Validation

Run:

* syntax checks
* import checks
* smoke tests

Patch must preserve runnable code.

---

## Stage 3 — Behavioral Validation

Scenario runner must verify intended fault manifests.

Example checks:

* race manifests
* metric drift occurs
* silent corruption detectable

A patch that applies but does not manifest intended fault is invalid.

---

# Agent Output Contract

When asked to generate a patch, the agent must return:

## Mutation Summary

* target files
* target symbols
* mutation rationale
* expected symptom

## patch_meta.json

## patch.diff

No additional prose.

---

# Anti-Patterns

Forbidden:

* patches against workspace paths
* patches generated from hallucinated code
* multi-fault patches
* patches with unrelated formatting changes
* patches without validation

---

# Design Philosophy

Patches are mutation artifacts, not code snapshots.

The canonical codebase remains the source of truth.

Scenario repos are ephemeral and disposable.

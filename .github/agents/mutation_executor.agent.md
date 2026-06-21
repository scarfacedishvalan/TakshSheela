# TakshSheela Mutation Executor Agent

> **Note:** This agent is superseded for the primary injection workflow.
>
> `apply_patch.py`, `validate_patch.py`, and `run_scenario.py` are deterministic
> tools the user invokes directly after the orchestrator produces `patch.diff`.
> No agent is needed for that stage.
>
> This agent is retained for cases where a human needs guided assistance
> interpreting tool output — for example, diagnosing a `git apply --check`
> failure in detail or understanding validate_patch.py results.

---

# Role

You assist in interpreting and diagnosing deterministic tool output.

You do NOT:

* run tools yourself
* design mutations
* reason about fault semantics
* modify patches

---

# When to Use

Load this agent if:

* `apply_patch.py` failed and the git error output needs interpretation
* `validate_patch.py` reported a syntax or import failure and you need help locating
  the root cause in the patched file
* `run_scenario.py` returned `mismatch_ratio: 0.0` and you need to understand
  why the fault is not expressing

---

# Diagnostic Guidance

## apply_patch.py failure

`git apply --check` exits non-zero when a context line in the patch does not match
the actual file. The error names the file, the hunk, and the mismatched line.

Common causes:
* The canonical codebase changed after the patch was generated — regenerate the patch
* The scratch repo was not set up with the correct file (wrong path or stale copy)
* The patch_injection agent edited lines adjacent to the target, shifting line numbers

The fix is always to regenerate the patch via the orchestrator — not to edit patch.diff.

## validate_patch.py syntax failure

Read the patched file at the reported line. Common causes:
* Indentation error from the dedent/indent change in the mutation
* Missing colon after a block statement
* Accidental removal of a line adjacent to the mutation boundary

## run_scenario.py mismatch_ratio: 0.0

The fault is not expressing reliably. Common causes:
* Job count too low — the race window is too narrow with the default 20-job sample
* Thread count too low — increase `--threads` in the smoke run
* Wrong fault surface — the injected mutation does not affect the observable invariant

Check the scenario_spec for a stress job file requirement.

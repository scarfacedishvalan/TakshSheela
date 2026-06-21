---
scenario_id: scen-002
spec_id: prob-001
fault_surface_ref: FS-02
fault_family: temporal
fault_subtype: race_condition
difficulty: 3
observability_level: structured
status: pending
---

# Scenario: scen-002 — Premature Reporter

## Fault

The reporter reads the accumulator before all worker threads have finished. A thread
join or barrier is missing or incorrectly placed — moved outside the correct scope
after a refactor, or conditioned on the wrong signal.

## Injection

Remove or misplace the synchronization call (e.g. `thread.join()` or queue sentinel
drain) that separates worker completion from reporter execution.

## Diagnostic Signal

Report total is consistently low and stable (not drifting run to run, unlike scen-001).
Some job categories may be missing entirely from the output. Log timestamps show worker
completion events occurring after the report was written.

## Primary Capability Tested

debugging_discipline — candidate must read log timestamps carefully to reconstruct
event order before forming a hypothesis. The symptom (low report total) looks similar
to scen-001 but the mechanism and fix are different.

## Difficulty Calibration

- Weak: confuses with a data issue or blames input
- Average: notices the missing categories, finds the join in the code, misidentifies its scope
- Strong: correlates log timestamps to prove reporter ran before workers finished
- Senior: identifies the refactor risk and proposes a safer synchronization pattern

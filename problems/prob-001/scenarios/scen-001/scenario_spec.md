---
scenario_id: scen-001
spec_id: prob-001
fault_surface_ref: FS-01
fault_family: coordination
fault_subtype: shared_mutable_state
difficulty: 4
observability_level: structured
status: pending
---

# Scenario: scen-001 — Lost Update Race

## Fault

Workers perform a non-atomic read-modify-write on the shared accumulator dict under
concurrent access. Updates from one thread silently overwrite updates from another.
The program completes without error. The report total is wrong.

## Injection

Remove or bypass the critical section guard on the accumulator update path in the worker.
The injected codebase should use the naive read-modify-write pattern rather than an
atomic update.

## Diagnostic Signal

Log-reported `jobs_processed` count (from a thread-safe atomic counter) is consistently
higher than the report's `total` field. The discrepancy is non-deterministic but grows
with thread count and queue depth.

## Primary Capability Tested

concurrency_reasoning — candidate must identify that the read-modify-write sequence
is not atomic even though individual dict operations are thread-safe in Python.

## Difficulty Calibration

- Weak: runs the code, sees no error, declares it working
- Average: notices wrong output, identifies the race, applies lock only around write (partial fix)
- Strong: identifies correct critical section boundary, wraps read-modify-write atomically
- Senior: questions whether shared mutable accumulator is the right design, proposes reduce-after pattern

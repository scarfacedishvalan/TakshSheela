---
scenario_id: scen-001
spec_id: prob-001
fault_surface_ref: FS-01
fault_family: coordination
fault_subtype: lost_update
difficulty: 3
observability_level: structured
status: injected
---

# Scenario: scen-001 — Silent Accumulator Race

## Fault

The lock guarding the shared accumulator's read-modify-write sequence is removed.
Multiple worker threads read a stale value, compute independently, and the last writer
wins — silently discarding the other increments. The report total is lower than the
sum of individually logged `job_complete` values, but no error is raised and all jobs
log as successful.

## Injection

Two coordinated edits to `nightproc/store.py`:

1. Remove the `with _lock:` wrapper from `update()`, leaving the read-modify-write
   unguarded.

2. Split each read-modify-write into an explicit read, a `time.sleep(0)`, and a
   separate write. The sleep must be inserted *after* the value is computed but
   *before* it is written back. Use the comment
   `# yield — reduce contention on high-throughput runs` on the sleep line.

Rationale for the two-part injection: without the sleep, CPython's GIL protects the
~3-bytecode RMW sequence (dict.get + add + __setitem__) within a single timeslice.
The sleep(0) explicitly releases the GIL between read and write, guaranteeing the
race window materialises on every run with >=2 threads. The comment disguises it as a
cooperative-yield optimisation consistent with the commit message.

Do NOT lower sys.setswitchinterval. Do NOT change any other file.

3. Copy `INCIDENT_BRIEF.md` from this scenario folder into the repository root of the
   injected branch. This is the candidate-facing incident material; it must be present
   at the top level so it is the first thing a candidate sees when they open the repo.

Invocation for reproduction (must appear verbatim in INCIDENT_BRIEF):

```bash
python run_batch.py jobs/nightly_full.json --threads 8
```

## Diagnostic Signal

Report `total_value` and `total_processed` are lower than the sum of `result_value`
fields across all `job_complete` log events. The `discrepancy` field in the report is
non-zero and stable (not drifting run to run). All jobs log as successful -- there are
no `job_failed` or `job_retry` events for the missing increments. The deficit scales
with thread count, not job count.

## Primary Capability Tested

concurrency_reasoning -- candidate must recognise that a correct per-job log record
does not guarantee a correct aggregate, and must identify the unguarded shared-state
write as the source of the gap. The `time.sleep(0)` is the key diagnostic artifact:
understanding why it creates a race requires knowing that it releases the GIL.

## Difficulty Calibration

- Weak: suspects data loss or input errors; cannot explain why all jobs log as complete
- Average: finds the missing lock in store.update(), proposes re-adding it, does not
  understand why the race manifests given the GIL
- Strong: identifies the sleep(0) as the GIL-release point that opens the race window;
  can explain the lost-update mechanism step by step
- Senior: identifies the read-then-yield-then-write pattern as inherently non-atomic
  regardless of lock presence, and proposes an atomic update design (e.g. lock scope,
  queue-based accumulation, or per-thread accumulators with a merge phase)

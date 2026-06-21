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
The program completes without error. The report totals are wrong.

The race occurs on all three flat keys written by `store.update()`:
`{category}_count`, `{category}_total`, and `{category}_failed`. Each key has its own
independent read-modify-write sequence. Lost updates on `_count` produce a discrepancy
in the invariant check; lost updates on `_total` corrupt the value sum silently.

## Injection

**Injection site:** `nightproc/store.py` — `update()` function, lines 34–40.

Remove the `with _lock:` block in `store.update()`, leaving the body unguarded:

```python
# INJECTED (faulty) version of store.update()
def update(accumulator, category, value, failed=False):
    if failed:
        key = f"{category}_failed"
        accumulator[key] = accumulator.get(key, 0) + 1
    else:
        accumulator[f"{category}_count"] = accumulator.get(f"{category}_count", 0) + 1
        accumulator[f"{category}_total"] = accumulator.get(f"{category}_total", 0) + value
```

The `_lock` object at module level can remain — its presence is a red herring for candidates
who check the imports but not the call site.

**Do not touch `runner.py`, `processor.py`, or any other module.** The fault is a
single-function change in `store.py`.

**Note:** The canonical codebase has the lock in place and is correct. This injection
creates a scenario variant. The canonical codebase must not be modified.

## Stress Job File

`sample_jobs.json` (20 jobs, ~5ms per job) is unlikely to produce a consistently
observable discrepancy on a modern machine due to the narrow race window and the GIL.

For reliable fault expression, this scenario requires a stress job file:

- Minimum **200 jobs**, all standard processing mode (fast path, ~5ms each)
- At least **6–8 threads** (`--threads 8`)
- All jobs in the same 1–2 categories to maximise contention on a small key set

A suitable stress job file should be created at:
`codes/prob-001/scenarios/scen-001/stress_jobs.json`

Run command for the assessment:
```
python run_batch.py codes/prob-001/scenarios/scen-001/stress_jobs.json --threads 8
```

With this configuration the discrepancy is reliably non-zero across repeated runs.

## Diagnostic Signals

**Primary signal — `reporter_complete` log event:**

```json
{
  "event": "reporter_complete",
  "job_count": 200,
  "total_processed": 193,
  "discrepancy": 7
}
```

`job_count` comes from the thread-safe `AtomicCounter` (always correct).
`total_processed` is summed from `{category}_count` keys in the accumulator (corrupted).
`discrepancy = job_count - total_processed - failed_count` is non-zero when the
accumulator has lost updates.

**Secondary signal — `total_value` in `report.json`:**

The JSON report written to disk also contains `total_value` which will be understated
relative to what is expected from the job inputs. This is harder to notice without a
known-good reference but a careful candidate will compute the expected value manually.

**What is absent:**

- No exception, no stack trace, no error log
- `job_start` and `job_complete` events fire for every job — the log looks clean
- Worker threads exit cleanly via `worker_exit` events
- The race is invisible at the per-job level; it only manifests in the aggregate

## Primary Capability Tested

`concurrency_reasoning` — candidate must identify that the read-modify-write sequence
is not atomic even though individual dict operations are GIL-protected in CPython.
The `.get()` call and the assignment are two separate bytecode operations with a
preemption window between them.

## Difficulty Calibration

- **Weak:** runs the code, sees no exception, declares it working; does not look at
  the `discrepancy` field or dismisses it as expected variation
- **Average:** notices the non-zero discrepancy, identifies the accumulator as the
  likely source, applies a lock around the write-only line (partial fix — does not
  cover the read)
- **Strong:** identifies the correct critical section boundary as the full
  read-modify-write; wraps the get + assign sequence atomically, matching the
  canonical fix
- **Senior:** questions whether a shared mutable dict is the right accumulator design
  at all; proposes a reduce-after pattern (workers collect locally, dispatcher merges
  serially after `q.join()`) which eliminates the shared state entirely

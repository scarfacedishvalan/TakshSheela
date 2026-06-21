---
scenario_id: scen-006
spec_id: prob-001
fault_surface_ref: FS-06
fault_family: resource
fault_subtype: unbounded_queue
difficulty: 4
observability_level: structured
status: pending
---

# Scenario: scen-006 — Queue Starvation

## Fault

A specific job category triggers the slow processing path. Under a certain input
distribution (many slow-path jobs), the thread pool is saturated by slow workers.
Fast-path jobs queue behind them. Batch runtime grows beyond the ops team's expected
window; some jobs time out before being processed.

## Injection

Inject a specific input distribution into the scenario (a job queue skewed toward
the slow-path category) rather than modifying the codebase. The canonical slow-path
code is already present — the fault is the input, not the code.

Alternatively: introduce a bug where the thread pool size is computed from a config
value that was accidentally set too low in a recent config change.

## Diagnostic Signal

Batch runtime metric is 4–6x normal. Queue depth metric stays elevated well into the
run rather than draining smoothly. Fast-path job categories are underrepresented in
the final report. No errors. Workers are running — just slowly.

## Primary Capability Tested

systems_thinking and observability_usage — candidate must correlate queue depth, runtime,
and output distribution to form the hypothesis. The problem is not visible in any single
signal; it requires cross-signal reasoning.

## Difficulty Calibration

- Weak: sees no errors, marks the system as healthy
- Average: notices the runtime anomaly, attributes it to load rather than distribution
- Strong: correlates queue depth with job category distribution, identifies the slow path
- Senior: identifies the thread pool sizing as a systemic risk given unbounded slow-path variance

---
scenario_id: scen-003
spec_id: prob-001
fault_surface_ref: FS-03
fault_family: semantic
fault_subtype: wrong_algorithm
difficulty: 3
observability_level: structured
status: pending
---

# Scenario: scen-003 — Retry Duplication

## Fault

When a job fails transiently and is retried, the original accumulator write is not
rolled back before the retry. Both the failed attempt's partial result and the retry's
result are accumulated. Certain job categories are double-counted.

## Injection

Alter the retry path so that accumulator cleanup is skipped or the retry re-enters
the full accumulation path without clearing the prior write.

## Diagnostic Signal

Report total is higher than `jobs_processed` log count. Inflation only affects
categories where transient errors occur. The discrepancy is proportional to retry
volume, not thread count — the key diagnostic differentiator from scen-001.

## Primary Capability Tested

root_cause_analysis — candidate must distinguish inflation (scen-003) from undercounting
(scen-001 and scen-002), then trace the inflation specifically to the retry path rather
than the normal processing path.

## Difficulty Calibration

- Weak: notices wrong totals, no further diagnosis
- Average: finds the retry code, doesn't see the accumulator write before it
- Strong: traces the exact execution path for a failing job and identifies both writes
- Senior: redesigns the retry to be idempotent with respect to accumulation

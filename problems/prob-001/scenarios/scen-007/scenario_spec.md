---
scenario_id: scen-007
spec_id: prob-001
fault_surface_ref: FS-01
fault_family: semantic
fault_subtype: key_collision
difficulty: 3
observability_level: structured
status: injected
---

# Scenario: scen-007 — Silent Category Merge

## Fault

A one-line normalisation is added to `store.update()` that lower-cases the category
and replaces hyphens with underscores before building the accumulator key. Two
distinct category names in the job input — `"invoices"` (known to config) and
`"Invoices"` (legacy capitalisation from an upstream API) — collapse to the same
key. All `"Invoices"` jobs are silently accumulated under `"invoices"`. The
`"Invoices"` category never appears in the report. The report's top-level
`discrepancy` field is **zero** because no jobs are lost — they are merely
mis-attributed.

## Injection

Single edit to `nightproc/store.py`: add one line at the top of `update()`, before
the lock is acquired:

```python
category = category.lower().replace("-", "_")  # normalise — legacy category names from v1 API
```

Do NOT change any other file.

The injected job file (`collision_jobs.json`) contains 30 jobs:
- 20 with `category: "invoices"` (config multiplier 1.5)
- 10 with `category: "Invoices"` (no config entry; falls back to multiplier 1.0)

Both sets write to the `invoices` accumulator bucket after normalisation. The
differing multipliers mean the per-job `result_value` fields in the log are
internally consistent with each job's own payload, but the merged bucket total
does not match any single multiplier applied uniformly to the combined count.

Invocation for reproduction (must appear verbatim in INCIDENT_BRIEF):

```bash
python run_batch.py jobs/collision_jobs.json --threads 4
```

## Diagnostic Signal

- The report contains no `"Invoices"` category entry. The `"invoices"` count (30)
  is 50% higher than the expected 20.
- The top-level `discrepancy` is 0. The built-in health check passes.
- Structured log `job_complete` events show `category: "Invoices"` for 10 jobs,
  but no corresponding category in `report.json`.
- The `"invoices"` `value` in the report (36,645) does not equal either the sum
  of `invoices`-category log `result_value` fields (30,075) or the sum of all
  logged `result_value` fields (36,645 = 30,075 + 6,570). A candidate who sums
  log values by category and compares to the report will find the discrepancy
  within the category breakdown, not in the totals.
- The `config_load` event shows only four categories loaded (`invoices`, `credits`,
  `adjustments`, `writeoffs`). `"Invoices"` is absent — no config entry, no error.

## Primary Capability Tested

debugging_discipline — candidate must notice that `discrepancy: 0` does not mean
the report is correct. The fault is in the *categorical attribution*, not the
count. Diagnosis requires correlating structured log `category` fields with report
category keys and noticing the case mismatch.

## Difficulty Calibration

- Weak: sees `discrepancy: 0`, marks the batch as healthy
- Average: notices the missing `"Invoices"` category in the report; attributes it
  to the input (assumes those jobs were never submitted) rather than reading the log
- Strong: finds `job_complete` events with `category: "Invoices"` in the log,
  confirms they were processed, then traces the category to the report and
  finds it absent; locates the normalisation line in `store.update()`
- Senior: identifies that `discrepancy` is structurally blind to mis-attribution
  (it only checks counts, not category correctness); proposes a report-time check
  that cross-references log category values against report keys

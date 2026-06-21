---
scenario_id: scen-004
spec_id: prob-001
fault_surface_ref: FS-04
fault_family: state
fault_subtype: stale_cache
difficulty: 5
observability_level: structured
status: pending
---

# Scenario: scen-004 — Stale Config Cache

## Fault

The per-category processing config is loaded once at startup and cached. A config file
change is made mid-run (simulated by a pre-positioned updated config file with a
timestamp that falls within the run window). Workers continue using the original cached
config for the remainder of the run.

## Injection

Ensure the config cache has no reload mechanism and that the scenario's observability
artifacts include a config file modification event mid-run. The canonical codebase's
config cache path must be injectable without altering its interface.

## Diagnostic Signal

Output values for affected categories shift part-way through the run. Two cohorts of
results are visible in the structured log: jobs processed before and after the config
change timestamp have different numerical profiles. A config file modification event
appears in the filesystem log. Workers logged no config reload.

## Primary Capability Tested

debugging_discipline and systems_thinking — candidate must correlate a config change
event with a behavioral discontinuity in output. No error. No stack trace. The diagnosis
requires reading multiple signal types and reconstructing a timeline.

## Difficulty Calibration

- Weak: looks for errors, finds none, cannot form hypothesis
- Average: notices the numerical discontinuity, attributes it to data rather than config
- Strong: correlates the config modification timestamp with the output shift, finds the cache
- Senior: identifies the cache-on-startup pattern as a systemic risk, proposes a reload mechanism

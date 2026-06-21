---
scenario_id: scen-005
spec_id: prob-001
fault_surface_ref: FS-05
fault_family: resource
fault_subtype: memory_leak
difficulty: 4
observability_level: structured
status: pending
---

# Scenario: scen-005 — Unbounded Run History

## Fault

The run-history structure accumulates metadata for every run in an in-memory list that
is never cleared between invocations. Over many runs the process grows unboundedly.
Individual runs are correct; the problem is only visible across multiple executions.

## Injection

No injection needed to the canonical codebase logic — the run history is already
accumulated. The scenario is constructed by providing an observability artifact showing
memory growth across 30+ simulated runs, and a process that is currently consuming
anomalous memory after weeks of nightly execution.

## Diagnostic Signal

Memory metric grows monotonically across runs in the provided metrics artifact. A single
run shows no anomaly. The run-history structure size correlates with run count. Ops
team reports the process needs manual restart approximately weekly.

## Primary Capability Tested

systems_thinking — candidate must reason across run boundaries, not just within a
single run. The symptom (high memory, weekly restarts) is decoupled from any individual
run's behavior.

## Difficulty Calibration

- Weak: inspects single run, finds nothing wrong, cannot explain the memory growth
- Average: identifies memory growth but attributes it to the job queue rather than history
- Strong: finds the run-history list, identifies it grows without bound, confirms via metrics
- Senior: identifies the design flaw (audit history belongs in a bounded store, not memory)

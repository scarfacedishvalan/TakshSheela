---
spec_id: prob-001
version: "0.2"
status: spec_ready

domain: background_worker
genome_scale: medium
genome_maturity: mid_life
genome_team_style: mixed

# Fault families the canonical codebase must architecturally support.
# These are design requirements, not committed faults.
# The blueprint must satisfy each declared surface.
# Scenarios draw from these surfaces during fault injection.
fault_families_supported:
  - coordination
  - state
  - resource
  - temporal
---

# Spec: prob-001

## System Concept

A batch job processing service used by an ops team to process queued work items nightly.

The system pulls jobs from an in-memory queue, fans them out to a configurable thread pool,
accumulates results into a shared structure, and writes a structured summary report at the end.
Downstream systems consume the report. The system runs unattended; output correctness
is validated hours later.

Three primary components:

**Job Dispatcher** — drains the job queue and distributes work to the thread pool. Added
in v2 when sequential processing became too slow for the growing job volume.

**Worker** — processes a single job and records its result into the shared accumulator.
Workers are stateless with respect to individual jobs but share the accumulator.

**Reporter** — once processing is complete, reads the accumulator and writes the summary
report including total counts, per-category breakdowns, and success/failure rates.

The system also maintains:
- A per-category processing config, loaded at startup and cached in memory
- A retry mechanism for transiently-failing jobs
- A run-history log accumulated in memory across invocations (for audit purposes)
- Structured logging of job events and run metrics

---

## Historical Evolution

v1 was a sequential loop. Correct, simple, obviously safe. v2 introduced the thread pool
for throughput. The threading was added by a different engineer than the original author.
The core data structures — accumulator, config cache, run history — were designed for
single-threaded use and adapted rather than redesigned. The code carries visible evidence
of this: naming conventions from v1, structural patterns that work correctly in isolation
but have hazards under concurrency, comments that reference the old approach.

This history is important. The system should feel like it evolved, not like it was
designed with threading in mind from the start.

---

## Operational Characteristics

- Runs nightly as a scheduled batch job
- Input: queue of job descriptors (in-memory, loaded from file at startup)
- Output: structured JSON report written to disk
- Runtime: seconds to low minutes depending on queue depth and thread count
- Thread count is configurable; default is 4
- Failures are retried up to a configurable limit before being marked as failed
- The ops team monitors the report output; anomalies are noticed the following morning
- No external services — all in-process, stdlib only

---

## Fault Surfaces Supported

These are architectural requirements. The blueprint must design the system such that
each surface is genuinely present and injectable without requiring an architectural
overhaul. The canonical codebase must be correct — these surfaces are latent
vulnerabilities, not active faults.

### FS-01 — Shared Mutable Accumulator
**Requirement:** Workers must share a mutable aggregation structure and update it
concurrently. The structure must be designed in a way that looks safe but admits
non-atomic update patterns.
**Fault families:** coordination, temporal
**Why required:** Enables the richest class of concurrency scenarios. The update
pattern must be non-trivially unsafe — not an obvious global variable, but a
structure that requires understanding Python's memory model to reason about correctly.

### FS-02 — Reporter Synchronization Boundary
**Requirement:** The reporter must have an explicit synchronization point with the
worker pool. This boundary must be a discrete, auditable code location — not implicit.
**Fault families:** temporal
**Why required:** Enables premature-read scenarios. The synchronization must be
explicit enough to be removable or misplaceable by a fault injection.

### FS-03 — Retry and Deduplication Interaction
**Requirement:** The retry mechanism must re-submit failed jobs through the same
accumulation path as original jobs. There must be no deduplication of accumulator
writes on retry.
**Fault families:** semantic, state
**Why required:** Enables double-counting scenarios. The retry path must be
structurally similar enough to the normal path that the duplication is non-obvious.

### FS-04 — Startup Config Cache
**Requirement:** Processing configuration must be loaded at startup and stored in a
module-level or instance-level cache. It must not be reloaded automatically. The cache
must be used by workers during processing.
**Fault families:** state
**Why required:** Enables stale-config scenarios where config changes mid-run are
invisible to workers.

### FS-05 — Unbounded Run History
**Requirement:** The system must accumulate run-level metadata across invocations in
an in-memory structure that is never cleared. This structure must grow with each run.
**Fault families:** resource
**Why required:** Enables memory leak scenarios detectable only across multiple runs.
The accumulation must be realistic — an "audit log" or "run history" feature, not
obviously a leak.

### FS-06 — Worker Throughput Variance
**Requirement:** The worker must have at least two distinct processing paths with
materially different execution times (e.g. a fast path and a slow path based on job
type or category). The thread pool must be small enough that slow-path jobs can
starve fast-path jobs.
**Fault families:** resource, temporal
**Why required:** Enables queue starvation scenarios where throughput degradation is
detectable through metrics but not through errors.

---

## Scenario Diversity Goals

The canonical codebase should support at least six distinct scenario families:

1. **Lost update race** — concurrent accumulator writes lose updates silently
2. **Premature reporter** — reporter reads accumulator before workers finish
3. **Retry duplication** — failed jobs are double-counted on retry
4. **Stale config** — per-category config is stale after a mid-run config change
5. **Memory growth** — run history grows unbounded across invocations
6. **Queue starvation** — slow-path jobs exhaust the thread pool

Each scenario should be independently injectable from the canonical codebase without
modifying any other part of the system.

---

## Constraints

- stdlib only: `threading`, `queue`, `logging`, `json`, `time`, `collections`
- No third-party libraries
- No web framework, no HTTP, no database
- Threading-based concurrency only — no asyncio
- No comment or identifier in the canonical codebase should name a fault surface as unsafe
- Each fault surface must look like a reasonable production design decision

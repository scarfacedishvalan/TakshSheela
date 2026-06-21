# Problem Ideation: prob-001

*Level 1 artifact — completely free-form. Think out loud here before writing the spec.*

---

## What Kind of Problem Do I Want?

A concurrent batch processing system. The interesting thing about this domain is that
concurrent systems have a whole class of failure modes that are invisible to the program
itself — no exception, no crash, just wrong output. That's the richest space for
assessment because it separates candidates who debug by following errors from candidates
who debug by reasoning about system behavior.

Framework knowledge should not help at all. The interesting skill here is concurrency
reasoning and debugging discipline, not knowing the right library call.

---

## System Character

A batch job processing service used by an ops team. It reads a queue of work items,
fans them out to a thread pool for parallel processing, accumulates results, and writes
a summary report at the end.

This feels like something a small team built over time. v1 was sequential — simple,
obviously correct. v2 added threading for throughput, written by someone who understood
threads in general but didn't audit every design assumption from v1. The code carries
visible evidence of this history: variable names that made sense before threading, a
comment or two referencing the old approach, design patterns that work fine single-threaded
but have subtle hazards under concurrency.

The system is operationally real: it has configuration, retry logic, logging, a config
cache, a run-history mechanism, queue management, and a reporter. These are all realistic
production features that also happen to create interesting fault opportunities.

---

## What Makes This System Rich for Assessment

The system has multiple distinct areas where things can go wrong in non-obvious ways:

- The accumulator is shared mutable state accessed by concurrent workers
- The reporter must synchronize with workers before reading — ordering matters
- Retry logic can interact with deduplication in subtle ways
- Config is loaded at startup and cached — stale if config changes during a run
- Run history is accumulated in memory across multiple runs — never cleared
- Queue depth and worker throughput interact in ways that can cause starvation

None of these are bugs in the canonical codebase. They are structural characteristics
that make the system realistic and also make it a rich source of fault scenarios.

---

## Operational Context

Nightly batch job. Ops team runs it. Runtime is seconds to low minutes depending on
queue depth. It writes a structured report that downstream systems consume. When the
report is wrong, the downstream impact is noticed hours later.

This timing — fault fires at night, impact noticed the next morning — is realistic and
adds to assessment richness. A candidate is debugging something that happened in the
past, not something they can trivially reproduce in isolation.

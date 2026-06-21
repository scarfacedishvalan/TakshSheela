---
blueprint_id: prob-001-bp-01
spec_id: prob-001
version: "0.2"
status: revised
---

# Blueprint: prob-001-bp-01

---

## System Overview

The system is a nightly batch job processing service called **Batchwork**. It is operated
by a small ops team who loads it with a queue of work items each evening and expects a
structured JSON summary report the following morning. The report is consumed by downstream
systems for reporting and billing purposes; incorrect totals have downstream financial
consequences, which is why the ops team notices discrepancies — though usually only after
the fact.

The system was originally written as a sequential loop by one engineer and worked
reliably for about a year. When job volume grew, a second engineer added a thread pool
to speed up processing. This is the v2 codebase. The original data structures were
adapted rather than redesigned; the threading layer was laid on top of an architecture
that assumed single-threaded access throughout.

Normal operation: the operator invokes the system via a CLI entrypoint, passing a job
file and a config file. The system loads the job queue, initialises the thread pool,
drains the queue using workers, and writes the report to disk. The process exits cleanly.
Runtimes range from thirty seconds for small batches to several minutes for large ones.
There are no external service dependencies — everything is in-process.

The codebase is stdlib-only. It uses `threading`, `queue`, `logging`, `json`, `time`,
and `collections`. There are no third-party libraries. The code is medium-sized — enough
modules that a new reader needs to navigate before understanding the flow, but not so
large that the structure is opaque.

---

## Subsystems

### Job Dispatcher

The dispatcher is the system's entry point after initialisation. It owns the job queue
and is responsible for draining it by handing jobs to the worker pool. It was the core
of the v1 sequential processor — in v1, it simply iterated over the job list and called
the worker function directly. In v2, it submits jobs to a thread pool instead.

**Responsibility:** Drain the job queue by submitting each job to the worker pool. Monitor
queue state. Signal completion when the queue is empty and all submitted work is done.

**Runtime role:** Runs in the main thread. Manages the lifecycle of the worker pool.
Owns the sentinel-based queue drain protocol.

**State owned:** The job queue (`queue.Queue`), the thread pool (list of `threading.Thread`
objects), and a thread-safe atomic job counter implemented with `threading.Lock` and
a plain integer. The job counter is used for logging and is the ground truth for
how many jobs were submitted — it is always correct.

**Key interfaces:** Accepts a pre-loaded list of job dicts at construction. Exposes a
`run()` method that starts the pool, drains the queue, waits for completion, and
triggers the reporter. Exposes the job counter as a read-only property for the reporter.

The dispatcher is the only component that starts and joins worker threads. Thread
lifecycle is fully owned here.

---

### Worker

The worker is the processing unit. Each thread runs a worker loop that pulls jobs from
the shared queue, processes them, and records results into the shared accumulator. Workers
were introduced in v2. In v1, the equivalent logic lived inline in the dispatcher loop.

**Responsibility:** Pull jobs from the queue, process each job according to its category
and the loaded config, classify the result, and write it to the shared accumulator.
Handle transient failures by re-queuing the job up to the configured retry limit.

**Runtime role:** Each worker runs in its own thread. Multiple workers run concurrently.
Worker count is configurable; default is four threads.

**State owned:** Workers own no state of their own. They read from the shared job queue,
read from the shared config cache, and write to the shared accumulator. All three of
these are owned by other components and shared across threads.

**Key interfaces:** Workers are not instantiated as classes — they are thread target
functions that close over the shared queue, accumulator, config cache, and a stop event.
This design comes from v1 where the equivalent was a plain function. The closure pattern
was kept when threading was added for minimal disruption.

The worker has two processing paths: a fast path for standard jobs (the majority) and
a slow path for jobs flagged as requiring extended processing. The slow path is
materially slower — it includes a simulated heavy computation. The split is determined
by a field in the job descriptor.

---

### Accumulator

The accumulator is the shared result collection structure. It was designed in v1 as a
plain module-level dict that the dispatcher wrote to after each sequential job. In v2
it is written to concurrently by all worker threads.

**Responsibility:** Hold per-category result totals as jobs complete. Provide a stable
snapshot to the reporter after all workers are done.

**Runtime role:** Not a process or thread — it is a shared data structure accessed by
all worker threads and read by the reporter. It is not a class; it is a plain dict
held as an attribute of the dispatcher (because in v1 the dispatcher owned the whole
processing loop).

**State owned:** A dict keyed by result category (strings), with integer total values.
Categories are dynamically added as new category types are encountered during processing.
The accumulator also holds a per-category count of failed jobs, stored as a nested dict.

**Key interfaces:** Workers access it directly via the shared reference. There is no
accessor API — it is passed by reference as a closure variable. This was fine in v1.

The accumulator is the most structurally important component for fault surface purposes.
It is shared mutable state with no encapsulation and no synchronisation, accessed
concurrently by all worker threads.

---

### Config Cache

The config cache holds per-category processing parameters loaded from the config file
at startup. Workers consult it during the slow path to determine processing behaviour
for each job category.

**Responsibility:** Load config from disk at startup. Provide read access to per-category
config during processing. The cache is never refreshed during a run.

**Runtime role:** Library component. Initialised once by the main thread before the
dispatcher starts. Accessed read-only by worker threads during processing — but because
Python dicts are not thread-safe for mutation, and the cache is only mutated at
startup before threads start, the read-only concurrent access is actually safe. This
is a distinction workers implicitly rely on.

**State owned:** A module-level dict mapping category names to parameter dicts. Also
stores the config file path and load timestamp, which are visible in the logs.

**Key interfaces:** A `load(path)` function called once at startup. A `get(category)`
function used by workers. No reload or invalidation mechanism.

---

### Reporter

The reporter reads the accumulator after all workers are done and writes the structured
JSON report to disk.

**Responsibility:** Compute summary statistics from the accumulator — total jobs, per-
category breakdown, success/failure counts. Write the structured report. Log the run
summary including total count (from the dispatcher's job counter) and reported total
(from the accumulator). These two numbers should always match; the log line that prints
both is the most useful single diagnostic line in the system.

**Runtime role:** Runs in the main thread, invoked by the dispatcher after the worker
pool has been joined. Sequential — no concurrency at this stage.

**State owned:** Nothing persistent. Reads the accumulator and job counter, computes
derived values, writes to disk, and exits.

**Key interfaces:** A `generate(accumulator, job_count, output_path)` function. Called
once per run by the dispatcher.

---

### Run History

The run history is a lightweight audit mechanism added in v2 by the second engineer.
After each run, a summary dict (run timestamp, job count, report path, runtime seconds)
is appended to a module-level list. The intent was to make it easy to query recent run
history in a future admin interface that was never built.

**Responsibility:** Accumulate per-run metadata across invocations of the process. In
normal single-invocation use, the process exits after each run and the list has one
entry. However, the system supports a `--keep-alive` mode (documented in the README)
that holds the process open and accepts successive job files without restarting — useful
for the ops team during maintenance windows when startup overhead matters. In this mode,
the run history list grows by one entry per run indefinitely and is never cleared.

**Runtime role:** Library component. Written to by the dispatcher at the end of each
run. Never read by anything in the current codebase.

**State owned:** A module-level list of dicts. Never cleared. Never bounded. Grows
by one entry per run.

**Key interfaces:** An `append_run(metadata)` function called by the dispatcher. A
`get_history()` function that returns the list — unused in normal operation.

---

## Dependency Graph

The dispatcher is the coordinator. It depends on everything else: it constructs the
accumulator, loads the config cache, instantiates the workers (via thread targets),
invokes the reporter, and appends to the run history.

Workers depend on three shared structures they don't own: the job queue (owned by
dispatcher), the accumulator (owned by dispatcher), and the config cache (owned by
the config cache module). This ownership structure — dispatcher owns the data,
workers access it by reference — comes directly from v1 where the dispatcher iterated
and wrote sequentially. The threading layer did not change ownership.

The reporter depends on the accumulator and the job counter, both owned by the
dispatcher. The reporter has no dependency on workers directly — it assumes workers
are done before it is called, which is an assumption enforced by the dispatcher's
join sequence.

The config cache has no dependencies — it reads from disk at startup and is then
static.

The run history module has no dependencies — it is a passive accumulator.

There is a notable structural asymmetry: the accumulator is accessed by workers
without going through the dispatcher, even though the dispatcher owns it. In v1 this
was fine — the dispatcher called the worker function and wrote the result back itself.
In v2 the reference was passed directly to thread closures for efficiency, bypassing
the dispatcher's control entirely.

---

## Project Structure

The repository root is named `nightproc` — the internal name the ops team gave it when
it was first set up. The package inside is also `nightproc`. The name predates the
system's current scope and doesn't describe what it does, which is typical for internal
tooling that outlives its original purpose.

```
nightproc/
│
├── run_batch.py                ← CLI entrypoint. Parses args, loads job file,
│                                 calls config and runner. This is what the ops team
│                                 invokes. It is not named main.py.
│
├── nightproc/
│   ├── __init__.py
│   │
│   ├── runner.py               ← Job Dispatcher. The name "runner" sounds like the
│   │                             entrypoint but it is the coordinator/dispatcher.
│   │                             Contains the Dispatcher class and the thread pool
│   │                             lifecycle. v1 comments still describe a sequential loop.
│   │
│   ├── processor.py            ← Worker. Thread target functions live here.
│   │                             process_job() is the fast path.
│   │                             process_job_extended() is the slow path.
│   │                             Both write directly to the accumulator passed as arg.
│   │
│   ├── store.py                ← Accumulator. Not a class — a module that provides
│   │                             make_accumulator(), update(), and read() functions.
│   │                             "store" is a holdover name from when this was a
│   │                             file-backed store in an earlier prototype.
│   │
│   ├── settings.py             ← Config Cache. Loads and caches per-category config.
│   │                             Module-level _cache dict. load() and get() functions.
│   │                             Named "settings" rather than "config" to avoid
│   │                             shadowing the standard library.
│   │
│   ├── report.py               ← Reporter. generate() function. Reads accumulator,
│   │                             computes totals, writes JSON. Also contains the
│   │                             critical summary log line comparing job_count vs total.
│   │
│   ├── history.py              ← Run History. Module-level _runs list. append_run()
│   │                             and get_history(). The _runs list is never cleared.
│   │
│   └── util/
│       ├── __init__.py
│       ├── counter.py          ← Thread-safe atomic counter used by dispatcher
│       │                         for job_count. Lock + int. Correct by design.
│       └── log.py              ← Logging setup. Configures JSON structured formatter
│                                 and rotating file handler. Called once at startup.
│
├── config/
│   └── default.yaml            ← Default per-category config. Multipliers, processing
│                                 modes, timeout values. Ops team edits this file.
│
├── jobs/
│   └── sample_jobs.json        ← Example job file for testing and ops use.
│
├── tests/
│   ├── test_processor.py
│   ├── test_report.py
│   └── test_runner.py          ← Tests cover v1 sequential behaviour; some tests
│                                 pass trivially because they don't exercise concurrency.
│
└── README.md                   ← Describes CLI usage including --keep-alive mode.
                                  Written in v1 era; threading section is a short
                                  addendum at the bottom.
```

### Navigational Notes for Code Generation

The module naming deliberately does not map one-to-one to subsystem names in this
blueprint. A candidate reading `runner.py` will not immediately know it is the
dispatcher. A candidate reading `store.py` will not immediately know it is the
accumulator. This friction is intentional — it reflects the realistic naming drift
of a mid_life internal tool and prevents candidates from pattern-matching their way
to the relevant code without reading it.

The v1-era comments in `runner.py` and `processor.py` describe the sequential loop
as if it is still the primary execution model. A candidate reading the inline comments
may initially believe processing is sequential before noticing the thread pool
instantiation. This is the most important single piece of code generation friction
for the concurrency scenarios (scen-001, scen-002).

---

## Runtime Lifecycle

**Startup:** The main thread parses CLI arguments, loads the job file into a list of
dicts, calls `config_cache.load(config_path)`, constructs the dispatcher with the job
list, and calls `dispatcher.run()`.

**Queue loading:** The dispatcher loads all jobs from the list into the `queue.Queue`
before starting any threads. This is a sequential operation in the main thread.

**Thread start:** The dispatcher starts N worker threads (default: four). Each worker
begins pulling jobs from the queue immediately.

**Processing:** Workers run concurrently. Each worker pulls a job, looks up its category
in the config cache, processes it on either the fast or slow path, classifies the result,
and writes to the accumulator. Failed jobs are re-queued by the worker with an incremented
retry counter; if the retry limit is exceeded, the job is recorded as failed in the
accumulator without re-queuing.

**Queue drain:** Workers detect an empty queue via a sentinel value placed in the queue
by the dispatcher after all jobs have been enqueued. When a worker receives the sentinel,
it re-enqueues it (so the next worker also exits) and terminates its loop.

**Join:** The dispatcher calls `thread.join()` on each worker thread in sequence. This
is the synchronisation boundary — the reporter must not run before this completes.

**Reporting:** The dispatcher calls `reporter.generate()` with the accumulator and job
counter. The reporter computes totals, logs the summary line, and writes the JSON file.

**Run history:** The dispatcher calls `run_history.append_run()` with run metadata.

**Exit:** The process exits. All in-memory state is discarded — including the run history
list, unless the process is kept alive.

The join sequence is the most operationally critical ordering constraint. Everything
depends on it. If the join is misplaced — inside the sentinel loop rather than after
it, or missing for any thread — the reporter may read a partially-written accumulator.

---

## Data Model

**Job descriptor** — the unit of work. A dict with at minimum: `job_id` (string),
`category` (string), `payload` (dict), `retry_count` (int, default 0). Loaded from
the job file. Mutated in-place when retried (retry_count incremented). Category
determines which config parameters apply and which processing path is used.

**Accumulator** — a flat dict in the v1 style, with composite string keys to separate
totals from failure counts. Keys follow the pattern `{category}_total` and `{category}_failed`.
Example: `{"invoices_total": 4821, "invoices_failed": 3, "credits_total": 1204, "credits_failed": 0}`.
This is the original v1 structure; the second engineer kept it when adding threading to
minimise the diff. It means there is no clean type boundary around a category's data —
the reporter iterates keys and reconstructs per-category structure by splitting on `_total`
and `_failed` suffixes. This is slightly awkward to read and subtly harder to navigate.
Written by workers. Read by reporter.

**Config entry** — a dict per category with processing parameters. Example fields:
`multiplier` (numeric, applied to payload values), `processing_mode` (string, determines
fast vs slow path), `timeout_seconds` (int). Loaded from the config file at startup.

**Report** — the final JSON output. Top-level keys: `run_id`, `generated_at`, `job_count`
(from dispatcher counter), `total` (summed from accumulator), `categories` (per-category
breakdown), `failed_count`. The `job_count` vs `total` discrepancy is the primary
diagnostic signal for accumulator corruption scenarios.

**Run history entry** — a dict appended per run: `run_id`, `started_at`, `finished_at`,
`job_count`, `report_path`. Accumulates in the module-level run history list.

---

## System Invariants

**Invariant 1 — Count consistency:** After a correct run, `report.job_count` must equal
`report.total + report.failed_count`. The dispatcher's atomic job counter is the ground
truth; the accumulator must account for every submitted job exactly once. Violation
produces a report where the numbers don't add up — the primary observable signal for
lost-update and premature-reporter scenarios.

**Invariant 2 — Reporter post-join:** The reporter must never read the accumulator
while any worker thread is still running. The join sequence is the only mechanism
enforcing this. Violation produces non-deterministic report totals with a different
symptom profile from Invariant 1 (stable undercounting vs drifting undercounting).

**Invariant 3 — Retry idempotence:** A job that is retried must contribute exactly once
to the accumulator total, not once per attempt. The retry path must not write a partial
result before re-queuing. Violation produces inflation rather than undercounting.

**Invariant 4 — Config stability:** All workers processing jobs in the same run must
use the same config. Config must not change between the time a worker reads it and the
time it uses the value to compute a result. Within a run this is trivially satisfied
(config is read-only during processing); across runs with a long-lived process it
depends on the config file not changing between invocations.

**Invariant 5 — Bounded memory:** The run history list must not grow without bound in
a long-lived process. In practice this is violated by the current design if the process
is kept alive across multiple runs — the list grows by one entry per run indefinitely.

---

## Logging Schema

All log events use Python's `logging` module with a structured formatter that emits
JSON lines to a rotating file handler. Every event carries a common envelope:
`timestamp` (ISO-8601), `level`, `event` (the event name below), and `run_id`.
Additional fields are event-specific.

This schema is a code generation constraint: every event listed here must be emitted
at the specified point in the code. Omitting any event will make one or more scenario
diagnostic signals unavailable.

---

### config_load
Emitted once by the config cache module after successfully loading and parsing the
config file.

Fields: `path`, `load_timestamp`, `category_count`, `categories` (list of category names).

*Critical for FS-04: candidates use `load_timestamp` to establish when the config was
read and compare it against the config file's modification time.*

---

### job_start
Emitted by the worker at the moment it dequeues a job and begins processing.

Fields: `job_id`, `category`, `processing_path` (fast/slow), `thread_id`, `retry_count`.

*Used to reconstruct per-job timelines and identify which thread processed which job.*

---

### job_complete
Emitted by the worker after successfully processing a job and writing to the accumulator.

Fields: `job_id`, `category`, `processing_path`, `result_value`, `thread_id`, `duration_ms`.

*Critical for FS-04: `result_value` in combination with `job_start.category` allows
candidates to detect the multiplier cohort shift. The ratio of `result_value` to payload
value should be consistent within each cohort and different between cohorts.*

---

### job_retry
Emitted by the worker when a job fails and is re-queued for retry.

Fields: `job_id`, `category`, `retry_count`, `reason`, `thread_id`.

*Critical for FS-03: candidates can count `job_retry` events per job to establish how
many times it was processed. If `job_complete` events for the same `job_id` exceed 1,
the double-write is confirmed.*

---

### job_failed
Emitted by the worker when a job exhausts its retry limit and is marked as permanently
failed.

Fields: `job_id`, `category`, `final_retry_count`, `thread_id`.

---

### worker_exit
Emitted by each worker thread just before its loop terminates (after receiving the
sentinel).

Fields: `thread_id`, `jobs_processed`, `timestamp`.

*Critical for FS-02: candidates compare `worker_exit` timestamps against
`reporter_start` to prove the reporter ran before all workers finished.*

---

### reporter_start
Emitted by the reporter at the very start of its `generate()` call, before reading
the accumulator.

Fields: none beyond the common envelope.

*Critical for FS-02. Must be the first thing the reporter emits, before any accumulator
access.*

---

### reporter_complete
Emitted by the reporter after writing the JSON report to disk.

Fields: `job_count` (from dispatcher counter), `total` (summed from accumulator),
`failed_count`, `discrepancy` (job_count minus total minus failed_count — non-zero
indicates a count consistency violation), `output_path`, `duration_ms`.

*The `discrepancy` field is the single most useful diagnostic value in the system.
Code generation must compute and emit it even when it is zero.*

---

### run_history_append
Emitted after the run history entry is appended.

Fields: `run_id`, `history_length` (current length of the run history list),
`runtime_seconds`.

*Critical for FS-05: `history_length` growing monotonically across runs is the
diagnostic signal for memory growth. Candidates can correlate it with process memory
metrics.*

---

## Fault Surfaces

### FS-01 — Shared Mutable Accumulator (coordination / temporal)

The accumulator is a plain dict passed by reference to all worker threads. Workers
perform updates of the form: read current total, add job result, write back. This
read-modify-write sequence is not atomic. Between the read and the write, another
thread may have already written a new value, which the first thread's write will
silently overwrite.

This is why it is a fault surface: the pattern looks safe. Python dicts are thread-safe
for individual operations. A reader who knows that `dict.__setitem__` is protected by
the GIL may conclude the accumulator is safe — and be wrong, because the hazard is
not in the individual operation but in the sequence. The fault is injected by ensuring
the update uses the non-atomic pattern. The canonical codebase uses the correct pattern
(a lock around the full read-modify-write); the injection removes or misplaces it.

Observable when violated: `report.total` is lower than `report.job_count`. The
discrepancy is non-deterministic and grows with thread count and queue depth.

---

### FS-02 — Reporter Synchronization Boundary (temporal)

The dispatcher calls `thread.join()` for each worker before calling the reporter.
This join sequence is the only thing preventing the reporter from reading a partially-
written accumulator. The join call is a single, discrete, removable code location.

This is why it is a fault surface: the join is structurally fragile. The most realistic
and assessment-rich injection is a misplacement rather than a deletion: the join calls
are moved inside the sentinel drain loop, so each thread is joined immediately when
the dispatcher observes its sentinel being re-enqueued — but this join fires as soon
as the sentinel is forwarded, before the worker has necessarily finished processing
its last job. The result is that some threads are joined too early and others not at
all, depending on queue timing. This looks careful to a code reviewer (you are joining)
but is wrong in a way that only manifests under certain queue orderings.

Other injectable variants: join skipped if dispatcher's error handler fires early;
join conditioned on a flag that is not always set.

Observable when violated: `report.total` is lower than `report.job_count`, but unlike
FS-01, the undercounting is stable across repeated runs (not drifting), and specific
job categories may be missing entirely from the output. The critical diagnostic signal
is log timestamps: `worker_exit` events appear after the `reporter_start` event,
proving the reporter ran before all workers finished.

---

### FS-03 — Retry Path Without Deduplication (semantic / state)

When a worker processes a job, it computes the result, writes it to the accumulator,
then checks the operation's return code to determine success or failure. On failure,
the job is re-queued with an incremented retry counter. On the retry, the job is
processed again and the result is written to the accumulator a second time. The
category total is inflated by one job's full result value for every job that fails
and is retried.

This is why it is a fault surface: the canonical codebase checks the return code
before writing to the accumulator — write only on confirmed success. The injection
swaps the order: write first, check after. The change is a single reorder of two
lines that are adjacent in the worker function. It looks like an innocent refactor.
The inflation only manifests for jobs that hit the transient failure path, so under
low-error conditions the report totals look correct.

Observable when violated: `report.total` is higher than `report.job_count`. Inflation
is proportional to retry volume and is confined to categories where transient failures
occur. This is the diagnostic differentiator from FS-01 and FS-02, both of which
produce undercounting — FS-03 is the only surface that produces overcounting.

---

### FS-04 — Config Cache Without Reload (state)

The config cache is loaded once at startup via a `load()` call and stored in a module-
level dict. There is no reload mechanism, no file-watch, and no TTL. Workers call
`get(category)` during processing and receive whatever was loaded at startup.

This is why it is a fault surface: the cache is behaviorally correct within a single
run where config doesn't change. The hazard only materialises if the config file is
updated while the process is running (or between runs in a long-lived process). The
cache has no awareness of this. The scenario is constructed by providing an updated
config file whose modification timestamp falls within the run window — the observability
artifacts will show a config change that the system did not react to.

Observable when violated: per-category totals for affected categories are wrong in a
specific, detectable way. The config `multiplier` for a category scales the payload
value before accumulation. If the multiplier changes mid-run (e.g. from 1.0 to 1.5),
jobs processed before the change use the old multiplier and jobs processed after use
the cached (old) multiplier — so the total reflects the old rate for all jobs, even
those that should have used the new rate. The symptom is a consistent factor discrepancy
between the expected total (computed from the new config) and the reported total.
Two cohorts are visible in per-job logs: `job_complete` events before and after the
config file modification timestamp carry different payload-to-result ratios. The
`config_load` log event shows only one load, at startup — no reload despite the change.

---

### FS-05 — Unbounded Run History (resource)

The run history list is a module-level list that is appended to after each run and
never cleared. In a single-invocation process this is harmless — the list has one
entry and the process exits. In a long-lived process it grows by one entry per run
indefinitely.

This is why it is a fault surface: the accumulation pattern looks like a deliberate
design decision (audit logging), not a bug. The list is never read by anything in
the current codebase, so its growth has no functional impact on individual runs — the
only symptom is memory growth over time. The scenario is constructed by providing
metrics artifacts showing memory growth across many runs in a process the ops team
has been keeping alive.

Observable when violated: process memory grows monotonically across runs. No errors.
Individual runs are correct. The ops team has been restarting the process weekly.

---

### FS-06 — Worker Throughput Variance (resource / temporal)

Workers have two processing paths: a fast path (the majority of jobs) and a slow path
(jobs with `processing_mode: extended`). The slow path is materially slower — it
includes a deliberate sleep to simulate heavy computation. With a thread pool of default
size (four threads), a batch skewed toward extended-mode jobs can saturate the pool
with slow workers, causing fast-path jobs to queue behind them.

This is why it is a fault surface: the slow path is a realistic production feature,
not an artificial construct. Real systems have jobs with variable processing time.
The hazard only manifests with certain input distributions, making it input-dependent
rather than code-dependent.

Quantitative characterisation: the fast path completes in ~5ms per job. The slow path
completes in ~500ms per job (100x slower). With a default pool of 4 threads and a
batch of 200 jobs where 80%+ are extended-mode, all 4 threads are occupied with slow-
path jobs for the majority of the run. Fast-path jobs that arrive in the queue during
this window wait for a thread to free up. Total runtime for such a batch is ~25 seconds
vs ~2 seconds for an equivalent all-fast-path batch — a 12x difference, clearly
anomalous against the ops team's expected runtime of under 5 seconds.

The scenario is constructed by providing a job file skewed toward extended-mode jobs,
or a config change that reclassifies a large category from standard to extended mode.

Observable when violated: batch runtime metric is 10–12x the fast-path baseline. Queue
depth stays elevated for the first 80% of the run, then drains rapidly at the end as
slow-path jobs complete and fast-path jobs clear quickly. Fast-path categories are
present but underrepresented in the report relative to their share of the input.
No errors. All workers are running throughout.

---

## Open Questions

*Resolved in revision 0.2. All decisions recorded below.*

1. **Sentinel drain protocol — resolved:** Use the re-enqueue pattern (each worker
forwards the sentinel to the next). This is the more realistic Python pattern for
thread pool drain, is slightly more fragile than per-worker poison pills, and makes
FS-02 misplacement more plausible and interesting. Decision: re-enqueue.

2. **Accumulator ownership — resolved:** Keep as a dispatcher attribute passed by
reference to worker closures. Module-level singleton would make shared-state too
obvious. The current design — dispatcher "owns" it, workers bypass the dispatcher
entirely — is the right level of deceptive. Decision: dispatcher attribute, closure
reference.

3. **Retry counter mutation — resolved:** Leave dormant. The in-place mutation of job
dicts is a realistic pattern and could become a future fault surface, but activating
it now adds noise without a clean corresponding scenario. Decision: dormant.

4. **Config cache thread safety — resolved:** Leave undocumented in the codebase.
Surfacing it in comments or docstrings would tip off candidates near the FS-04
injection site. Decision: dormant, no documentation.

5. **Report output path — resolved:** Out of scope. Dismissed.

6. **Code generation friction — new, for IR stage:** Code generation must introduce
navigational friction to prevent the architecture from being self-evident. Specifically:
module names must not map cleanly to subsystem names as labelled in this blueprint;
the main entrypoint must not obviously reveal the dispatcher/worker split; v1-era
comments in the dispatcher and worker must describe the sequential flow as if it still
applies, creating misleading inline documentation. This is a code generation constraint,
not an architectural one — record it in the IR as a generation directive.

---

## Critique History

### Critique 1 — 2026-06-19

**Overall assessment: revise**

**Blockers:**
- Missing logging schema. All six scenarios depend on structured log signals at well-defined
  points (job start/complete/retry, worker exit, reporter start/complete, config load, run
  history append). Without a specified schema, code generation cannot reliably produce the
  observability each scenario requires. A Logging Schema section must be added.

**Major:**
- FS-03 injection description is incoherent. "Partial write before re-queue" is ambiguous —
  if processing failed, what value was written? Revise to: worker writes result before
  checking return code; on failure, job is re-queued; retry processes and writes again,
  inflating the total.

**Minor:**
- FS-02: add explicit description of the misplaced-join-in-sentinel-loop variant (joins
  only some threads before reporter runs), as this is the most realistic and assessment-rich
  injection.
- FS-04: specify what a config multiplier shift looks like in output terms so the two-cohort
  symptom is concrete and detectable.
- FS-06: add quantitative characterisation of slow path duration and thread pool sizing
  to ensure starvation is reliably producible, not just slightly slower.
- Open Q1–Q5: resolve in blueprint before IR. Recommendations: re-enqueue sentinel (Q1),
  dispatcher-owned accumulator passed by reference (Q2), leave Q3/Q4 dormant, dismiss Q5.

### Revision 0.2 — 2026-06-19

All critique findings addressed:
- Added Logging Schema section (8 events with fields and scenario cross-references)
- FS-03 injection rewritten: write-before-check reorder, not partial-write-on-failure
- FS-02 expanded: misplaced-join-in-sentinel-loop variant described explicitly
- FS-04 symptom made concrete: multiplier cohort shift, factor discrepancy, two-cohort log pattern
- FS-05 scenario motivation strengthened: `--keep-alive` mode added as documented operational feature
- FS-06 quantified: fast path ~5ms, slow path ~500ms, 80%+ extended-mode batch produces 10–12x runtime
- Accumulator structure flattened to v1-style composite keys (realistic mid_life design)
- Open questions Q1–Q6 resolved
- Code generation friction requirement added as Open Question 6 / IR generation directive

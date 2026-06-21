# Critique Notes — prob-001-bp-01

*Level 1 artifact. Critique 1, 2026-06-19.*
*Verdict: revise*

---

## 1. Assessment Effectiveness

The system has genuine complexity in the right places. The dispatcher/worker/accumulator
triangle requires a candidate to navigate three components before forming a hypothesis,
and the v1→v2 history gives a realistic reason for the design debt. Enough surface area
exists across slow/fast paths and retry logic that a candidate cannot resolve the system
model in five minutes.

One forward concern: the subsystems are cleanly labelled in the blueprint. Code generation
must introduce navigational friction so the architecture isn't self-evident from module
names or entrypoints. The v1-era comments should mislead about data flow, not clarify it.

**Recommendation:** Add a note to Open Questions specifying that code generation must
introduce navigational friction — module names that don't map cleanly to subsystem names,
a main entrypoint that obscures the dispatcher/worker split, v1-era comments that
describe the sequential flow as if it still applies.

---

## 2. Fault Surface Quality

**FS-01 (Accumulator) — excellent.** The explanation of why individual GIL-protected
dict operations look safe but the read-modify-write sequence is not is exactly the right
level of subtlety. Clean surface, clean injection point.

**FS-02 (Reporter sync boundary) — good, undersells best variant.** The most assessment-
rich injection is not "join is missing" but "join is misplaced inside the sentinel drain
loop" — this joins only the thread whose sentinel happened to fire, leaving others
unjoined when the reporter runs. This looks like careful code (you are joining) but is
wrong in a subtle way. The blueprint should describe this variant explicitly.

**FS-03 (Retry deduplication) — incoherent injection description. Blocker-level.**
"Partial write before re-queue" does not hold up: if processing failed, what value was
written? The coherent version: worker writes result to accumulator *before* checking
whether the operation succeeded. On failure, the job is re-queued. The retry processes
the job again and writes a second result. Total is inflated by one job's value per
failed-then-retried job. Revise the injection description to this model.

**FS-04 (Config cache) — solid, needs concreteness.** The two-cohort symptom profile
is the right diagnostic signal but "output values shift" is vague. The config controls
a `multiplier` per category. After the config change, jobs in affected categories produce
totals computed with the new multiplier while the accumulator holds the old totals for
earlier jobs. The shift is a consistent factor difference between the first and second
cohort, visible in per-category averages, not just totals. Make this explicit.

**FS-05 (Run history) — correct, scenario motivation is thin.** The long-lived process
mode is described as an informal ops practice ("sometimes during maintenance windows").
This is not strong enough motivation for a scenario that depends on it. Consider adding
a `--keep-alive` or `--daemon` CLI flag as a documented operational mode. This makes
the memory growth scenario arise from a legitimate feature, not an undocumented ops hack.

**FS-06 (Throughput variance) — surface present, needs quantitative grounding.** With
4 threads and N% extended-mode jobs, does starvation actually produce a clearly anomalous
runtime (4–6x) or just a mild slowdown? This needs to be specified. The slow path must
be slow enough that the scenario is unmistakable, but not so slow that the system times
out before producing any output. Recommend: slow path takes ~10x the fast path duration,
and the scenario uses 80%+ extended-mode jobs.

---

## 3. Observability Coherence — Blocker

The blueprint specifies `structured` observability but does not define the log schema.
All six scenarios depend on specific log events being present at code generation time.
Without a schema, generation will produce ad-hoc logging that may not emit the right
signals for each scenario's diagnostic path.

Required log events (minimum):

| Event | Key Fields |
|---|---|
| job_start | job_id, category, thread_id, timestamp |
| job_complete | job_id, category, result_value, processing_path, timestamp |
| job_retry | job_id, retry_count, reason, timestamp |
| worker_exit | thread_id, jobs_processed, timestamp |
| reporter_start | timestamp |
| reporter_complete | job_count, total, failed_count, discrepancy, timestamp |
| config_load | path, load_timestamp, category_count |
| run_history_append | run_id, job_count, runtime_seconds |

`reporter_start` is critical for FS-02: candidates must be able to compare its timestamp
against `worker_exit` timestamps to prove the reporter ran before workers finished.

`config_load` is critical for FS-04: candidates must be able to compare its timestamp
against job processing timestamps to identify the cohort boundary.

**This must be added to the blueprint as a Logging Schema section before IR compilation.**

---

## 4. Realism

**System motivation:** Credible. stdlib-only internal batch tool with a sequential v1
and threaded v2 is a real pattern. No concerns.

**Accumulator structure:** Too clean. A nested dict `{"category": {"total": N, "failed": M}}`
looks like it was designed with the assessment in mind. A v1 accumulator from a
mixed-team mid_life codebase would more likely be a flat dict or have inconsistent
structure across categories (some flat, some nested, a comment explaining the v1 approach).
Flatten or make inconsistent during code generation.

**System naming:** "Batchwork" is a clean name. Real internal tools tend to have less
polished names. Minor, acceptable to leave.

---

## 5. Candidate Experience

The primary entry point for scen-001 through scen-004 is the reporter summary log line
comparing `job_count` and `total`. This is a good anchor — specific, observable,
requires no code reading to notice. The incident description should be framed as "report
totals look wrong" to direct candidates to this signal without telling them where to look.

Intended ambiguity between scen-001 and scen-002: both produce `total` < `job_count`.
The distinction requires the candidate to check log timestamps (FS-02) vs run multiple
times and observe drift (FS-01). This is a good assessment property — the same symptom
profile tests different capabilities depending on which scenario is active. Note this
explicitly in the blueprint as intended design, not a flaw.

scen-005 (memory growth) has a fundamentally different entry point — no report anomaly,
just an ops complaint about process memory and weekly restarts. This scenario requires
different packaging and should be flagged in the scenario spec as requiring a different
incident framing than the others.

---

## 6. Open Questions — Recommended Resolutions

**Q1 — Sentinel protocol:** Use re-enqueue pattern. It is the more realistic Python
pattern, slightly more fragile, and produces a subtler FS-02 injection when misused.

**Q2 — Accumulator ownership:** Keep as dispatcher attribute passed by reference to
workers. Module-level singleton would make shared-state too obvious.

**Q3 — Retry counter mutation:** Leave dormant. Do not exploit as a fault surface now.

**Q4 — Config cache thread safety:** Leave undocumented. Surfacing it risks tipping
off candidates via code comments.

**Q5 — Report output path race:** Dismiss. Out of scope.

---

## Verdict: revise

The blueprint is architecturally sound and all six fault surfaces from the spec are
present. Two changes are required before IR compilation can proceed: (1) add a Logging
Schema section defining the minimum structured log events required across all scenarios —
this is a blocker because without it code generation cannot produce the observability
the scenarios depend on; (2) revise the FS-03 injection description to the coherent
model (write-before-check, not partial-write-on-failure). Four minor issues (FS-02
variant description, FS-04 concreteness, FS-05 scenario motivation, FS-06 quantitative
grounding) should be addressed in the same revision pass.

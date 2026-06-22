# Incident: Category Breakdown Mismatch — Invoices Line Item

**Severity:** P2
**Opened:** 2026-06-22 06:14 UTC
**Reported by:** Finance Operations (manual reconciliation)
**Run ID:** run-1750636800

---

## Alert

> [finance-reconciliation] NightProc run-1750636800 category breakdown does not match
> ledger. "Invoices" department jobs are missing from report. "invoices" count is 30,
> expected 20. Batch marked complete. discrepancy: 0.

---

## What Finance sees

The nightly batch report (`report.json`) is missing the `Invoices` category entirely.
Finance Operations runs two separate job pipelines — lowercase `invoices` (standard
billing) and `Invoices` (a legacy capitalisation used by an upstream ERP export since
Q3 2024). Both pipelines submitted jobs last night. Only `invoices` appears in the
report.

The `invoices` line item shows a count of **30** and a total value of **36,645**.
Finance expected:
- `invoices`: count 20, total value 30,075
- `Invoices`: count 10, total value 6,570

The top-level `discrepancy` field in the report is **0**. No error alerts fired.
All 30 jobs appear to have processed successfully.

This pattern has appeared once before (2026-05-08) and was attributed to a one-off
input error. Finance are no longer confident it was a one-off.

---

## Reproduction

The batch was invoked as:

```bash
python run_batch.py jobs/collision_jobs.json --threads 4
```

Logs are written to `logs/nightproc.log`.

---

## Available signals

| Signal | Location |
|---|---|
| Structured run log | `logs/nightproc.log` |
| Disputed report | `report.json` |
| Job input | `jobs/collision_jobs.json` |
| Source | `nightproc/` |

---

## Notes

- Finance confirmed both `invoices` and `Invoices` jobs were present in the input
  file submitted last night — `collision_jobs.json` is attached above.
- The report `discrepancy` field is 0. All 30 submitted jobs are accounted for in
  the count — they are not missing, they are misattributed.
- Re-running the batch produces the same result every time. This is not a race
  condition.
- The `Invoices` category uses different processing parameters from `invoices`;
  the multipliers are not the same. The merged total (36,645) is consistent with
  neither category processed uniformly.

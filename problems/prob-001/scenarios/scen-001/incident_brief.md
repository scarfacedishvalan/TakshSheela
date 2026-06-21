---
scenario_id: scen-001
artifact_type: incident_brief
audience: candidate
---

# Incident Report — nightproc batch run

The nightly batch completed in 4.2 seconds with no exceptions and no error-level log
output. All 200 jobs emitted a `job_complete` or `job_failed` event.

The generated report shows `total_processed: 193` and `discrepancy: 7`. The system
defines discrepancy as `job_count − total_processed − failed_count`. On a correct run,
discrepancy is always zero. No failed jobs were recorded in this run.

The run has been reproduced three times. The discrepancy value varies (observed: 5, 7, 9)
but is never zero.

**Your task:** identify the root cause and propose a fix. You have access to the source
code, the run logs, and the generated report.

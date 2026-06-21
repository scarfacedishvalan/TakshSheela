---
artifact_id: prob-001-fsm-01
spec_id: prob-001
blueprint_id: ""        # populated after blueprint is approved
version: "0.1"
status: pending         # pending | draft | approved
---

# Fault Surface Map: prob-001

*Level 2 artifact. Produced after blueprint approval by running the fault brainstorm
and extraction stages. Maps each declared spec fault surface to its concrete location
in the approved architecture, and enumerates viable injection types.*

*Pending blueprint generation and approval.*

---

## Coverage Checklist

Each surface declared in spec.md must be fulfilled here before scenarios can be created.

| Surface ID | Spec Declaration         | Blueprint Location | Status  |
|------------|--------------------------|-------------------|---------|
| FS-01      | Shared mutable accumulator | —               | pending |
| FS-02      | Reporter sync boundary    | —                | pending |
| FS-03      | Retry/dedup interaction   | —                | pending |
| FS-04      | Startup config cache      | —                | pending |
| FS-05      | Unbounded run history     | —                | pending |
| FS-06      | Worker throughput variance | —               | pending |

---

## Surface Analyses

*One section per surface. Populated after blueprint approval.*

### FS-01 — Shared Mutable Accumulator

**Blueprint location:** —
**Concrete structure:** —
**Why it looks safe:** —
**Viable injection types:** —
**Observable when violated:** —

---

### FS-02 — Reporter Synchronization Boundary

**Blueprint location:** —
**Concrete structure:** —
**Why it looks safe:** —
**Viable injection types:** —
**Observable when violated:** —

---

### FS-03 — Retry and Deduplication Interaction

**Blueprint location:** —
**Concrete structure:** —
**Why it looks safe:** —
**Viable injection types:** —
**Observable when violated:** —

---

### FS-04 — Startup Config Cache

**Blueprint location:** —
**Concrete structure:** —
**Why it looks safe:** —
**Viable injection types:** —
**Observable when violated:** —

---

### FS-05 — Unbounded Run History

**Blueprint location:** —
**Concrete structure:** —
**Why it looks safe:** —
**Viable injection types:** —
**Observable when violated:** —

---

### FS-06 — Worker Throughput Variance

**Blueprint location:** —
**Concrete structure:** —
**Why it looks safe:** —
**Viable injection types:** —
**Observable when violated:** —

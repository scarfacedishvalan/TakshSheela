---
blueprint_id: ""     # e.g. prob-001-bp-01
spec_id: ""
version: "0.1"
status: draft        # draft | critique_pending | revised | approved
---

# Blueprint: {blueprint_id}

*This is a Level 2 artifact. Structured sections are required by the compiler.
Prose is expected and encouraged within each section. Do not reduce to bullet lists
where reasoning adds value.*

---

## System Overview

*Describe the system in plain language. What does it do? What is its operational context?
What does a normal run look like from start to finish?*

---

## Subsystems

*One subsection per subsystem. Each must cover: what it does, what it owns, and how it
interacts with the rest of the system. Prose + optional bullet lists.*

### {SubsystemName}

**Responsibility:**

**Runtime role:** *(process / thread / coroutine / library / config)*

**State owned:**

**Key interfaces:**

---

## Project Structure

*Repository layout. Include a directory tree with brief inline comments explaining
each file's role. Module names should reflect the realistic naming of the implied
team and codebase maturity — not the clean subsystem names from this blueprint.
Note any intentional navigational friction below the tree.*

```
{repo_name}/
├── {entrypoint}.py
├── {package}/
│   ├── __init__.py
│   ├── ...
│   └── util/
├── config/
├── tests/
└── README.md
```

### Navigational Notes for Code Generation

*Describe any intentional friction: module names that mislead, comments that describe
a superseded design, entrypoints that obscure the architecture.*

---

## Dependency Graph

*Describe how subsystems depend on each other. Prose is preferred over edge lists —
explain the nature of each dependency, not just its existence.*

*A simple ASCII diagram is encouraged but not required.*

---

## Runtime Lifecycle

*Describe startup and shutdown sequence. What initializes first and why? What happens
during graceful shutdown? Are there ordering constraints that could be fault surfaces?*

---

## Data Model

*Describe the key data entities flowing through the system. What are they, who owns
them, and how do they change over time?*

---

## System Invariants

*List the correctness invariants the system is supposed to maintain. For each invariant,
explain why it matters and what happens when it is violated. These drive fault ideation.*

---

## Fault Surfaces

*Identify areas of the design that are structurally prone to faults. These are not faults —
they are locations where faults could plausibly be injected. Explain why each surface
is interesting from an assessment perspective.*

### {ComponentName} — {SurfaceDescription}

**Why this is a fault surface:**

**Mechanism families likely applicable:**

**Observability when violated:**

---

## Open Questions

*Anything unresolved in this blueprint that should be addressed before IR compilation.*

---

## Critique History

*Record of critique passes. Append each critique cycle here rather than overwriting.*

### Critique {n} — {date}

**Overall assessment:** *(pass / revise / reject)*

**Issues:**

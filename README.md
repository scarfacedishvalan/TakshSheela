# TakshSheela

TakshSheela is a synthetic software debugging assessment generation platform.

Its purpose is to generate realistic synthetic Python codebases and reusable debugging
scenarios for evaluating software engineering capability across multiple dimensions:
debugging discipline, code navigation, systems thinking, concurrency reasoning, and
root-cause analysis.

The platform produces systems that feel indistinguishable from real production codebases
while remaining configurable and reusable across many assessment scenarios.

---

## Core Goal

Generate realistic debugging assessments that differentiate between:

- Weak engineers
- Average engineers
- Strong engineers
- Senior engineers

Optimised for: realism, scenario scalability, difficulty calibration, and
anti-coaching robustness.

---

## Generation Pipeline

TakshSheela treats assessment generation as a compiler pipeline. Each stage transforms
artifacts into more concrete artifacts. The pipeline for one problem looks like:

```
spec → blueprint → fault surface map → canonical codebase
                          ↓                     ↓
                    [scenario spec] → fault injection → assessment
```

A **canonical codebase** is always correct — it contains no active faults. It supports
multiple scenario variants. Each scenario injects exactly one fault into a copy of the
canonical codebase.

See [ARCHITECTURE.md](ARCHITECTURE.md) for a detailed description of each stage.

## Scenario Injection

Fault injection is split between agents (reasoning) and deterministic tools (execution).

```
Orchestrator agent
  └─► Patch Injection agent   (edits one file in a scratch git repo)
  └─► git diff                (captures the diff — no LLM writes diff syntax)
  └─► patch.diff saved

User runs deterministic tools:
  seed_canonical.py           (one-time per problem — seeds workspace git repo)
  apply_patch.py              (6 pre-flight checks + git apply --check + commit)
  validate_patch.py           (syntax, import, smoke run)
  run_scenario.py             (repeated fault expression check)
```

Candidate workspaces live outside this repository at `<workspace_root>/<problem_id>/`
(configured in `tools/config.json`). Each problem is an independent git repo. Each
scenario is a branch with the canonical state as the first commit and the mutation as
a second commit with a realistic message. No evidence of injection remains in the
working tree.

---

## Repository Structure

```
TakshSheela/
│
├── problems/                   Problem definitions
│   ├── manifest.yaml           Index of all problems and their pipeline status
│   └── prob-001/               One problem per directory
│       ├── ideation.md         Level 1 — free-form system character sketch
│       ├── spec.md             Level 2 — structured spec with frontmatter
│       ├── blueprint.md        Level 2 — architecture artifact; drives code generation
│       ├── fault_surface_map.md  Level 2 — concrete injection targets per fault surface
│       └── scenarios/
│           └── scen-001/
│               ├── scenario_spec.md    Fault definition and injection instructions
│               └── incident_brief.md  Candidate-facing problem statement
│
├── codes/                      Generated codebases
│   └── prob-001/
│       └── canonical/          Correct implementation; no active faults
│
├── taxonomy/                   Shared classification vocabulary
│   ├── failure_mechanisms.yaml   6-family fault taxonomy (coordination, state, …)
│   ├── capability_model.yaml     6-axis candidate capability model
│   ├── codebase_genome.yaml      Axes for describing codebase character
│   └── observability_model.yaml  Signal types available in scenarios
│
├── schemas/                    JSON Schema for Level 3 artifacts
│   ├── fault_scenario.schema.json
│   └── lineage.schema.json
│
├── prompts/                    LLM prompt templates per pipeline stage
│   ├── blueprint_generation/
│   ├── critique/
│   ├── fault_ideation/
│   └── scenario_packaging/
│
├── templates/                  Artifact templates
│   ├── spec_template.md
│   ├── blueprint_template.md
│   └── fault_brainstorm_template.md
│
├── concepts/                   Reference material on fault families
│   ├── concurrency/
│   ├── state_management/
│   └── resource_lifecycle/
│
├── ARCHITECTURE.md             Pipeline stage definitions and artifact contracts
├── DECISIONS.md                Architecture decision records (ADR-001 – ADR-005)
└── ROADMAP.md                  Phase-by-phase progress tracker
```

---

## Artifact Fidelity Model

Artifacts are produced at three fidelity levels depending on how much structure is
appropriate for the stage:

| Level | Format | Used for |
|---|---|---|
| 1 — Soft | Free-form markdown | Ideation, brainstorm, fault divergence |
| 2 — Semi-structured | Markdown with YAML frontmatter | Spec, blueprint, scenario spec, surface map |
| 3 — Hard | Schema-validated YAML / JSON | Fault candidates, lineage hashes |

Early stages are intentionally unstructured. Schema validation is only applied where
machine consumption requires it.

---

## Major Concepts

**Spec** — defines what kind of system to generate and which fault families it must
architecturally support. Fault surfaces are declared here as requirements so that
the blueprint cannot produce a system where injection is architecturally impossible.

**Blueprint** — authoritative architecture document. Defines subsystems, project
structure, data model, logging schema, and fault surface locations. Drives code
generation directly. Must pass a critique review before the codebase is generated.

**Canonical Codebase** — a correct, runnable Python codebase generated from the
blueprint. Contains fault surfaces as latent structural characteristics, never as
active bugs. Shared across all scenarios for the same problem.

**Fault Surface Map** — maps each declared fault surface to its concrete module,
function, and injection type in the generated codebase.

**Scenario Spec** — selects one fault surface, specifies the injection, and defines
difficulty calibration across candidate levels.

**Incident Brief** — candidate-facing problem statement in operational voice. States
a concrete observable symptom without naming the fault family or location.

**Assessment** — a fault-injected codebase variant paired with synthesized observability
artifacts (logs, metrics, report output) and success criteria.

---

## Repository Philosophy

LLMs are used for architecture reasoning, fault ideation, and scenario generation.
Deterministic software handles schema validation, artifact lineage, and selective rebuild.

Selective rebuild is tracked via `lineage.yaml` per problem using content hashes.
Changing a spec invalidates the blueprint and everything downstream. Changing only a
scenario spec invalidates only that scenario's assessment.

---

## Current Status

See [ROADMAP.md](ROADMAP.md) for phase-by-phase progress.

- `prob-001` (nightproc) — canonical codebase generated, 17 tests passing
- `scen-001` through `scen-006` — scenario specs and incident briefs written; fault injection pending

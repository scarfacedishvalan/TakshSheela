# Roadmap

---

## Phase 1 — Knowledge Architecture ✓

Goals:

* taxonomy design
* concept ontology
* artifact contracts
* pipeline architecture

Deliverables:

* `taxonomy/` — failure mechanisms, capability model, codebase genome, observability model
* `concepts/` — concurrency, state management, resource lifecycle
* `templates/` — spec, blueprint, fault brainstorm templates
* `schemas/` — fault_scenario, lineage (hard artifact schemas)
* `ARCHITECTURE.md`, `DECISIONS.md` — ADR-001 through ADR-005

---

## Phase 2 — Blueprint Generation ✓ (prob-001)

Goals:

* problem ideation
* spec authoring
* blueprint generation
* blueprint critique loop

Deliverables:

* `problems/prob-001/ideation.md`
* `problems/prob-001/spec.md`
* `problems/prob-001/blueprint.md` (approved, v0.2)
* `prompts/blueprint_generation/`, `prompts/critique/`

---

## Phase 3 — Fault Surface Mapping

Goals:

* fault brainstorm (divergent ideation from approved blueprint)
* fault extraction (structured candidates from brainstorm)
* fault surface map (concrete injection targets per surface)

Deliverables:

* `problems/prob-001/fault_brainstorm.md`
* `problems/prob-001/fault_surface_map.md` (approved)
* `prompts/fault_ideation/v1_fault_brainstorm.md`
* `prompts/fault_ideation/v2_fault_extraction.md`

---

## Phase 4 — Canonical Codebase Generation

Goals:

* generate the correct canonical Python repository from the approved blueprint
* validate project structure, module naming, logging schema, data model
* post-generation review: confirm all fault surfaces are present and injectable

Deliverables:

* `problems/prob-001/codebase/` — the `nightproc` repository
* `problems/prob-001/lineage.yaml` — hash chain initialised

---

## Phase 5 — Scenario Injection

Goals:

* per-scenario fault injection from canonical codebase
* observability synthesis (logs, metrics, alerts per scenario)
* assessment packaging (incident ticket, starting context, success criteria)

Deliverables:

* `problems/prob-001/scenarios/scen-00{1-6}/fault_scenario.yaml`
* `problems/prob-001/scenarios/scen-00{1-6}/observability/`
* `problems/prob-001/scenarios/scen-00{1-6}/assessment_package.yaml`

---

## Phase 6 — Assessment Validation

Goals:

* expert benchmarking against each scenario
* psychometric calibration (difficulty scores validated against target levels)
* scenario scoring rubrics
* anti-coaching review (check for pattern-matchable tells)

Deliverables:

* validated scenario portfolio for prob-001
* scoring rubrics per scenario
* second problem (prob-002) spec drafted from lessons learned

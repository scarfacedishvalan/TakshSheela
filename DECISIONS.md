# Architectural Decisions

This document records major architectural decisions.

---

## Decision Template

### Decision ID

### Context

### Options Considered

### Decision

### Tradeoffs

---

## ADR-001

### Context

Need scalable architecture for synthetic debugging assessment generation.

### Options Considered

* direct prompt generation
* artifact pipeline

### Decision

Adopt artifact-driven generation pipeline.

### Tradeoffs

Higher infrastructure complexity but improved reproducibility and selective rebuild.

---

## ADR-002

### Context

Need fault classification system.

### Options Considered

* flat bug taxonomy
* mechanism-based taxonomy

### Decision

Use mechanism-based taxonomy.

### Tradeoffs

Requires richer ontology but improves composability.

---

## ADR-003

### Context

Early schema design applied strict JSON Schema validation to spec and blueprint artifacts.
These are creative/ideation-stage artifacts authored by humans and LLMs, not machine-compiled outputs.
Strict schemas at this stage suppressed reasoning quality and forced premature structural commitment.

### Options Considered

* Keep strict schemas across all stages
* Mixed-fidelity artifact model: soft → semi-structured → hard by pipeline stage

### Decision

Adopt mixed-fidelity artifact model with three levels:

* Level 1 — Soft: free-form markdown (ideation.md, fault_brainstorm.md, critique_notes.md)
* Level 2 — Semi-structured: markdown with required frontmatter + section headings (spec.md, blueprint.md)
* Level 3 — Hard: schema-validated YAML/JSON (ir.yaml, fault_scenario.yaml, lineage.yaml)

Schema validation applies only at Level 3. The Level 2 → Level 3 boundary (blueprint → IR) is the
deterministic enforcement gate.

### Tradeoffs

Gains: richer LLM reasoning at creative stages, easier artifact evolution, better assessment quality.
Costs: blueprint → IR compilation must parse markdown instead of YAML; spec has no machine-enforceable
gate before generation (mitigated by critique-loop validation prompt).

---

## ADR-005

### Context

The IR stage was designed to compile the blueprint into a machine-readable artifact that
would drive code generation with reduced ambiguity. As the blueprint evolved to include a
Project Structure section (exact module layout), a Logging Schema section (exact event
fields), explicit fault surface injection descriptions, and concrete data model field names,
the blueprint absorbed most of the information the IR was meant to encode. The IR had become
a mechanical YAML re-transcription of information already present in the blueprint.

### Options Considered

* Keep IR as a strict compilation stage between blueprint and code generation
* Remove IR; generate code directly from the approved blueprint
* Keep IR but simplify it to only encode lineage and injection targets

### Decision

Remove the IR stage entirely. Code generation takes the approved blueprint directly as
input. Lineage tracking is handled by `lineage.schema.json` (hashes only, no structural
content). Fault injection target resolution is handled by `fault_surface_map.md`.

### Tradeoffs

Gains: one fewer pipeline stage; no artifact to keep in sync with blueprint; blueprint
is the single source of truth for code generation; simpler selective rebuild.

Costs: code generation is a direct LLM call on a long markdown document with no compiled
intermediate to catch structural drift; if the generated codebase diverges from the
blueprint's module layout or naming, there is no compiled artifact to detect it — only
a post-generation review pass.

---

## ADR-004

### Context

Initial prob-001 spec conflated three distinct concepts: canonical problem definition,
fault surface declaration, and scenario-specific fault injection. The spec contained
Python pseudocode for a specific race condition and named a single fault family. This
made the canonical codebase a single-scenario artifact with no reuse path.

### Options Considered

* Keep scenario-centric model: one codebase per bug
* Canonical codebase model: one codebase, many scenarios via fault injection

### Decision

Adopt canonical codebase model with explicit separation of:

1. Problem spec — defines the system and declares fault surfaces as architectural requirements
2. Blueprint — designs the correct canonical system, proves each fault surface is present
3. Fault surface map — analyzes concrete injection points after blueprint approval
4. Scenario spec — selects one surface and specifies assessment parameters per scenario
5. Fault injection — produces one faulty codebase variant per scenario

Fault surfaces are declared in the spec to constrain blueprint generation. The blueprint
must architecturally satisfy every declared surface. This prevents generating a canonical
codebase where desired fault surfaces are impossible to inject without redesign.

The canonical codebase is always correct. It never contains an active fault.

### Tradeoffs

Gains: each canonical codebase yields a scenario portfolio (6+ scenarios for prob-001);
blueprint generation is constrained to produce architecturally injectable systems;
scenarios are independently injectable with no cross-contamination.

Costs: more artifacts per problem; fault surface map adds a pipeline stage; scenario
specs require their own ideation and quality review.

---

## ADR-006

### Context

The original patch injection agent handled the full scenario injection workflow in a
single agent: scenario understanding, code inspection, mutation planning, workspace
materialization, patch application, validation, retry logic, and final reporting.
This made the agent overloaded and difficult to reason about — reasoning-heavy steps
(mutation design) and execution-heavy steps (tool invocation, retry loops) were
interleaved with no clean boundaries.

A second agent (mutation.agent.md) was introduced to cover Steps 1–3 (reasoning only)
but duplicated the same instructions as the original agent without eliminating them.
No orchestrator existed to coordinate the two agents or manage handoffs.

### Options Considered

* Refactor single agent into clearly separated sections with stronger internal headers
* Introduce a true multi-agent runtime with programmatic invocation
* Orchestrator + specialized subagents with protocol switching for VSCode compatibility

### Decision

Adopt orchestrator + specialized subagents with protocol switching.

Four agents, each with a single responsibility:

1. **Orchestrator** — workflow state, approval gates, handoff emission, retry decisions
2. **Patch Injection Agent** — reasoning only: scenario understanding, code inspection, mutation planning, patch generation
3. **Mutation Executor Agent** — execution only: workspace copy, apply_patch.py, validate_patch.py, failure classification
4. **Patch Validator Agent** — quality evaluation only: candidate perspective, solvability, capability coverage

Because VSCode custom agents do not support programmatic subagent invocation, the
orchestrator uses a protocol-switching model: it emits structured HANDOFF blocks that
instruct the user to load the appropriate agent, and resumes when the agent returns a
structured RETURN block.

The redundant mutation.agent.md was deleted — it is fully superseded by the refactored
patch_injection.agent.md.

### Tradeoffs

Gains: each agent has a single clear responsibility; reasoning and execution are never
interleaved; the orchestrator owns all retry logic so no agent needs to decide whether
to regenerate its own output; the protocol-switching model works within VSCode
constraints without requiring a runtime framework.

Costs: each scenario injection requires the user to manually switch agent context at
phase boundaries; the orchestrator cannot enforce handoffs programmatically — the
workflow relies on the user following the emitted HANDOFF instructions.

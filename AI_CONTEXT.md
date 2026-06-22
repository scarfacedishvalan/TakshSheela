# AI Context

This file contains authoritative project intent for AI coding assistants.

All AI assistants working on TakshSheela must treat this document as high-priority context.

If code or generated artifacts appear to conflict with this document, this document takes precedence unless explicitly overridden by the human operator.

---

# Project Intent

TakshSheela is not a generic interview platform.

It is a system for generating realistic debugging assessments based on synthetic software systems.

The core objective is to evaluate software engineering capability through debugging and incident investigation.

---

# Primary Optimization Targets

Optimize for:

1. realism
2. assessment quality
3. fault richness
4. scenario diversity
5. maintainability
6. anti-coaching robustness

Do NOT optimize for:

* academic elegance
* perfect code quality
* excessive abstraction
* framework sophistication

Synthetic codebases should feel production-realistic.

Messiness is acceptable when realistic.

---

# Core Design Principles

## Principle 1 — Artifacts Are Source of Truth

Agents must communicate via structured artifacts.

Agents must NOT communicate via raw prompt prose.

Examples of valid artifacts:

* spec
* blueprint
* scenario metadata
* patch artifacts (patch.diff, patch_meta.json)

---

## Principle 2 — LLMs Reason, Deterministic Systems Enforce

LLMs are responsible for:

* reasoning
* planning
* critique
* ideation

Deterministic software is responsible for:

* schema enforcement
* orchestration
* validation
* lineage tracking

Never rely solely on LLM outputs for authoritative structural correctness.

---

## Principle 3 — Optimize for Assessment Quality

The product is not code generation itself.

The product is high-quality debugging assessment.

Every architectural decision should be evaluated against assessment quality.

---

## Principle 4 — Framework Neutrality

Avoid excessive dependence on web frameworks.

Prefer framework-neutral Python architectures.

Assessments should test engineering fundamentals, not framework familiarity.

---

## Principle 5 — Intuitive Frontline Entry

Every generated codebase must expose intuitive front-line entrypoints.

Examples:

* CLI runner
* service main
* incident replay script
* operational dashboard hooks

Candidates should be able to start interacting quickly.

---

# Taxonomy Model

TakshSheela uses a 5-axis generation model.

1. Codebase Genome
2. Capability Model
3. Failure Mechanisms
4. Observability Model
5. Scenario Packaging

---

# Failure Mechanism Families

Current major fault families:

* semantic
* state
* temporal
* coordination
* resource
* contract

These classify causal failure mechanisms rather than surface symptoms.

---

# Guidance for AI Assistants

Before major changes:

1. Explain affected artifacts
2. Identify dependency impact
3. Propose implementation plan
4. Wait for approval

For major architectural changes:
Always discuss tradeoffs before editing.

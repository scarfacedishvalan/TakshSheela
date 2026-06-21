# TakshSheela

TakshSheela is a synthetic software debugging assessment generation platform.

Its purpose is to generate realistic synthetic Python codebases and reusable debugging scenarios for evaluating software engineering capability across multiple dimensions, including debugging discipline, code navigation, systems thinking, concurrency reasoning, and root-cause analysis.

The project aims to produce software systems that feel indistinguishable from real production codebases while remaining configurable, scalable, and reusable across assessment scenarios.

---

## Core Goal

Generate realistic debugging assessments that can differentiate between:

* weak engineers
* average engineers
* strong engineers
* senior engineers

The platform must optimize for:

* realism
* diversity
* scenario scalability
* difficulty calibration
* psychometric validity
* anti-coaching robustness

---

## Generation Pipeline

TakshSheela uses an artifact-driven generation pipeline:

```text
spec → blueprint → IR → codebase → fault scenario → assessment
```

Artifacts are the source of truth across pipeline stages.

---

## Repository Philosophy

TakshSheela treats generation as a compiler problem.

LLMs are used for:

* architecture reasoning
* planning
* fault ideation
* scenario generation

Deterministic software is used for:

* schema validation
* orchestration
* artifact lineage
* selective rebuild
* dependency management

---

## Major Concepts

### Canonical Codebase

A reusable synthetic software system serving as a base for multiple debugging scenarios.

### Blueprint

A structured architecture specification describing system design before code generation.

### IR

Intermediate representation compiled from blueprint into machine-readable structured artifacts.

### Scenario

A fault-injected assessment instance derived from a canonical codebase.

---

## Current Status

Phase 1:

* taxonomy design
* artifact contracts
* generation architecture

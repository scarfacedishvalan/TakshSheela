---
spec_id: ""          # matches problem folder name, e.g. prob-001
version: "0.1"
status: draft        # draft | ready | superseded

# Identity fields — these are parsed by the pipeline compiler.
# Keep values from the allowed lists below.

domain: ""
# allowed: data_pipeline | api_service | background_worker | cli_tool
#          event_driven_system | distributed_cache | scheduler

difficulty: null
# allowed: 1 (weak) | 2 | 3 (average) | 4 | 5 (senior)

fault_family: ""
# allowed: semantic | state | temporal | coordination | resource | contract
# Note: subtype is chosen during fault ideation, not here.

observability_level: ""
# allowed: none | basic | structured | full

genome_scale: ""
# allowed: small | medium | large

genome_maturity: ""
# allowed: greenfield | mid_life | legacy

genome_team_style: ""
# allowed: disciplined | mixed | cowboy
---

# Spec: {spec_id}

## Intent

*What kind of debugging scenario do you want to create? What should it feel like to the candidate?*

Write freely. This is the most important section. Describe the experience, not just the parameters.

---

## System Concept

*Sketch the kind of system you have in mind. What does it do? Who operates it? What does normal operation look like?*

---

## Capability Focus

*Which engineering capabilities should this scenario stress? Why? What should differentiate a strong candidate from an average one here?*

Refer to `taxonomy/capability_model.yaml` for the full list.

---

## Fault Direction

*Do you have any intuition about the kind of fault you want? What should it feel like — is the bug subtle, is it intermittent, does it require reading code vs reading logs?*

Do not over-specify. This is a direction, not a constraint. The fault ideation stage will generate candidates.

---

## Constraints and Exclusions

*Anything this scenario must not do? Any domains, patterns, or fault types to avoid?*

---

## Notes

*Anything else relevant. Open questions. Inspirations.*

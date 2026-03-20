# RAMP Engineering Reference & Data Schema — Gap Assessment

## Documents Reviewed

### System Design References (Earlier)
1. **1-6. State Engine (V1)** — State creation, lifecycle, transitions, severity, confidence
2. **1-7. Baseline & Savings Method (V1)** — Baseline types, freeze, deviation, verification
3. **1-8. Priority Engine (V1)** — Priority formula, bands, types, decision guardrails
4. **1-9. MVP Handoff Pack (V1)** — Core capabilities, architecture, acceptance criteria
5. **1-3. Lens Contract Specification (V1)** — Field-level exposure rules per lens

### Engineering & Data Schema References (New)
6. **1-11. Engineering Blueprint V3** — Module structure, navigation zones, screen inventory
7. **1-12. Developer Spec V2** — Architecture layers, API design, integration requirements
8. **1-13. Command Centre Specification** — Functional modules, data model, relationships
9. **1-14. Wireframe Pack & ERD** — Screen wireframes, entity relationships

---

## Executive Summary

The current MVP implementation is **well-aligned** with the core system design principles (State Engine, Baseline, Priority, Lens Contract). The new Engineering Blueprint documents describe a broader platform vision that includes modules beyond the current MVP scope (Assessments, LEAP Programme, Partner Orchestration, etc.).

**Key findings:**
- ✅ Core loop is correctly implemented: Signal → Baseline → State → Priority → Action → Outcome → Learning
- ✅ Data schema relationships align with ERD
- ⚠️ Some lens contract violations need correction (raw score exposure)
- ⚠️ State transitions not explicitly tracked
- ℹ️ Many Blueprint modules are future scope (Assessments, LEAP, Partner Operations)

---

## Alignment Analysis

### ✅ ALIGNED — No Action Required

| Reference Spec | Current Implementation | Status |
|----------------|------------------------|--------|
| **Data Model: Organisation → Site → System → Asset** | `ramp_organisations` → `ramp_sites` → `ramp_systems` → `ramp_assets` | ✅ |
| **State families: OPERATIONAL, ENERGY, MAINTENANCE, PRODUCTION** | `state_family` field | ✅ |
| **State types: DRIFT, SPIKE, DEGRADATION** | `state_type` field | ✅ |
| **Baseline freeze on intervention** | `frozen_at`, `frozen_for_intervention_id` | ✅ |
| **Baseline confidence scoring** | `confidence`, `confidence_band` | ✅ |
| **Context segmentation** | `context_signature` JSONB | ✅ |
| **State severity with bands** | `severity_score`, `severity_band` | ✅ |
| **State confidence with bands** | `confidence`, `confidence_band` | ✅ |
| **Priority bands: CRITICAL, HIGH, MEDIUM, LOW** | `priority_band` | ✅ |
| **Priority drivers (explainability)** | `drivers` JSONB array | ✅ |
| **Economic impact (VaR/VR)** | `economic_impact` JSONB | ✅ |
| **Outcome statuses: PENDING, VERIFIED, INSUFFICIENT_DATA** | `status` field | ✅ |
| **Savings calculated against frozen baseline** | Verification scheduler | ✅ |
| **Event backbone for state changes** | `ramp_events` table | ✅ |
| **HOW/WHERE lens separation** | `/api/how/*`, `/api/where/*` routes | ✅ |
| **Intervention linked to state** | `state_id` FK | ✅ |
| **Outcome linked to intervention** | `intervention_id` FK | ✅ |
| **Learning tracks recurrence & effectiveness** | `ramp_learning` table | ✅ |

---

### ⚠️ GAPS — Require Correction

#### 1. ~~Lens Contract: Raw Field Exposure~~ ✅ FIXED (2026-03-20)

**Fixed:** HOW lens now properly suppresses raw scores and exposes only bands/labels:
- `confidence` raw → `confidence_label` (strong/moderate/low/insufficient)
- `priority_score` → `priority_band` only
- `severity_score` → `severity_band` only
- `baseline_value`, `score_components`, `actual_value` → suppressed

**Implementation:**
- Created `/app/backend/ramp/lenses/helpers.py` with `confidence_to_label()` mapping
- Updated `HOWLens` to use states for confidence
- Updated `/api/how/priorities` to fetch states
- Updated `/api/system/value-summary` to use confidence_label
- Updated `/api/system/demo/first-five-minutes` to use confidence_label

---

#### 2. ~~State Transitions (Priority: MEDIUM)~~ ✅ FIXED (2026-03-20)

**Reference (State Engine §8):**
> States must transition — not just stop/start.
> `current_state → next_state`
> Transition rules must be explicit.

**Fixed:** State transition tracking fully implemented:
- `transitioned_to_state_id` field in `ramp_states` now properly used
- `transition_state()` method in `db.py` handles atomic state transitions
- `state_transitioned` event type created for audit trail
- Resolution types: `RESOLVED`, `INTERVENTION`, `SUPERSEDED`, `ESCALATED`

**Implementation:**
- `POST /api/system/states/transition` - Transition from one state to another
- `GET /api/system/states/{state_id}/chain` - Get full transition history
- `POST /api/system/states/{state_id}/end` - End state with resolution type
- Events created in `ramp_events` table for all transitions

---

#### 3. ~~Escalation Logic (Priority: MEDIUM)~~ ✅ FIXED (2026-03-20)

**Reference (Priority Engine §8.2, §9.1):**
> Duration Increases Priority:
> - DRIFT for 10 minutes = medium
> - DRIFT for 8 hours = high
> - DRIFT for 2 days = critical
> 
> Escalation Modifier: Increase score if repeat occurrence, no action taken, state worsened.

**Fixed:** Duration-based escalation logic implemented:
- `EscalationService` in `/app/backend/ramp/services/escalation.py`
- Configurable thresholds per state type (DRIFT, DEGRADATION, SPIKE)
- Automatic escalation via `/api/system/escalation/run`
- Manual escalation via `/api/system/escalation/manual`
- `priority_escalated` events for audit trail

**Implementation:**
```python
DURATION_ESCALATION_THRESHOLDS = {
    "DRIFT": [(10, "MEDIUM"), (480, "HIGH"), (2880, "CRITICAL")],
    "DEGRADATION": [(30, "MEDIUM"), (240, "HIGH"), (1440, "CRITICAL")],
    "SPIKE": [(5, "HIGH"), (60, "CRITICAL")],
}
```

---

#### 4. ~~Confidence Labels (Priority: MEDIUM)~~ ✅ FIXED (2026-03-20)

**Reference (Lens Contract §4.6):**
> `confidence_label` e.g. strong / moderate / low — HOW can see this
> `confidence_raw` — WHERE only

**Current State:**
- Confidence exposed as numeric (0.89)
- No text label translation

**Required Fix:**
```python
def confidence_to_label(confidence: float) -> str:
    if confidence >= 0.80: return "strong"
    elif confidence >= 0.60: return "moderate"
    elif confidence >= 0.40: return "low"
    return "insufficient"
```

**Action:** Add `confidence_label` to HOW responses, keep raw for WHERE.

---

### ℹ️ FUTURE SCOPE — Not Required for Current MVP

These modules are defined in the Engineering Blueprint but are explicitly **out of scope** for the current MVP:

| Module | Blueprint Reference | MVP Status |
|--------|---------------------|------------|
| Assessment Engine (ESA, EMHA, EMRA) | CC-05, CC-06 | Future |
| LEAP Programme Management | CC-12 | Future |
| Partner Orchestration | CC-13 | Future |
| Portfolio Map (geographic) | CC-03 | Future |
| Reliability Analytics | CC-08 | Future |
| Resilience & Risk Layer | CC-09 | Future |
| Commercial Health | CC-11 | Future |
| Full Admin Console | CC-14 | Partial (basic) |

---

## Data Schema Comparison

### ERD from Reference vs Current Implementation

**Reference ERD (Wireframe Pack §10):**
```
Organisation (1:n) → Site (1:n) → Production Line (1:n) → Asset
                          ↓
                    Assessment → Recommendation → Action/Task
                          ↓
                        Alert
                          ↓
                      Programme
```

**Current Implementation:**
```
ramp_organisations (1:n) → ramp_sites (1:n) → ramp_systems (1:n) → ramp_assets
                                                                       ↓
ramp_baselines ← ramp_states ← ramp_priorities ← ramp_interventions ← ramp_outcomes
                                                                       ↓
                                                               ramp_events
                                                                       ↓
                                                               ramp_learning
```

**Alignment:**
- ✅ Organisation → Site → System (≈ Production Line) → Asset matches
- ✅ State ≈ Alert concept (behavioural exception)
- ✅ Intervention ≈ Action/Task
- ✅ Outcome = Verified result
- ℹ️ Assessment, Programme, Partner entities are future scope

---

## Priority Matrix

| Gap | Priority | Complexity | Action |
|-----|----------|------------|--------|
| Lens raw field suppression | HIGH | Low | Fix HOW lens builder |
| Confidence label translation | MEDIUM | Low | Add helper function |
| State transitions | MEDIUM | Medium | Add migration + logic |
| Escalation logic | MEDIUM | Medium | Add to priority calc |
| Full priority formula | LOW | Medium | Add action_friction, risk_delta |
| Baseline types (Operational, Asset) | LOW | High | Future enhancement |
| Composite states | LOW | High | Future enhancement |

---

## Recommended Action Plan

### ✅ Completed (2026-03-20)
1. **Fixed lens field suppression** — HOW lens now exposes bands/labels only
2. **Added confidence labels** — Single consistent mapping across all responses

### Near-Term (P1)
3. **Implement state transitions** — 4-6 hours
   - Add `transitioned_to_state_id` migration
   - Implement transition rules

4. **Add escalation logic** — 4-6 hours
   - Duration-based escalation
   - Auto-escalate on inaction

### Deferred (P2+)
5. Full priority formula with all 6 factors
6. Operational and Asset Performance baselines
7. Composite/hybrid states
8. Assessment Engine integration
9. LEAP Programme Management
10. Partner Orchestration

---

## Summary

The current implementation is **substantially aligned** with the canonical engineering references. The core VSO loop (Detect → Interpret → Prioritise → Act → Verify → Learn) is correctly implemented.

**Critical correction needed:** HOW lens is exposing raw numeric scores that should be bands/labels only. This violates the Lens Contract and should be fixed before expansion.

**Deviations are documented.** New work will align with these references, and any future deviations will be explicitly called out.

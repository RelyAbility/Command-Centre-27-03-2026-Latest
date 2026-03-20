# RAMP Engineering Reference Alignment Report

## Documents Reviewed

1. **1-6. RAMP – State Engine (V1)** - State creation, lifecycle, transitions, severity, confidence
2. **1-7. RAMP – Baseline & Savings Method (V1)** - Baseline types, freeze, deviation, verification
3. **1-8. RAMP – Priority Engine (V1)** - Priority formula, bands, types, decision guardrails
4. **1-9. RAMP Command Centre — MVP Handoff Pack (V1)** - Core capabilities, architecture, acceptance criteria
5. **1-3. RAMP Lens Contract Specification (V1)** - Field-level exposure rules per lens

---

## Current Implementation Alignment Summary

### ✅ Aligned (No Action Required)

| Reference Spec | Current Implementation | Status |
|----------------|------------------------|--------|
| State families: OPERATIONAL, ENERGY, MAINTENANCE, PRODUCTION | Implemented in `state_family` field | ✅ |
| State types: DRIFT, SPIKE, DEGRADATION, etc. | Implemented in `state_type` field | ✅ |
| Baseline freeze on intervention | `frozen_at`, `frozen_for_intervention_id` | ✅ |
| Baseline confidence scoring | `confidence`, `confidence_band` | ✅ |
| Context segmentation | `context_signature` JSONB field | ✅ |
| State severity with band | `severity_score`, `severity_band` | ✅ |
| State confidence | `confidence`, `confidence_band` | ✅ |
| Priority bands: CRITICAL, HIGH, MEDIUM, LOW | `priority_band` field | ✅ |
| Priority drivers (explainability) | `drivers` JSONB array | ✅ |
| Economic impact | `economic_impact` with VaR/VR | ✅ |
| Outcome statuses | PENDING, VERIFIED, INSUFFICIENT_DATA | ✅ |
| Savings against frozen baseline | Implemented in verification scheduler | ✅ |
| Event backbone | All state changes emit events | ✅ |
| HOW/WHERE lens separation | `/api/how/*`, `/api/where/*` routes | ✅ |

---

## ⚠️ Areas Requiring Attention

### 1. State Transitions (Reference: State Engine §8)

**Reference Spec:**
> States must transition — not just stop/start.
> `current_state → next_state`
> Transition rules must be explicit, versioned, deterministic.

**Current Implementation:**
- States have `ended_at` and `resolution_type` but no explicit transition tracking
- No `next_state_id` or transition log

**Recommendation:**
- Add `transitioned_to_state_id` field to `ramp_states`
- Add `state_transitioned` event type
- Implement transition rules in State Engine

---

### 2. State Composition / Hybrid States (Reference: State Engine §11)

**Reference Spec:**
> `composite_state = operational + energy + maintenance (+ context)`
> Example: RUNNING + DRIFT + DEGRADING → composite state
> Composite states override simple states.

**Current Implementation:**
- Each state is independent
- No composite state linking

**Recommendation:**
- Consider adding `composite_state_members` array to track concurrent states
- May defer to P1 if not critical for MVP

---

### 3. State Hierarchy / Aggregation (Reference: State Engine §12)

**Reference Spec:**
> States must aggregate upward: Asset → System → Line → Site
> Weighted by: energy consumption, production criticality, cost impact

**Current Implementation:**
- States are asset-level only
- No system/site-level state aggregation

**Recommendation:**
- Add system-level state aggregation for WHERE lens
- May defer to P1 (multi-site support)

---

### 4. Escalation Logic (Reference: State Engine §14)

**Reference Spec:**
> States escalate when: duration increases, severity increases, no action taken
> Example: drift > 2 hours → notify, > 8 hours → escalate, > 24 hours → critical

**Current Implementation:**
- No automatic escalation
- `escalation_status` field exists but not populated

**Recommendation:**
- Implement escalation thresholds in Priority Engine
- Add `escalation_threshold_hours` to rules

---

### 5. Priority Formula (Reference: Priority Engine §5)

**Reference Spec:**
```
priority_score = (state_severity × 0.30) 
               + (economic_impact × 0.25) 
               + (risk_delta × 0.15) 
               + (criticality × 0.15) 
               + (confidence × 0.10) 
               - (action_friction × 0.05)
```

**Current Implementation:**
- Priority score calculated but formula not exactly matching
- `action_friction` not implemented

**Recommendation:**
- Review and align priority calculation with reference weights
- Add `action_friction` consideration

---

### 6. Baseline Types (Reference: Baseline Method §3)

**Reference Spec:**
Three distinct baseline types:
1. **Behavioural Baseline** - Expected metric behaviour (kWh/unit, load factor)
2. **Operational Baseline** - Expected state behaviour (% time in Idle, Drift)
3. **Asset Performance Baseline** - Expected physical performance (efficiency, flow curves)

**Current Implementation:**
- Single baseline type (behavioural) via `metric_type`
- No operational or asset performance baselines

**Recommendation:**
- Add `baseline_category` field: BEHAVIOURAL, OPERATIONAL, ASSET_PERFORMANCE
- Consider for P1 advanced learning

---

### 7. Lens Contract - Raw Field Suppression (Reference: Lens Contract §4)

**Reference Spec - Fields SYSTEM Only:**
- `severity_score_raw` - never exposed
- `priority_score_raw` - internal only
- `baseline_value` - never exposed raw outside SYSTEM
- `confidence_raw` - WHERE only, not HOW

**Current Implementation:**
- `/api/how/priorities` returns raw `priority_score`
- Baseline values may be exposed in some responses

**Recommendation:**
- Review HOW API responses to ensure raw scores are replaced with bands
- Add lens builders to filter raw numeric fields
- Ensure HOW gets `priority_band` not `priority_score`

---

### 8. Lens Contract - Specific Field Violations

**Fields currently exposed that should be suppressed:**

| Field | Current | Should Be | Action |
|-------|---------|-----------|--------|
| `priority_score` in HOW | Exposed | `priority_band` only | Filter |
| `confidence` raw in HOW | Exposed | `confidence_label` | Translate |
| `baseline_value` in HOW | Exposed | Suppressed | Filter |
| `severity_score` in HOW | Exposed | `severity_band` only | Filter |

---

### 9. API Endpoint Naming (Reference: Handoff Pack §6.2)

**Reference Spec:**
- `/api/how/vso-queue`
- `/api/how/state/{id}`
- `/api/how/interventions`
- `/api/how/outcomes`
- `/api/where/state-distribution`
- `/api/where/risk-distribution`

**Current Implementation:**
- `/api/how/priorities` (should be `/api/how/vso-queue`)
- `/api/how/assets/{id}/state`
- `/api/where/priorities/summary`

**Recommendation:**
- Consider aliasing `/api/how/vso-queue` → `/api/how/priorities`
- Minor naming adjustment, low priority

---

## Recommended Action Plan

### Immediate (Before Next Feature Work)

1. **Lens Field Filtering** - Update HOW lens builder to suppress raw scores
   - Priority: HIGH
   - Impact: Contract compliance
   
2. **Review Priority Calculation** - Align with reference formula weights
   - Priority: MEDIUM
   - Impact: Consistency

### Near-Term (P1)

3. **State Transitions** - Add transition tracking
4. **Escalation Logic** - Implement duration-based escalation
5. **State Aggregation** - System-level states for WHERE

### Future (P2)

6. **Composite States** - Hybrid state handling
7. **Baseline Types** - Operational and Asset Performance baselines
8. **Full Priority Formula** - Add `action_friction` and `risk_delta`

---

## Summary

The current implementation is **substantially aligned** with the engineering references. The core loop, state model, baseline freeze, verification, and learning are all implemented correctly.

**Key gaps to address:**
1. **Lens field suppression** - Raw scores exposed in HOW that should be bands only
2. **State transitions** - Not explicitly tracked
3. **Escalation logic** - Not implemented

These can be addressed incrementally without breaking changes.

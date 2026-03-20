# RAMP Command Centre — MVP PRD

## Original Problem Statement

Build RAMP — a state-based, event-driven decision and action system for industrial intelligence. Not a dashboard, not a traditional data platform. Everything structured around:

**Signal → State → Decision → Action → Learning**

## Architecture

### Core Loop (MVP COMPLETE)
```
Sensor → Signal → Metric → Baseline → Rule → STATE → Priority → ACTION → Outcome → LEARNING
```

### System Principles
- **State is the behavioral truth** — not metrics, not signals
- **Baselines make deviation meaningful** — first-class primitive
- **VSO (Verified State Outcome)** — output for learning and commercial value
- **HOW vs WHERE** — lens separation, not separate engines

### Technology Stack
- **Backend:** FastAPI + Supabase/PostgreSQL (via asyncpg)
- **Frontend:** React + TailwindCSS
- **Events:** Synchronous dispatch, database-backed immutable audit trail
- **ORM:** SQLAlchemy with Alembic migrations

## User Personas

### HOW Lens (Operators)
- See what matters now (priority queue)
- Take action on states
- Verify if actions worked

### WHERE Lens (Portfolio)
- See risk distribution
- View aggregated value at risk
- Export evidence

## Core Requirements

| Requirement | Status |
|-------------|--------|
| Signal ingestion | ✅ Implemented |
| Metric calculation | ✅ Implemented |
| Baseline establishment | ✅ Implemented |
| Baseline freeze on intervention | ✅ Implemented |
| State detection via rules | ✅ Implemented |
| Severity scoring (base + modifiers) | ✅ Implemented |
| Confidence construction | ✅ Implemented |
| Priority calculation | ✅ Implemented |
| Economic impact (VaR + VR) | ✅ Implemented |
| Intervention capture | ✅ Implemented |
| **Verification scheduler** | ✅ Implemented (2026-03-20) |
| **Configurable verification windows** | ✅ Implemented |
| **Outcome status handling** | ✅ Implemented |
| **Learning engine connection** | ✅ Implemented |
| HOW lens API | ✅ Implemented |
| WHERE lens API | ✅ Implemented |
| Command Centre UI | ✅ Implemented |
| PostgreSQL Migration | ✅ Completed |

## What's Been Implemented

### Date: 2026-03-20 - Verification & Learning Loop Complete

**MAJOR: Core MVP Loop is Complete**

The full verification and learning loop is now functional:

1. **Verification Configuration** (`/app/backend/ramp/services/verification_config.py`):
   - Configurable windows by **state family** (ENERGY: 4h, OPERATIONAL: 2h, MAINTENANCE: 8h)
   - Configurable windows by **intervention type** (ADJUSTMENT: 2h, REPAIR: 8h, REPLACEMENT: 24h, CALIBRATION: 1h)
   - Intervention type takes precedence over state family
   - Configurable: `window_hours`, `min_samples`, `min_window_coverage`, `max_retry_attempts`

2. **Verification Scheduler** (`/app/backend/ramp/services/verification_scheduler.py`):
   - Processes PENDING outcomes when verification window elapses
   - **Always verifies against frozen baseline**
   - Calculates savings: `baseline_value - actual_avg`
   - Calculates explicit confidence (0.0-1.0) with confidence band
   - Handles retries for insufficient data

3. **Outcome Status Handling**:
   - `PENDING` → Window not elapsed or data accumulating
   - `VERIFIED` → Sufficient data, savings and confidence calculated
   - `INSUFFICIENT_DATA` → Max retries reached, data never sufficient
   - **Never forces verification** — proper guard rails

4. **Learning Connection**:
   - Verified outcomes update learning records
   - Tracks: `occurrence_count`, `intervention_count`, `total_savings`, `avg_effectiveness`
   - Events created: `outcome_verified`, `learning_updated`

5. **API Endpoints**:
   - `GET /api/system/verification/config` — View all verification settings
   - `GET /api/system/verification/pending` — List pending outcomes
   - `POST /api/system/verification/run` — Execute verification scheduler
   - `GET /api/system/learning/{asset_id}` — Get learning records
   - `POST /api/system/demo/complete-verification-flow` — Full demo
   - `POST /api/system/demo/insufficient-data-scenario` — Guard rail demo

**Testing Results (25/25 passed):**
- Verification config with state family and intervention type configs ✅
- Pending outcomes tracking ✅
- Scheduler processes outcomes correctly ✅
- Verified outcomes have explicit confidence ✅
- INSUFFICIENT_DATA handling (never forced to VERIFIED) ✅
- Learning records update after verification ✅
- Relational chain with SQL JOINs ✅
- HOW/WHERE lens endpoints work ✅

### Earlier: 2026-03-20 - PostgreSQL Migration

Successfully migrated from MongoDB to Supabase/PostgreSQL:
- 13 tables with `ramp_` prefix and foreign key relationships
- JSONB handling with `CAST(:param AS jsonb)` for asyncpg
- Full relational chain verified with SQL JOINs

---

## MVP Complete Status

The core RAMP MVP loop is now **COMPLETE**:

```
Signal → Metric → Baseline → Rule → STATE → Priority → ACTION → Outcome → LEARNING
                      ↑                                  ↓
                      └─────── Baseline Freeze ──────────┘
                                     ↓
                            Verification against Frozen Baseline
                                     ↓
                            Verified Outcome with Savings/Confidence
                                     ↓
                            Learning Record Updated
```

**Key Guardrails Enforced:**
1. ✅ Verification window configurable by state family / intervention type
2. ✅ Verification always against frozen baseline
3. ✅ Never force verification without sufficient data
4. ✅ Verified outcomes carry explicit confidence

---

## Prioritized Backlog

### P0 (MVP) ✅ COMPLETE
- Full event loop working
- State detection and priority assignment
- Intervention creation with baseline freeze
- PostgreSQL migration with full chain verification
- Verification scheduling with configurable windows
- Outcome status handling (PENDING, VERIFIED, INSUFFICIENT_DATA)
- Learning connection from verified outcomes

### P1 (Product Surface)
- Frontend Verified Outcomes View
- State timeline visualization
- Real-time updates (WebSocket)
- Rule configuration admin UI

### P2 (Future)
- Multiple sites support
- Asset relationships/dependencies
- Advanced learning (baseline optimization from verified outcomes)
- Cross-asset benchmarking
- Outcome export (CSV/PDF)
- Asset-class-specific threshold modifiers
- Complex site configurations (demand-based energy tariffs)

## Next Tasks

1. **P1: Frontend Verified Outcomes View**
   - Display verification results in Command Centre
   - Show savings calculations and confidence bands
   - Timeline of outcome progression

2. **P1: Real-time Updates**
   - WebSocket for priority queue updates
   - State change notifications
   - Verification completion alerts

3. **P1: Rule Configuration UI**
   - Admin interface for rule management
   - Verification window configuration

4. **P2: Learning-driven Baseline Optimization**
   - Use verified outcomes to refine baseline thresholds
   - Track effectiveness patterns

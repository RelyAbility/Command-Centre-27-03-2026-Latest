# RAMP Command Centre — MVP PRD

## Original Problem Statement

Build RAMP — a state-based, event-driven decision and action system for industrial intelligence. Not a dashboard, not a traditional data platform. Everything structured around:

**Signal → State → Decision → Action → Learning**

## Architecture

### Core Loop
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
- **Events:** Synchronous dispatch (MVP), database-backed immutable audit trail
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
| Verification engine | ✅ Implemented |
| Learning engine (partial) | ✅ Implemented |
| HOW lens API | ✅ Implemented |
| WHERE lens API | ✅ Implemented |
| Command Centre UI | ✅ Implemented |
| PostgreSQL Migration | ✅ Completed (2026-03-20) |

## What's Been Implemented

### Date: 2026-03-20 - PostgreSQL Migration Complete

**MAJOR: MongoDB → Supabase/PostgreSQL Migration**

Successfully migrated entire persistence layer from MongoDB to Supabase/PostgreSQL:

1. **Database Schema** (13 tables with `ramp_` prefix):
   - `ramp_organisations`, `ramp_sites`, `ramp_systems`, `ramp_assets`
   - `ramp_rules`, `ramp_signals`, `ramp_metrics`
   - `ramp_baselines`, `ramp_states`, `ramp_priorities`
   - `ramp_interventions`, `ramp_outcomes`
   - `ramp_events` (immutable audit trail with trigger protection)
   - `ramp_learning`

2. **Foreign Key Relationships Verified** (with SQL JOINs):
   ```
   baseline → state → priority → intervention → outcome → event
   ```

3. **JSONB Handling Fixed**:
   - All JSONB columns use `CAST(:param AS jsonb)` syntax for asyncpg compatibility
   - JSON serialization via `json.dumps()` before binding

4. **API Endpoints Working**:
   - `/api/system/reset` — Clear all demo data
   - `/api/system/seed` — Idempotent demo data seeding
   - `/api/system/demo/simulate-drift` — Create full relational chain
   - `/api/system/checkpoint/relational-chain` — Verify chain with SQL JOINs
   - `/api/how/priorities` — Operator priority queue
   - `/api/how/interventions` — Create/complete interventions
   - `/api/where/priorities/summary` — Portfolio overview

5. **Lens Separation Enforced**:
   - HOW lens via `/app/backend/ramp/lenses/how.py`
   - WHERE lens via `/app/backend/ramp/lenses/where.py`

**Key Files Modified:**
- `/app/backend/ramp/db.py` — Complete rewrite for PostgreSQL
- `/app/backend/database.py` — Supabase async connection
- `/app/backend/server.py` — Updated routes and checkpoint test
- `/app/backend/models.py` — SQLAlchemy ORM models
- `/app/backend/alembic/versions/ramp_001_initial_schema.py` — Migration

---

### Earlier Work

**Phase 0: Foundation (Locked)**
- Data model schema (13 tables)
- 7 services with clear boundaries
- Event flow with synchronous dispatch

**Services:**
1. Ingestion Service — signal intake, metric calculation
2. Baseline Engine — establish, maintain, freeze baselines
3. State Engine — rule evaluation, state lifecycle
4. Priority Engine — scoring, economic impact
5. Intervention Service — action capture, baseline freeze trigger
6. Verification Engine — post-action comparison, savings calculation
7. Learning Engine — recurrence tracking, effectiveness (partial)

**APIs:**
- `/api/system/*` — health, seed, demo, reset, checkpoint
- `/api/how/*` — operator priority queue, asset state, interventions
- `/api/where/*` — portfolio summary, site states, outcomes export
- `/api/ingest/*` — signal batch ingestion

**Frontend:**
- Command Centre UI with HOW/WHERE lens toggle
- Priority queue with drivers and economic impact
- Asset state panel with active states
- Intervention modal
- Portfolio overview with distribution chart

## Prioritized Backlog

### P0 (MVP Complete) ✅
- Full event loop working
- State detection and priority assignment
- Intervention creation with baseline freeze
- PostgreSQL migration with full chain verification

### P1 (Next)
- Verification scheduler (wait for post-action data accumulation)
- Support for "pending" / "insufficient_data" outcome statuses
- Connect verified outcomes to Learning Engine for baseline refinement
- State timeline visualization
- Real-time updates (WebSocket)

### P2 (Future)
- Multiple sites support
- Asset relationships/dependencies
- Advanced learning (baseline optimization)
- Benchmark learning / cross-asset comparison
- Portfolio-level WHERE views
- Outcome export to CSV/PDF
- Asset-class-specific threshold modifiers (V1.1)
- Complex site configurations (demand-based energy tariffs)

## Next Tasks

1. **P1: Verification Loop Completion**
   - Implement scheduler to run verification after configurable time window
   - Add logic to accumulate post-action metric data
   - Support pending/insufficient_data statuses
   - Connect outcomes to Learning Engine

2. **P1: Frontend Verified Outcomes View**
   - Display verification results in Command Centre
   - Show savings calculations and confidence

3. **P2: Real-time Updates**
   - WebSocket for priority queue updates
   - State change notifications

4. **P2: Admin UI**
   - Rule configuration interface
   - Asset class threshold modifiers

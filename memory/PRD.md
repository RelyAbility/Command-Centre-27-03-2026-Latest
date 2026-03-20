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

## Core Requirements Status

| Requirement | Status |
|-------------|--------|
| Signal ingestion | ✅ Implemented |
| Metric calculation | ✅ Implemented |
| Baseline establishment | ✅ Implemented |
| Baseline freeze on intervention | ✅ Implemented |
| State detection via rules | ✅ Implemented |
| Severity scoring | ✅ Implemented |
| Confidence construction | ✅ Implemented |
| Priority calculation | ✅ Implemented |
| Economic impact (VaR + VR) | ✅ Implemented |
| Intervention capture | ✅ Implemented |
| Verification scheduler | ✅ Implemented |
| Configurable verification windows | ✅ Implemented |
| Outcome status handling | ✅ Implemented |
| Learning engine connection | ✅ Implemented |
| PostgreSQL Migration | ✅ Completed |
| **Proof of Value View** | ✅ Completed (2026-03-20) |

## What's Been Implemented

### Date: 2026-03-20 - Proof of Value View Complete

**MAJOR: Single Focused Dashboard Demonstrating Full Loop**

Built a "Proof of Value" view that answers in under a minute:

1. **Where is value being lost?**
   - Current Value at Risk: `$XX.XX/day`
   - Breakdown by priority band (CRITICAL, HIGH, MEDIUM, LOW)
   - Active priority count

2. **What to do about it?**
   - Top Priority Actions (max 5)
   - Each shows: asset name, state type, value at risk, confidence band
   - "Take Action" button opens intervention modal

3. **What has been recovered?**
   - Total savings recovered
   - Recent verified outcomes with:
     - Savings value and unit (e.g., +6.9 kWh)
     - Confidence band and percentage
     - Time to verify (hours)

4. **Is the system working?**
   - Loop Integrity signal
   - Verified / Pending / Insufficient counts
   - Verification rate percentage
   - Status badge: HEALTHY (≥70%) / DEGRADED (≥40%) / POOR (<40%)

**API Endpoint:**
```
GET /api/system/value-summary
```
Returns all four sections in a single call.

**Testing: 13/13 backend tests + all UI elements verified**

---

### Earlier: 2026-03-20 - Verification & Learning Loop

Implemented complete verification and learning loop with guardrails:
- Configurable verification windows by state family and intervention type
- Always verifies against frozen baseline
- Never forces verification without sufficient data
- Verified outcomes carry explicit confidence
- Learning records updated after successful verification

### Earlier: 2026-03-20 - PostgreSQL Migration

Migrated from MongoDB to Supabase/PostgreSQL with full relational chain verification.

---

## MVP Complete Status ✅

The core RAMP MVP is now **COMPLETE** with:

1. ✅ **Full Event Loop** — Signal → State → Decision → Action → Learning
2. ✅ **PostgreSQL Persistence** — Relational chain with SQL JOINs
3. ✅ **Verification Loop** — Configurable, guarded, with explicit confidence
4. ✅ **Proof of Value Surface** — Single view showing business impact

---

## Prioritized Backlog

### P0 (MVP) ✅ COMPLETE

### P1 (Productization)
- Real-time updates (WebSocket for priority queue, state changes)
- Rule configuration admin UI
- Multiple sites support
- User authentication (Emergent Google Auth or JWT)

### P2 (Expansion)
- Asset relationships/dependencies
- Advanced learning (baseline optimization from verified outcomes)
- Cross-asset benchmarking
- Outcome export (CSV/PDF)
- Asset-class-specific threshold modifiers
- Complex site configurations (demand-based energy tariffs)

## Next Tasks

1. **P1: Real-time Updates**
   - WebSocket for priority queue updates
   - State change notifications
   - Verification completion alerts

2. **P1: Rule Configuration UI**
   - Admin interface for rule management
   - Verification window configuration

3. **P1: Multi-site Support**
   - Site selector in dashboard
   - Site-level aggregation

## Key Files

### Backend
- `/app/backend/server.py` — Main API with all endpoints
- `/app/backend/ramp/db.py` — Database operations
- `/app/backend/ramp/services/verification_scheduler.py` — Verification logic
- `/app/backend/ramp/services/verification_config.py` — Configurable windows
- `/app/backend/ramp/lenses/how.py` — HOW lens payload builder
- `/app/backend/ramp/lenses/where.py` — WHERE lens payload builder

### Frontend
- `/app/frontend/src/App.js` — Proof of Value dashboard

### Database
- `/app/backend/alembic/versions/ramp_001_initial_schema.py` — Schema
- `/app/backend/alembic/versions/ramp_002_add_retry_count.py` — Retry tracking

## Test Reports
- `/app/test_reports/iteration_2.json` — Verification system tests (25/25 passed)
- `/app/test_reports/iteration_3.json` — Proof of Value tests (13/13 passed)

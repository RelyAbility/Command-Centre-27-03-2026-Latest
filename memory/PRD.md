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
- **Real-time:** WebSocket with event backbone integration
- **State management:** Zustand (frontend WebSocket state)

## Core Requirements Status

| Requirement | Status |
|-------------|--------|
| Signal ingestion | Implemented |
| Metric calculation | Implemented |
| Baseline establishment | Implemented |
| Baseline freeze on intervention | Implemented |
| State detection via rules | Implemented |
| Severity scoring | Implemented |
| Confidence construction | Implemented |
| Priority calculation | Implemented |
| Economic impact (VaR + VR) | Implemented |
| Intervention capture | Implemented |
| Verification scheduler | Implemented |
| Configurable verification windows | Implemented |
| Outcome status handling | Implemented |
| Learning engine connection | Implemented |
| PostgreSQL Migration | Completed |
| Proof of Value View | Completed |
| First 5 Minutes Experience | Completed (2026-03-20) |
| State Transition Tracking | Completed (2026-03-20) |
| Duration-based Escalation | Completed (2026-03-20) |
| WebSocket Real-time Updates | Completed (2026-03-23) |
| Database Security (RLS) | Completed (2026-03-23) |
| Authentication (Supabase) | Completed (2026-03-23) |
| Role-based Access Control | Completed (2026-03-23) |
| Multi-site Scoped Access | Completed (2026-03-26) |
| Frontend WebSocket Hook (Zustand) | Completed (2026-03-26) |
| Industrial Intelligence Surface | Completed (2026-03-27) |
| **Portfolio Mode (Multi-Site Intelligence)** | **Completed (2026-03-27)** |

## Rockwell Demo — Intelligence Surface

The Intelligence Surface is ONE unified component that scales from asset → site → portfolio based on user role:

### Operator Mode (HOW lens)
- Asset-level ranked priorities via WebSocket
- Inline traceability (State → Priority → Intervention → Outcome)
- Real-time "Live" indicator
- Individual outcome details

### Portfolio Mode (WHERE lens)
- Site-level aggregation ranked by VaR
- "Focus here first" callout for highest-risk site
- Portfolio badge in header
- Per-site outcome summaries
- Trust metrics scoped to portfolio

### Role Routing (same surface, different aggregation)
- **Operator** → Operator mode
- **Portfolio** → Portfolio mode
- **Admin** → Operator mode (has HOW + WHERE, HOW takes precedence)

### Key API Endpoints
- `GET /api/intelligence/summary` — Operator VaR/recoverable/count
- `GET /api/intelligence/outcomes` — Operator verified outcomes
- `GET /api/intelligence/trust` — System trust metrics
- `GET /api/intelligence/trace/{state_id}` — Condition-to-outcome trace
- `GET /api/where/portfolio/intelligence` — Portfolio site-level aggregation
- `POST /api/system/demo/seed-portfolio` — Seed multi-site demo data

## Test Users
- Admin: rampadmin@gmail.com / RampAdmin2024!
- Operator: operator1@gmail.com / Operator2024!
- Portfolio: portfolio1@gmail.com / Portfolio2024!

## Demo Data
- **Riverside Plant - Building A**: 3 priorities (HIGH $151, MEDIUM $43, LOW $19) = $213/day
- **Warehouse Distribution Center**: 2 priorities (CRITICAL $340, MEDIUM $55) = $395/day
- **Portfolio Total**: $608/day VaR across 2 sites, $514/day recoverable

---

## Next Tasks

**P0 — Design Polish (Rockwell Demo)**
- Use design agent to refine visual aesthetics of Intelligence Surface (Clarity > Speed > Credibility)

**P1 — Minimal Admin (Pilot Support)**
- Admin UI: User roles, site assignment, basic site creation/edit
- Rule Configuration: Threshold tuning, verification window config

**P2 — Post-Pilot**
- Asset relationships/dependencies
- Cross-asset benchmarking
- Learning optimization
- Export/reporting

**Deferred**
- Full assessment modules (IBA, EPA, EMHA, EMRA)
- Accelerator schema integration
- Large-scale admin tooling
- Energy cost configuration

## Key Files

### Backend
- `/app/backend/server.py` — Main API with intelligence & portfolio endpoints
- `/app/backend/ramp/db.py` — Database operations
- `/app/backend/ramp/auth/` — Authentication module
- `/app/backend/ramp/auth/scope.py` — Site scope filtering
- `/app/backend/ramp/lenses/where.py` — WHERE lens payload builder
- `/app/backend/ramp/websocket/` — WebSocket connection manager
- `/app/backend/ramp/services/escalation.py` — Escalation service

### Frontend
- `/app/frontend/src/components/IntelligenceSurface.jsx` — Dual-mode intelligence surface
- `/app/frontend/src/stores/useRAMPStore.js` — Zustand WebSocket state store
- `/app/frontend/src/hooks/useRAMPWebSocket.js` — React hooks for WebSocket
- `/app/frontend/src/contexts/AuthContext.jsx` — Auth context with role detection
- `/app/frontend/src/components/ConnectionStatus.jsx` — Connection indicator
- `/app/frontend/src/components/LoginForm.jsx` — Login form with demo credentials

## Test Reports
- `/app/test_reports/iteration_9.json` — Frontend WebSocket Hook tests (8/8 passed)
- `/app/test_reports/iteration_10.json` — Portfolio Intelligence tests (19/19 backend + 4/4 frontend)

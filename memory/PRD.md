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

## Rockwell Demo — Intelligence Surface (COMPLETE)

ONE surface, TWO modes — same component, different aggregation level.

### Operator Mode (HOW lens)
- Asset-level ranked priorities via WebSocket (Live indicator)
- Inline traceability (State → Priority → Intervention → Outcome)
- Real-time VaR summary
- Individual outcome details

### Portfolio Mode (WHERE lens) — Commercial Story
- **Focus Site Callout**: "Focus here first" with highest-risk site
- **Portfolio Scale Banner**: VaR/day, Annual Exposure ($222k), Recoverable/day, Sites + Assets count
- **Recurring Conditions**: "DRIFT — 5 occurrences, 2 sites, 5 assets — Systemic"
- **Sites Ranked by Risk**: Inline drill-down showing top 3 priorities per site
- **Replication Opportunity**: Asset-class breakdown showing where insights apply elsewhere
- **Scalable Impact**: "$1.30 verified → $1.30 across 1 similar asset" (projected savings)
- **System Trust**: Portfolio-scoped verification rate, actions validated, learning active

### Role Routing (same surface, different aggregation)
- **Operator** → Operator mode (asset level)
- **Portfolio** → Portfolio mode (site/portfolio level)
- **Admin** → Operator mode (has HOW + WHERE, HOW takes precedence)

### Key API Endpoints
- `GET /api/intelligence/summary` — Operator VaR/recoverable/count
- `GET /api/intelligence/outcomes` — Operator verified outcomes
- `GET /api/intelligence/trust` — System trust metrics
- `GET /api/intelligence/trace/{state_id}` — Condition-to-outcome trace
- `GET /api/where/portfolio/intelligence` — Portfolio intelligence with replication, repeatability, scaled outcomes, drill-down
- `POST /api/system/demo/seed-portfolio` — Seed multi-site demo data

## Core Requirements Status

| Requirement | Status |
|-------------|--------|
| Signal ingestion | Implemented |
| Metric calculation | Implemented |
| Baseline establishment | Implemented |
| Baseline freeze on intervention | Implemented |
| State detection via rules | Implemented |
| Severity/Confidence/Priority scoring | Implemented |
| Economic impact (VaR + VR) | Implemented |
| Intervention + Outcome pipeline | Implemented |
| Learning engine connection | Implemented |
| PostgreSQL Migration | Completed |
| Authentication (Supabase JWT) | Completed |
| RBAC + RLS | Completed |
| Multi-site Scoped Access | Completed |
| WebSocket Real-time (Zustand) | Completed |
| Intelligence Surface (Operator) | Completed (2026-03-27) |
| Portfolio Mode (Site-level) | Completed (2026-03-27) |
| **Portfolio Scale + Replication** | **Completed (2026-03-27)** |
| **Repeatability Signals** | **Completed (2026-03-27)** |
| **Scaled Outcomes** | **Completed (2026-03-27)** |
| **Site Drill-Down** | **Completed (2026-03-27)** |

## Test Users
- Admin: rampadmin@gmail.com / RampAdmin2024!
- Operator: operator1@gmail.com / Operator2024!
- Portfolio: portfolio1@gmail.com / Portfolio2024!

## Demo Data
- **Riverside Plant - Building A**: 3 priorities (HIGH $151, MEDIUM $43, LOW $19) = $213/day
- **Warehouse Distribution Center**: 2 priorities (CRITICAL $340, MEDIUM $55) = $395/day
- **Portfolio Total**: $608/day VaR, $222k annual exposure, $514/day recoverable, 7 assets across 2 sites

---

## Next Tasks

**P0 — Design Polish (Rockwell Demo)**
- Use design agent to refine visual aesthetics (Clarity > Speed > Credibility)

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
- Energy cost configuration

## Key Files

### Backend
- `/app/backend/server.py` — Main API with intelligence, portfolio, & demo endpoints
- `/app/backend/ramp/db.py` — Database operations
- `/app/backend/ramp/auth/` — Authentication module
- `/app/backend/ramp/auth/scope.py` — Site scope filtering
- `/app/backend/ramp/lenses/where.py` — WHERE lens payload builder
- `/app/backend/ramp/websocket/` — WebSocket connection manager

### Frontend
- `/app/frontend/src/components/IntelligenceSurface.jsx` — Dual-mode intelligence surface (scale, replication, repeatability, drill-down)
- `/app/frontend/src/stores/useRAMPStore.js` — Zustand WebSocket state store
- `/app/frontend/src/hooks/useRAMPWebSocket.js` — React hooks for WebSocket
- `/app/frontend/src/contexts/AuthContext.jsx` — Auth context with role detection
- `/app/frontend/src/components/ConnectionStatus.jsx` — Connection indicator

## Test Reports
- `/app/test_reports/iteration_9.json` — WebSocket Hook tests (8/8 passed)
- `/app/test_reports/iteration_10.json` — Portfolio Intelligence basic tests (19/19 + 4/4)
- `/app/test_reports/iteration_11.json` — Portfolio Commercial Features (23/23 + all frontend)

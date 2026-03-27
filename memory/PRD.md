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
- **IBA deterministic pipeline** — signals → metrics → states → benchmarks → recommendations (no AI)
- **WAT (Workflow-Agent-Tool)** — target architecture for structured, event-triggered workflows

### Technology Stack
- **Backend:** FastAPI + Supabase/PostgreSQL (via asyncpg)
- **Frontend:** React + TailwindCSS
- **Events:** Synchronous dispatch, database-backed immutable audit trail
- **ORM:** SQLAlchemy with Alembic migrations
- **Real-time:** WebSocket with event backbone integration
- **State management:** Zustand (frontend WebSocket state)

## Rockwell Demo — Intelligence Surface (COMPLETE)

ONE surface, TWO modes — same component, different aggregation level.
Industrial Refrigeration / Dairy Processing context throughout.

### Operator Mode (HOW lens)
- Asset-level ranked priorities via WebSocket (Live indicator)
- Inline traceability (State → Priority → Intervention → Outcome)
- Real-time VaR summary
- Individual outcome details

### Portfolio Mode (WHERE lens) — Full Commercial Story

**"We analysed 400 assets across your portfolio… here's where the money is… and here's proof we can capture it"**

#### Portfolio Analysis (IBA Layer)
- **Fleet Overview**: 400 refrigeration units · 8 sites · 30-day analysis
- **Scale**: $91k/30-day → $1.1M/year annualized opportunity
- **State Distribution**: Stable 54.5%, Drift 20.2%, Idle 9.2%, Cycling 9.8%, Degraded 6.2%
- **Top Opportunities**: Compressor Efficiency Recovery ($47k/mo), Refrigeration System Rehabilitation ($27k/mo), Compressor Cycling Optimization ($16k/mo), Standby Load Reduction ($1k/mo)
- **Fleet Benchmarks**: P25/P50/P75 for Energy Intensity, Runtime Ratio, Cycle Frequency
- **Trust Signal**: "Based on measured operating behaviour (no AI inference)"

#### Analysis → Action Connection
- Active Detection: [CRITICAL] Screw Compressor #2 at Food Processing Facility ($340/day)
- Verified Proof: Glycol Circulation Pump at Dairy Processing Plant (+1.3 kWh/hr reduction)

#### Site Intelligence
- 8 sites ranked by opportunity (Dairy Processing Plant #1 at $19k/mo)
- "Top Opportunity" + "RAMP Live" badges
- Inline drill-down showing live RAMP priorities per site
- Per-site state distribution breakdowns

### Demo Context (Industrial Refrigeration)
**Sites**: Dairy Processing Plant — Refrigeration, Food Processing Facility — Cold Storage
**Systems**: Ammonia Refrigeration System, Low-Temperature Cooling System, Glycol Circulation System, Cold Storage Refrigeration, Process Cooling System
**Assets**: Screw Compressor #1/#2, Evaporator Bank 1, Condenser Unit 1, Glycol Circulation Pump, Cold Room Evaporator, Blast Freezer Evaporator
**Condition Language**: compressor efficiency degradation, refrigeration load imbalance, cooling drift, elevated condenser load

### Role Routing
- **Operator** → Operator mode (asset level)
- **Portfolio** → Portfolio mode (analysis + action + proof)
- **Admin** → Operator mode (has HOW + WHERE, HOW takes precedence)

### Key API Endpoints
- `GET /api/intelligence/summary` — Operator VaR/recoverable/count
- `GET /api/intelligence/outcomes` — Operator verified outcomes
- `GET /api/intelligence/trust` — System trust metrics
- `GET /api/intelligence/trace/{state_id}` — Condition-to-outcome trace
- `GET /api/where/portfolio/intelligence` — Portfolio RAMP data
- `GET /api/iba/refrigeration/analysis` — Portfolio Analysis (deterministic IBA pipeline + RAMP connection)
- `POST /api/system/demo/first-five-minutes` — Seed primary site
- `POST /api/system/demo/seed-portfolio` — Seed multi-site demo data

## Core Requirements Status

| Requirement | Status |
|-------------|--------|
| Signal ingestion | Implemented |
| Metric calculation | Implemented |
| Baseline establishment | Implemented |
| State detection via rules | Implemented |
| Priority/Economic impact | Implemented |
| Intervention + Outcome pipeline | Implemented |
| Learning engine | Implemented |
| PostgreSQL + Auth + RBAC + RLS | Completed |
| WebSocket Real-time (Zustand) | Completed |
| Intelligence Surface (Operator) | Completed (2026-03-27) |
| Portfolio Mode (Site-level) | Completed (2026-03-27) |
| Portfolio Scale + Replication | Completed (2026-03-27) |
| IBA Deterministic Pipeline | Completed (2026-03-27) |
| Portfolio Analysis UI | Completed (2026-03-27) |
| Analysis → Action Connection | Completed (2026-03-27) |
| Fleet Benchmarks + Distribution | Completed (2026-03-27) |
| **Demo Context: Industrial Refrigeration** | **Completed (2026-03-27)** |

## Test Users
- Admin: rampadmin@gmail.com / RampAdmin2024!
- Operator: operator1@gmail.com / Operator2024!
- Portfolio: portfolio1@gmail.com / Portfolio2024!

## Demo Data
- **Site 1**: Dairy Processing Plant — Refrigeration (3 priorities, $213 VaR)
- **Site 2**: Food Processing Facility — Cold Storage (2 priorities, $395 VaR)
- **IBA Fleet**: 400 units across 8 sites, $1.09M/yr opportunity

---

## Next Tasks

**P0 — Design Polish (Rockwell Demo)**
- Use design agent to refine visual aesthetics (Clarity > Speed > Credibility)

**P1 — Minimal Admin (Pilot Support)**
- Admin UI: User roles, site assignment, basic site creation/edit
- Rule Configuration: Threshold tuning, verification window config

**P2 — WAT Architecture Alignment**
- Formalize workflows table and workflow execution engine (run_id, started_at, completed_at, status)
- Agent role boundaries (Ingestion, Triage, Analysis, Recommendation, Reporting, Learning)
- Event → Workflow automatic triggering (currently events are recorded but don't auto-trigger)
- WAT Starter Pack reference docs stored at /tmp/starter_pack/

**P3 — Post-Pilot**
- Asset relationships, benchmarking, learning optimization, export/reporting

**Deferred**
- Full assessment modules, energy cost configuration, accelerator schema

## Key Files

### Backend
- `/app/backend/server.py` — Main API with intelligence, portfolio, IBA endpoints, demo seeders
- `/app/backend/ramp/iba/pipeline.py` — Deterministic refrigeration analysis pipeline
- `/app/backend/ramp/db.py` — Database operations
- `/app/backend/ramp/auth/` — Authentication + scope filtering
- `/app/backend/ramp/lenses/where.py` — WHERE lens payload builder

### Frontend
- `/app/frontend/src/components/IntelligenceSurface.jsx` — Unified surface (Portfolio Analysis + RAMP)
- `/app/frontend/src/stores/useRAMPStore.js` — Zustand WebSocket state
- `/app/frontend/src/hooks/useRAMPWebSocket.js` — WebSocket hooks
- `/app/frontend/src/contexts/AuthContext.jsx` — Auth context with role detection

## Test Reports
- `/app/test_reports/iteration_9.json` — WebSocket Hook (8/8)
- `/app/test_reports/iteration_10.json` — Portfolio basic (19/19 + 4/4)
- `/app/test_reports/iteration_11.json` — Portfolio commercial (23/23 + all frontend)
- `/app/test_reports/iteration_12.json` — IBA Integration (31/31 + 17/17)
- `/app/test_reports/iteration_13.json` — Industrial Refrigeration Terminology (30/30 + all frontend)

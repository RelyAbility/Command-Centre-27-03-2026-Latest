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
Industrial Refrigeration / Food Processing context throughout.

### Demo Narrative
"We analysed 400 assets across your portfolio, identified $9.9M in recoverable value, executed actions, verified outcomes, and can scale this across your operations."

### Enterprise-Scale Economics (REFINED 2026-03-27)
- **Portfolio**: $825k 30-day opportunity / $9.9M annualized
- **Live Site VaR**: $10k-50k per site ($30k/day combined across 2 RAMP-monitored sites)
- **Verified Outcomes**: $52.50/day ($19k/yr) validated → $745k/yr fleet-scale replication
- **Outcome narrative**: Annualized financial terms + fleet replication counts

### Single-Industry Context (8 food/dairy/refrigeration sites)
1. Dairy Processing Plant — Refrigeration (RAMP Live)
2. Meat & Poultry Facility — Cooling Operations (RAMP Live)
3. Beverage Production — Cold Chain
4. Frozen Foods Processing — Blast Cooling
5. Cheese Production Facility — Cooling
6. Milk Powder Plant — Process Cooling
7. Seafood Processing — Flash Freezing
8. Cold Storage Facility — Distribution

### Assets & Condition Language
**Assets**: Screw Compressor #1/#2, Evaporator Bank 1, Condenser Unit 1, Glycol Circulation Pump, Cold Room Evaporator, Blast Freezer Evaporator
**Systems**: Ammonia Refrigeration, Low-Temperature Cooling, Glycol Circulation, Cold Storage Refrigeration, Process Cooling
**Conditions**: compressor efficiency degradation, refrigeration load imbalance, cooling drift, elevated condenser load

### Operator Mode (HOW lens)
- Asset-level ranked priorities via WebSocket (Live indicator)
- Inline traceability (State → Priority → Intervention → Outcome)
- Real-time VaR summary with annualized exposure
- Individual outcome details with $/day + /yr annualized

### Portfolio Mode (WHERE lens) — Full Commercial Story

#### Portfolio Analysis (IBA Layer)
- **Fleet Overview**: 400 refrigeration units across 8 sites, 30-day analysis
- **Scale**: $825k/30-day → $9.9M/yr annualized opportunity
- **State Distribution**: Stable 54.5%, Drift 20.2%, Idle 9.2%, Cycling 9.8%, Degraded 6.2%
- **Top Opportunities**: Compressor Efficiency Recovery ($427k/mo), Refrigeration System Rehabilitation ($237k/mo), Compressor Cycling Optimization ($148k/mo), Standby Load Reduction ($13k/mo)
- **Fleet Benchmarks**: P25/P50/P75 with executive interpretation (P75 = top-quartile inefficiency, target P50)
- **Trust Signal**: "Based on measured operating behaviour (no AI inference)"

#### Analysis → Action → Outcome Connection
- Narrative: "Detected across portfolio assets → prioritised → resolved → verified → scaled across operations"
- Active Detection: [CRITICAL] Screw Compressor #2 at Food Processing Facility ($17,000/day)
- Verified Proof: Glycol Circulation Pump at Dairy Processing Plant ($34/day → $12.4k/yr → 60 similar → $745k/yr)

#### Verified Outcomes (Annualized + Fleet Replication)
- Portfolio verified: $52.50/day → $19.2k/yr annualized
- Fleet-scale replication shows asset_type_counts from IBA fleet (177 compressors, 95 condensers, 68 evaporators, 60 pumps)

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
- `GET /api/iba/refrigeration/analysis` — Portfolio Analysis (IBA pipeline + RAMP connection)
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
| Intelligence Surface (Operator) | Completed |
| Portfolio Mode (Site-level) | Completed |
| Portfolio Scale + Replication | Completed |
| IBA Deterministic Pipeline | Completed |
| Demo Context: Industrial Refrigeration | Completed (2026-03-27) |
| **Scaled Economics (Enterprise)** | **Completed (2026-03-27)** |
| **Single-Industry Narrative** | **Completed (2026-03-27)** |
| **Annualized Outcome Narrative** | **Completed (2026-03-27)** |
| **Benchmark Interpretation** | **Completed (2026-03-27)** |
| **Portfolio→Action→Outcome Narrative** | **Completed (2026-03-27)** |

## Test Users
- Admin: rampadmin@gmail.com / RampAdmin2024!
- Operator: operator1@gmail.com / Operator2024!
- Portfolio: portfolio1@gmail.com / Portfolio2024!

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
- Event → Workflow automatic triggering (events recorded but don't auto-trigger yet)
- WAT Starter Pack reference: /tmp/starter_pack/

**P3 — Post-Pilot**
- Asset relationships, benchmarking, learning optimization
- Export/reporting functionality
- Energy cost/tariff configuration interface

## Key Files

### Backend
- `/app/backend/server.py` — Main API with intelligence, portfolio, IBA endpoints, demo seeders
- `/app/backend/ramp/iba/pipeline.py` — Deterministic 400-unit analysis with enterprise-scale economics
- `/app/backend/ramp/db.py` — Database operations
- `/app/backend/ramp/auth/` — Authentication + scope filtering

### Frontend
- `/app/frontend/src/components/IntelligenceSurface.jsx` — Unified surface with portfolio analysis, annualized outcomes, benchmark interpretation
- `/app/frontend/src/stores/useRAMPStore.js` — Zustand WebSocket state
- `/app/frontend/src/hooks/useRAMPWebSocket.js` — WebSocket hooks

## Test Reports
- `/app/test_reports/iteration_9.json` — WebSocket Hook (8/8)
- `/app/test_reports/iteration_10.json` — Portfolio basic (19/19 + 4/4)
- `/app/test_reports/iteration_11.json` — Portfolio commercial (23/23 + all frontend)
- `/app/test_reports/iteration_12.json` — IBA Integration (31/31 + 17/17)
- `/app/test_reports/iteration_13.json` — Industrial Refrigeration Terminology (30/30 + all frontend)
- `/app/test_reports/iteration_14.json` — Scaled Economics + Rockwell Readiness (19/19 + all frontend)

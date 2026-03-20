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
- **Backend:** FastAPI + MongoDB
- **Frontend:** React + TailwindCSS
- **Events:** Synchronous dispatch (MVP), database-backed audit trail

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

## What's Been Implemented

### Date: 2026-03-20

**Phase 0: Foundation (Locked)**
- Data model schema (13 collections)
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
- `/api/system/*` — health, seed, demo
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

### P1 (Next)
- Verification with sufficient post-action data
- State timeline visualization
- Real-time updates (WebSocket)

### P2 (Future)
- Multiple sites support
- Asset relationships/dependencies
- Advanced learning (baseline optimization)
- Benchmark learning
- Portfolio-level WHERE views
- Outcome export to CSV/PDF

## Next Tasks

1. Add verification window scheduling (wait for post-action data)
2. Implement state timeline component
3. Add WebSocket for real-time priority updates
4. Create admin UI for rule configuration
5. Add asset class threshold modifiers

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
| Proof of Value View | ✅ Completed |
| First 5 Minutes Experience | ✅ Completed (2026-03-20) |
| State Transition Tracking | ✅ Completed (2026-03-20) |
| Duration-based Escalation | ✅ Completed (2026-03-20) |
| WebSocket Real-time Updates | ✅ Completed (2026-03-23) |
| **Database Security (RLS)** | ✅ Completed (2026-03-23) |
| **Authentication (Supabase)** | ✅ Completed (2026-03-23) |
| **Role-based Access Control** | ✅ Completed (2026-03-23) |
| **Multi-site Scoped Access** | ✅ Completed (2026-03-26) |
| **Frontend WebSocket Hook (Zustand)** | ✅ Completed (2026-03-26) |
| **Industrial Intelligence Surface** | ✅ Completed (2026-03-27) |

## What's Been Implemented

### Date: 2026-03-27 - Industrial Intelligence Surface (Latest)

**P0: Rockwell Demo Surface - Single Page Intelligence Dashboard**

Answers in <60 seconds:
1. **Where is value being lost?** - VaR View ($213/day, $77,599 annual exposure)
2. **What should I do?** - Ranked Priorities with confidence labels
3. **What has been recovered?** - Verified Outcomes (savings + confidence)
4. **Is the system working?** - System Trust metrics (verification rate, actions validated, learning)

**Key Features:**
- Single-page unified dashboard (no tabs, no navigation)
- Real-time priority updates via WebSocket
- Inline expandable traceability (State → Priority → Intervention → Outcome)
- Multi-site scoped access (admins see all, operators see their sites)

**New Files:**
```
/app/frontend/src/components/IntelligenceSurface.jsx  - Main dashboard component
```

**New API Endpoints:**
- `GET /api/intelligence/summary` - Aggregate VAR and priority metrics
- `GET /api/intelligence/outcomes` - Verified outcomes with savings
- `GET /api/intelligence/trust` - System trust indicators
- `GET /api/intelligence/trace/{state_id}` - Full condition-to-outcome trace

**Testing:** Screenshot verification confirms all 4 sections working with real data.

---

### Date: 2026-03-26 - Frontend WebSocket Hook with Zustand

**P2: Frontend Real-time Integration**
- Zustand store for WebSocket state management
- Auto-connect on login with exponential backoff reconnection
- Resync on connect/reconnect for state reconciliation
- Heartbeat handling with automatic pong responses
- Connection status indicators (Live/Connecting/Reconnecting/Error)

**New Frontend Files:**
```
/app/frontend/src/stores/useRAMPStore.js     - Zustand WebSocket store
/app/frontend/src/hooks/useRAMPWebSocket.js  - React hooks for WS
/app/frontend/src/contexts/AuthContext.jsx   - Auth context for tokens
/app/frontend/src/components/ConnectionStatus.jsx - Connection indicator
/app/frontend/src/components/LoginForm.jsx   - Login form with demo creds
```

**Features:**
- Live Value at Risk calculation from WebSocket data
- Priority queue display with real-time updates
- Priority distribution badges (CRITICAL/HIGH/MEDIUM/LOW)
- Connection status in header and footer
- Sign out functionality

**Multi-site Scoped Access Verified:**
- WHERE lens correctly filters by user's site_ids
- Admin sees all priorities (4), Portfolio sees scoped (3)
- HOW lens already had scoping from previous implementation

**Testing:** 8/8 frontend features verified (iteration_9.json)

---

### Date: 2026-03-23 - Authentication & Role-based Access Control

**Phase 2: Supabase Auth Integration**
- Email/password authentication via Supabase Auth
- JWT tokens with role + scope (organisation_id, site_ids) embedded
- Three user roles: `operator` (HOW lens), `portfolio` (WHERE lens), `admin` (both)
- Default role: No access until admin assigns role

**API Endpoints:**
```
GET  /api/auth/status         - Auth configuration check
POST /api/auth/signup         - Register new user
POST /api/auth/signin         - Sign in, get token
GET  /api/auth/me             - Current user info
POST /api/auth/admin/assign-role      - Assign role (admin only)
PATCH /api/auth/admin/users/{id}/role - Update role
GET  /api/auth/admin/users            - List users
POST /api/auth/admin/bootstrap        - Bootstrap first admin
```

**Route Protection:**
- HOW routes (`/api/how/*`) require operator or admin role
- WHERE routes (`/api/where/*`) require portfolio or admin role
- System routes (`/api/system/*`) remain public (health checks, demos)
- Admin routes (`/api/auth/admin/*`) require admin role
- WebSocket endpoints require token via `?token=` query parameter

**Test Users:**
- Admin: rampadmin@gmail.com / RampAdmin2024!
- Operator: operator1@gmail.com / Operator2024!
- Portfolio: portfolio1@gmail.com / Portfolio2024!

**Testing:** 25/25 tests passed (21 HTTP + 4 WebSocket)

---

### Date: 2026-03-23 - Database Security (RLS)

**Phase 1A: RAMP Runtime Tables**
- Enabled RLS on all 15 `ramp_*` tables
- No broad policies - backend uses `postgres` role which bypasses RLS
- Direct API access via `anon`/`authenticated` roles blocked

**Phase 1B: High-risk Legacy Tables**
- Enabled RLS on 16 sensitive legacy tables
- Removed overly-permissive policies from `completed_assessments`
- Tables: payments, checkouts, otp_codes, consultant_*, assessment_*, etc.

**Protected Tables:** 31 total (15 RAMP + 16 legacy)

---

### Date: 2026-03-23 - WebSocket Real-time Updates

**P1: Real-time System Behaviour**
- WebSocket layer driven from event backbone (not separate logic)
- Lens rules apply in real-time (HOW/WHERE separation enforced)
- No raw internals exposed (confidence as label, no scores)
- Controlled/filtered event stream
- Explicit reconnect/resync behavior for clean client recovery

**WebSocket Endpoints:**
```
/ws/priorities      - Priority queue real-time updates
/ws/states/{asset}  - State changes for specific asset
/ws/outcomes        - Verified outcome notifications
GET /api/system/ws/status - Connection status
```

**Key Features:**
- Resync on connect provides current state snapshot
- Heartbeat every 30 seconds to keep connections alive
- Invalid asset returns error and closes connection
- Event backbone integration via `broadcaster.py`

**Files Added:**
- `/app/backend/ramp/websocket/__init__.py` (ConnectionManager, payload builders)
- `/app/backend/ramp/websocket/broadcaster.py` (Event handlers)

**Testing:** 14/14 backend tests passed

---

### Date: 2026-03-20 - State Transition & Escalation Logic

**P1: State Transition Tracking**
- States now properly transition (SUPERSEDED, ESCALATED) rather than just ending
- `transitioned_to_state_id` field tracks state chains
- Full transition history viewable via API
- `state_transitioned` events for audit trail

**API Endpoints:**
```
POST /api/system/states/transition - Transition from one state to another
GET /api/system/states/{state_id}/chain - Get full transition history
POST /api/system/states/{state_id}/end - End state with resolution type
```

**P2: Duration-based Escalation Logic**
- Automatic escalation based on state duration
- Configurable thresholds per state type:
  - DRIFT: 10min→MEDIUM, 8hr→HIGH, 2days→CRITICAL
  - DEGRADATION: 30min→MEDIUM, 4hr→HIGH, 1day→CRITICAL
  - SPIKE: 5min→HIGH, 1hr→CRITICAL
- Manual escalation for operator override
- `priority_escalated` events for audit trail

**API Endpoints:**
```
POST /api/system/escalation/run - Auto-escalate all eligible priorities
GET /api/system/escalation/candidates - Preview what would be escalated
POST /api/system/escalation/manual - Manual escalation by operator
```

**Files Added/Modified:**
- `/app/backend/ramp/services/escalation.py` (NEW)
- `/app/backend/ramp/db.py` (transition_state, get_state_transition_chain methods)
- `/app/backend/server.py` (6 new endpoints)

**Testing:** 15/16 backend tests passed (1 skipped)

---

### Date: 2026-03-20 - First 5 Minutes Experience Complete

**MAJOR: Guided Onboarding / Demo Experience**

Built a "First 5 Minutes" experience that immediately establishes credibility and demonstrates value:

**1. Guided Entry with Credibility**
- "Riverside Plant - Building A" with real asset names
- 4 assets across 3 systems (HVAC, Compressed Air, Process Cooling)
- 14 days of established baseline data
- Professional, realistic industrial context

**2. Current Value at Risk ($212.60/day)**
- Total VaR prominently displayed
- Breakdown by priority band:
  - HIGH: $151 (Main Air Compressor)
  - MEDIUM: $43 (Air Handling Unit 1)
  - LOW: $19 (Process Chiller 1)
- 100% verification rate indicator

**3. Prioritised Actions with Explanations**
- **#1 HIGH**: Main Air Compressor - 22% energy drift for 3 hours, 89% confidence
  - → "Inspect inlet filter and check for leaks in downstream piping"
- **#2 MEDIUM**: Air Handling Unit 1 - 12% efficiency drop for 6 hours, 76% confidence
  - → "Check filter differential pressure and consider filter replacement"
- **#3 LOW**: Process Chiller 1 - 8% energy drift for 45 minutes, 65% confidence
  - → "Monitor - may self-correct with load changes"

**4. Completed Loop (Proof)**
- VFD Coolant Pump: 18.5% energy drift detected 3 days ago
- Action: Calibration - recalibrated VFD frequency setpoints
- Outcome: ✓ Verified +1.3 kWh/hr savings with 91% confidence
- Time to verify: 1 hour

**5. Continuous Monitoring Narrative**
- "Continuous Monitoring Active" indicator
- 1 healthy asset, 3 in active state
- Learning enabled
- "Signal → State → Decision → Action → Learning" tagline

**6. Interactive Guided Tour**
- 6-step walkthrough: Welcome, Site, Completed Loop, Value at Risk, Actions, Continuous
- Continue/Back/Skip navigation
- Highlights relevant sections as user progresses

**API Endpoint:**
```
POST /api/system/demo/first-five-minutes
```
Creates complete realistic demo scenario (~22 seconds)

**Testing: 11/11 backend tests + all UI elements verified**

---

### Earlier: 2026-03-20 - Proof of Value View

Single-page dashboard answering:
- Where is value being lost? → VaR/day
- What to do about it? → Priority actions
- What has been recovered? → Verified outcomes
- Is the system working? → Loop integrity

### Earlier: 2026-03-20 - Verification & Learning Loop

Complete verification loop with guardrails:
- Configurable windows by state family/intervention type
- Always verifies against frozen baseline
- Never forces verification without sufficient data
- Explicit confidence on verified outcomes
- Learning records updated from verified outcomes

### Earlier: 2026-03-20 - PostgreSQL Migration

Migrated from MongoDB to Supabase/PostgreSQL with full relational chain verification.

---

## MVP Complete Status ✅

The core RAMP MVP is now **COMPLETE** with:

1. ✅ **Full Event Loop** — Signal → State → Decision → Action → Learning
2. ✅ **PostgreSQL Persistence** — Relational chain with SQL JOINs
3. ✅ **Verification Loop** — Configurable, guarded, with explicit confidence
4. ✅ **Proof of Value Surface** — Single view showing business impact
5. ✅ **First 5 Minutes Experience** — Onboarding/demo that pulls users in
6. ✅ **Database Security** — RLS enabled on all RAMP and high-risk legacy tables
7. ✅ **Authentication** — Supabase Auth with role-based access control

---

## Prioritized Backlog

### P0 (MVP) ✅ COMPLETE

### P1 (Productization) ✅ COMPLETE
- ✅ **State Transition Tracking** — States transition properly with audit trail
- ✅ **Duration-based Escalation** — Auto-escalate based on configurable thresholds
- ✅ **WebSocket Real-time Updates** — Priority queue, state changes, outcomes
- ✅ **Database Security (RLS)** — 31 tables protected
- ✅ **Authentication** — Supabase Auth with JWT tokens
- ✅ **Role-based Access Control** — operator/portfolio/admin roles with scope

### P2 (Expansion)
- ✅ **Frontend WebSocket hook** — Zustand store with reconnect handling (COMPLETED 2026-03-26)
- ✅ **Multi-site support** — Scoped access via user roles (COMPLETED 2026-03-26)
- Rule configuration admin UI
- Asset relationships/dependencies
- Advanced learning (baseline optimization from verified outcomes)
- Cross-asset benchmarking
- Outcome export (CSV/PDF)
- Asset-class-specific threshold modifiers
- Complex site configurations (demand-based energy tariffs)

## Next Tasks

**🔴 P0 — Immediate (Rockwell Demo)**

1. **Portfolio View (Multi-Site Intelligence)**
   - Default landing for portfolio users
   - Site ranking by VaR
   - Site ranking by realized savings
   - Aggregated portfolio metrics
   - "Where to focus next" guidance

2. **Polish Intelligence Surface**
   - Design agent for visual refinement (clarity > speed > credibility)
   - Ensure all data paths work correctly

**🟡 P1 — Minimal Admin (Pilot Support)**

3. **Admin UI (Limited)**
   - User roles + site assignment
   - Basic site creation/edit
   - Minimal user management

4. **Rule Configuration (Limited)**
   - Threshold tuning only
   - Verification window config

**🔵 P2 — Post-Pilot**

5. Asset relationships/dependencies
6. Cross-asset benchmarking
7. Learning optimization
8. Export/reporting

**🚫 Deferred**
- Full assessment modules (IBA, EPA, EMHA, EMRA)
- Accelerator schema integration
- Large-scale admin tooling
- Energy cost configuration

## Key Files

### Backend
- `/app/backend/server.py` — Main API with auth-protected endpoints
- `/app/backend/ramp/db.py` — Database operations including transition_state()
- `/app/backend/ramp/auth/` — Authentication module (auth, dependencies, service)
- `/app/backend/ramp/websocket/` — WebSocket connection manager and broadcaster
- `/app/backend/ramp/services/verification_scheduler.py` — Verification logic
- `/app/backend/ramp/services/verification_config.py` — Configurable windows
- `/app/backend/ramp/services/escalation.py` — Escalation service
- `/app/backend/ramp/websocket/__init__.py` — ConnectionManager, payload builders
- `/app/backend/ramp/websocket/broadcaster.py` — Event backbone integration

### Frontend
- `/app/frontend/src/App.js` — Main app with WebSocket integration and auth
- `/app/frontend/src/stores/useRAMPStore.js` — Zustand WebSocket state store
- `/app/frontend/src/hooks/useRAMPWebSocket.js` — React hooks for WebSocket
- `/app/frontend/src/contexts/AuthContext.jsx` — Auth context for token management
- `/app/frontend/src/components/ConnectionStatus.jsx` — Connection indicator
- `/app/frontend/src/components/LoginForm.jsx` — Login form with demo credentials

### Database
- `/app/backend/alembic/versions/ramp_001_initial_schema.py` — Schema
- `/app/backend/alembic/versions/ramp_002_add_retry_count.py` — Retry tracking

## Test Reports
- `/app/test_reports/iteration_2.json` — Verification system tests (25/25 passed)
- `/app/test_reports/iteration_3.json` — Proof of Value tests (13/13 passed)
- `/app/test_reports/iteration_4.json` — First Five Minutes tests (11/11 backend + all UI passed)
- `/app/test_reports/iteration_6.json` — State Transition & Escalation tests (15/16 passed)
- `/app/test_reports/iteration_7.json` — WebSocket tests (14/14 passed)
- `/app/test_reports/iteration_8.json` — Authentication & RBAC tests
- `/app/test_reports/iteration_9.json` — Frontend WebSocket Hook tests (8/8 passed)

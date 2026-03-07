# RouteReality — Technical Documentation

Crowdsourced bus arrival prediction system for Belfast.
Real‑time user reports are combined with historical patterns and static timetables to provide accurate, continuously updated arrival estimates. Live updates are pushed to subscribed clients via WebSockets.

---

## Stack

- Python 3.12 / FastAPI
- PostgreSQL via SQLAlchemy ORM
- Pydantic v2 for request validation
- WebSockets for real-time client updates

---

## 1. Introduction

RouteReality is a platform that demonstrates how crowdsourced data can improve public transport information. Passengers report when they board a bus; the system aggregates these reports, maintains a shared anchor of the best known arrival time for each stop on a given trip, and broadcasts updated predictions to all interested clients. The goal is to offer predictions that are more reliable than static timetables alone, especially in the face of real‑world delays.


## 2. System Architecture

The system follows a modular, service‑oriented design inside a monolithic FastAPI application.
Key components:

FastAPI – serves REST endpoints and handles WebSocket connections.

PostgreSQL – stores journeys, events, arrival anchors, prediction snapshots, and historical data.

SQLAlchemy ORM – abstracts database interactions.

Pydantic v2 – validates request/response schemas.

WebSockets – provide real‑time broadcasts to clients subscribed to a specific service.

All prediction logic is triggered by user‑reported events for now. The arrival time for a stop is derived from the most reliable source available (fresh user report, historical average, or static timetable). Confidence scores reflect the expected accuracy of the prediction.
```
app/
├── routers/
│   ├── Journey.py          # journey lifecycle endpoints
│   └── Broadcast.py        # WebSocket + ConnectionManager
├── Services/
│   ├── journeyService/
│   │   ├── journey_service.py     # start_journey orchestration
│   │   └── eventHandler.py        # state machine handlers
│   └── v2/
│       ├── arrival/
│       │   └── arrival_reporting_service.py
│       ├── anchor/
│       │   └── best_arrival_anchor_service.py
│       └── snapshot/
│           └── snapshot.py
├── models/
│   ├── Journey.py
│   ├── Event.py
│   ├── StopArrivalAnchors.py
│   └── PredictionSnapshot.py
├── schemas/
│   └── journey.py
└── utils/
    └── fetch_time.py       # timetable lookup
```

---

## Database Schema

### journeys
| Column | Type | Notes |
|---|---|---|
| id | VARCHAR PK | UUID |
| service_id | VARCHAR | e.g. `10A-I_20260304_1729` |
| route_id | VARCHAR FK | |
| start_stop_id | VARCHAR FK | ATCO code |
| end_stop_id | VARCHAR FK | ATCO code |
| status | VARCHAR | STARTED / ARRIVED / DELAYED / STOP_REACHED |
| planned_start_time | TIMESTAMPTZ | |
| official_start_time | TIMESTAMPTZ | from timetable |
| predicted_arrival | TIMESTAMPTZ | updated on each event |
| confidence | FLOAT | 0.0 – 1.0 |
| ended_at | TIMESTAMPTZ | null until STOP_REACHED |
| created_at / updated_at | TIMESTAMPTZ | |

### stop_arrival_anchors
One row per `(service_id, stop_id)`. Updated on every arrival report.

| Column | Type | Notes |
|---|---|---|
| id | VARCHAR PK | UUID |
| service_id | VARCHAR | composite unique with stop_id |
| stop_id | VARCHAR | |
| best_arrival_time | TIMESTAMPTZ | |
| confidence | FLOAT | |
| report_count | INTEGER | |
| last_reported_at | TIMESTAMPTZ | |
| source | VARCHAR | "user_report" |

**Important:** unique constraint must be on `(service_id, stop_id)` together, not `service_id` alone.

### prediction_snapshots
Immutable audit log. One row per prediction event.

| Column | Type |
|---|---|
| id | VARCHAR PK |
| journey_id | VARCHAR FK |
| service_id | VARCHAR |
| stop_id | VARCHAR |
| static_scheduled | TIMESTAMPTZ |
| predicted_arrival | TIMESTAMPTZ |
| user_reported_arrival | TIMESTAMPTZ |
| best_trusted_arrival | TIMESTAMPTZ |
| confidence | FLOAT |
| source_summary | VARCHAR |
| calculated_at | TIMESTAMPTZ |

### journey_events
| Column | Type |
|---|---|
| id | VARCHAR PK |
| journey_id | VARCHAR FK |
| stop_id | VARCHAR FK |
| type | VARCHAR |
| reported_time | TIMESTAMPTZ |
| created_at | TIMESTAMPTZ |

---

## API Reference

### POST /journeys/start
Start a new journey. Runs initial timetable prediction immediately.

**Request**
```json
{
  "route_id": "10A-I",
  "start_stop_id": "700000001429",
  "end_stop_id": "700000001789",
  "planned_start_time": "2026-03-04T17:00:00Z"
}
```

**Response 201**
```json
{
  "journey_id": "273ae664-...",
  "service_id": "10A-I_20260304_1729",
  "status": "STARTED",
  "predicted_arrival": "2026-03-04T17:23:00Z",
  "confidence": 0.35
}
```

---

### POST /journeys/{journey_id}/event
Report an event on an active journey.

**Request**
```json
{
  "event": "ARRIVED",
  "stop_id": "700000001429"
}
```

Valid events: `ARRIVED` `DELAYED` `STOP_REACHED`

**Response 200**
```json
{
  "journey_id": "273ae664-...",
  "status": "ARRIVED",
  "predicted_arrival": "2026-03-04T17:29:45Z",
  "confidence": 0.85,
  "last_event": "ARRIVED",
  "updated_at": "2026-03-04T17:29:46Z",
  "message": "Recorded ARRIVED"
}
```

**Error responses**

| Code | Reason |
|---|---|
| 400 | Invalid state transition |
| 404 | Journey not found or not active |
| 409 | Duplicate ARRIVED on same journey |
| 422 | Invalid event type or stop_id |

---

### WebSocket /ws/service/{service_id}
Subscribe to live updates for a service. Connect once, receive broadcasts as arrivals are reported.

**Broadcast payload**
```json
{
  "type": "arrival_update",
  "journey_id": "273ae664-...",
  "stop_id": "700000001429",
  "predicted_arrival": "2026-03-04T17:29:45Z",
  "confidence": 0.85,
  "report_count": 3,
  "timestamp": "2026-03-04T17:29:46Z",
  "status": "ARRIVED"
}
```

---

### GET /ws/stats
Returns active WebSocket connections per channel. Useful for debugging.

```json
{
  "service:10A-I_20260304_1729": 2
}
```

---

## State Machine

```
STARTED ──→ ARRIVED ──→ STOP_REACHED
   │                         ↑
   └──→ DELAYED ─────────────┘
```

`_get_owned_active_journey` filters on `status IN ('STARTED', 'ARRIVED', 'DELAYED')` and `ended_at IS NULL`. Completed journeys return 404 automatically — no explicit terminal state check needed.

---

## Prediction Logic

Priority order on every event:

1. **Fresh anchor** — `last_reported_at` within 60 minutes. Confidence +0.15.
2. **Historical hour-of-day average** — from `historical_delays`, minimum 5 samples. Confidence +0.05.
3. **Static timetable** — `get_closest_scheduled_time_to_now()`. No boost.

Confidence formula:
```
base (0.30 – 0.75 depending on source)
+ 0.15  anchor used
+ 0.05  historical used
- 0.08  per DELAYED event on this journey

floor: 0.25  ceiling: 0.98
```

Tolerance bands when blending report vs timetable:
- Within 12 min → use reported time, confidence 0.85
- 13–25 min → use reported time, confidence 0.65
- Over 25 min → use timetable, confidence 0.40

---

## Service Responsibilities

**`JourneyEventHandler`** — owns all status transitions. The only place `journey.status` is written.

**`ArrivalReportingService`** — records what happened. Updates anchor, saves snapshot, writes `predicted_arrival` and `confidence` back to journey, broadcasts. Does not touch `journey.status` or `journey.ended_at`.

**`BestArrivalAnchorService`** — upserts the shared anchor for `(service_id, stop_id)`. If anchor is under 120 minutes old, overwrites with new report. If stale, only updates if new confidence is higher.

**`ConnectionManager`** — manages WebSocket channels. Broadcasts use `asyncio.gather` across all subscribers concurrently. Dead connections pruned after each broadcast.

---

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable
export DATABASE_URL=postgresql://user:pass@localhost:5432/routereality

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload

# Run integration tests
python -m app.tests.full_loop_test
```

---

## Known Limitations

- Historical patterns split by hour only — no day-of-week segmentation yet
- Single stop per journey — multi-stop chaining not implemented
- Confidence uses additive boosts, not variance-weighted scoring
- No authentication on any endpoint
- No caching — all predictions hit Postgres directly

---

## Planned

- Day-type patterns (weekday / saturday / sunday) in historical table
- `delay_count` column on `Journey` for per-journey confidence penalty
- Variance-based confidence scoring
- Multi-stop journey support with `current_stop_id`
- Redis cache for anchors and historical lookups
- JWT auth
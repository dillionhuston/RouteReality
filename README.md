# RouteReality: Real-Time Journey Tracking Engine

**Live demo:** [https://routereality.co.uk](https://routereality.co.uk) – Community-powered bus predictions for Belfast & Northern Ireland.


**RouteReality** is an open-source, community-powered journey tracking and public transport prediction engine.

It combines static timetables, historical journey data, and real-world passenger reports to produce live arrival estimates with confidence scores. The result is a transport experience that gets better as more people use it.

This repository shows the exact system running in Belfast, you can fork it and adapt it to your own city or use case.


## Why RouteReality?

Traditional timetables tell you when a bus is *supposed* to arrive. RouteReality helps show when it is *likely* to arrive.

Passengers can report real-world events such as:
- A bus arriving at a stop
- A journey being delayed
- A destination being reached

These reports are combined with historical data and timetable information to create better predictions for everyone.

The more people contribute, the more useful the system becomes.

## Features

### Real-time predictions

RouteReality uses a time-sensitive weighted average to prioritise recent reports and account for real-world delay patterns caused by:

- Traffic
- Weather
- School runs
- Time of day
- Public events
- Recurring route delays

### Community-powered data

Every report helps improve future predictions. Users can contribute journey events and see their impact across the network.

### Stop-based arrivals

View upcoming buses at any stop, rather than being limited to a single tracked journey.

### Confidence scores

Every prediction includes a confidence score based on:

- The number of recent reports
- The age of those reports
- The consistency of reported journey data
- Whether the prediction uses community data or the static timetable fallback

### Points and leaderboards

Reward users for submitting useful, accurate journey information with points, badges, and community rankings.

### Live updates

WebSockets and web push notifications provide real-time journey status updates.

### Secure authentication

JWT authentication protects user actions while keeping basic route, stop, arrival, and leaderboard data publicly readable.

### Adaptable architecture

RouteReality can be adapted for:

- Buses
- Trains
- Trams
- Ferries
- Campus shuttles
- Event transport
- Delivery fleets
- Logistics systems

---

## How It Works

RouteReality combines three sources of information:

1. **Live user reports**  
   Recent events such as arrivals, delays, and completed journeys.

2. **Historical journey data**  
   Previous journeys used to identify recurring route patterns.

3. **Static timetable data**  
   A reliable fallback when there is not enough recent community data.

Recent reports receive the greatest weight. Older journey data provides additional context, while the timetable is used as the final fallback.

## Points & Leaderboard System

Users earn points by contributing real-time journey data. The system tracks every event and awards points based on:

| Action | Points | Description |
|--------|--------|-------------|
| Start a journey | 5 | Creating a new journey tracking session |
| Report ARRIVED | 10 | Confirming bus arrival at start stop |
| Report DELAYED | 15 | Reporting a delay (helps others adjust plans) |
| Report STOP_REACHED | 20 | Completing a journey at destination |
| First report of the day | +5 bonus | Daily active user bonus |
| High-confidence prediction | +2 extra | When your data matches final outcome |

**Leaderboard** – The community leaderboard shows:

- Top 20 users by total points (all time)
- Top 10 users by weekly points
- Recent activity badges (Hot Streak, Early Reporter, Reliable Source)

**User stats endpoint** – Authenticated users can see:

- Total points earned
- Number of journeys contributed
- Number of events submitted
- Current rank on leaderboard
- Points breakdown by event type

```bash
GET /users/stats          # Your personal stats
GET /users/leaderboard    # Community leaderboard
```

Points never expire. The system encourages frequent, accurate reporting, more data means better predictions for everyone.


## Screenshots (Belfast UI)

Home screen – start journey map  
Route view with event reporting  
Active journey screen

*(Images are stored in the `images/` folder of the repository.)*

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 15+
- (Optional) Redis for WebSocket scaling

### Installation

```bash
git clone https://github.com/dillionhuston/RouteReality.git
cd RouteReality

python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env – set DATABASE_URL, JWT_SECRET_KEY, VAPID keys, etc.
```

### Generate VAPID keys (for push notifications)

```bash
python gen_vapid.py
# Copy the generated keys into your .env file
```

### Database setup

```bash
createdb journey_tracking
alembic upgrade head
```

### Run the server

```bash
uvicorn main:app --reload
```

API is available at `http://localhost:8000`  
Interactive docs at `http://localhost:8000/docs`

## API Usage (V2)

### Public endpoints

- `GET /route/routes` – list all routes
- `GET /route/routes/{route_id}/stops` – stops for a route
- `GET /arrivals/stop/{stop_id}` – all upcoming buses at a stop (V2)
- `GET /users/leaderboard` – community leaderboard (public read)

### Authenticated endpoints (JWT required)

- `POST /journeys/start`
- `POST /journeys/{journey_id}/event`
- `GET /users/stats` – your contribution stats and points

### Example: start a journey

```bash
POST /journeys/start
{
  "route_id": "16",
  "start_stop_id": "490000001",
  "end_stop_id": "490000050",
  "planned_start_time": "2026-04-08T09:00:00Z"
}
```

### Example: submit an event

```bash
POST /journeys/{journey_id}/event
{
  "event": "ARRIVED"   // or "DELAYED", "STOP_REACHED"
}
```

### Example response for user stats

```json
{
  "total_points": 245,
  "journeys_contributed": 12,
  "events_submitted": 34,
  "current_rank": 7,
  "breakdown": {
    "ARRIVED": 8,
    "DELAYED": 5,
    "STOP_REACHED": 21
  }
}
```

WebSocket and Web Push endpoints are also available for real-time updates.

## Prediction Engine Details

The engine uses a **time-sensitive weighted average** because bus delays are not random. Traffic, weather, school runs, and public events create patterns.

- Most recent report (e.g. 2 minutes ago) gets the highest weight.
- Completed journeys from the last 30–60 minutes get medium weight.
- Static timetable is the final fallback.

This approach has proven more reliable than a simple median or pure machine learning for real-world transit with variable data density.

## Journey State Machine

```
STARTED → DELAYED → ARRIVED → STOP_REACHED
```

- **STARTED** – journey created, waiting for bus
- **DELAYED** – user reports a delay
- **ARRIVED** – bus has arrived at the start stop
- **STOP_REACHED** – journey completed at destination

## Project Structure

```
app/
├── models/              # SQLAlchemy models (Journey, Route, Stop, User, UserStats, etc.)
├── schemas/             # Pydantic schemas for validation
├── Services/
│   ├── journeyService/  # Journey business logic and event handling
│   ├── Prediction/      # Prediction engine (improved in V2)
│   ├── notification/    # Web push and WebSocket broadcasting (V2)
│   └── points/          # Points calculation and leaderboard logic (V2)
└── routes/              # API routers (auth, stats, arrivals, etc.)
```

## Technical Decisions

- **SQLAlchemy** – clean database abstraction with FastAPI dependency injection.
- **String IDs** – uses real public identifiers (route numbers, ATCO codes) for easy recognition and GTFS compatibility.
- **Weighted average** – best for modelling real-time drift and non-random delays.
- **Data source tracking** – distinguishes timetable vs user data so trust increases with more community reports.
- **Points gamification** – encourages frequent, quality contributions; leaderboard fosters community engagement.

## Configuration

Key environment variables in `.env`:

```
DATABASE_URL=postgresql://user:password@localhost/journey_tracking
JWT_SECRET_KEY=your_secret_key
VAPID_PRIVATE_KEY=...
VAPID_PUBLIC_KEY=...
VAPID_SUBJECT=mailto:your@email.com
```

## Known Limitations

- Some routes or stops may have map overlaps on external providers (e.g. Google Maps).
- Prediction confidence is lower in areas with few user reports.
- Accuracy and coverage grow with community usage.
- Points system is opt-in via user registration (anonymous journeys earn no points).

## Contributing

We welcome contributions – especially from developers who want to adapt RouteReality for their own city or niche.

### Good areas to help

- Improving the prediction engine (time-of-day patterns, weather, ML fallback)
- Adding new timetable importers (GTFS, custom APIs)
- Frontend work (React, Vue, PWA) for V2 features (stats, leaderboard, push notifications)
- Expanding test coverage
- Documentation and architecture diagrams
- Multi-city support
- Alternative points formulas or badge systems

### Getting started

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Make your changes.
4. Add or update tests where possible.
5. Submit a pull request.

Follow PEP 8, use type hints, and keep functions focused.


## License

MIT License  
Copyright (c) 2026 Dillon Huston

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

Built with FastAPI, SQLAlchemy, and PostgreSQL. Contributions welcome.  
Let's make better real-time journey tracking available everywhere.

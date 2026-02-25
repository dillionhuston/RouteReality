# Changelog

All  changes to RouteReality will be documented in this file.


## [1.3.0] - 2026-02-21 – Stability & Cleanup Release

### Added
- Three UI screenshots to README (start journey map, event reporting, active journey screen)
- `JourneyEventType.PENDING` to support clearer initial journey states
- Structured logging throughout prediction and event handling
- Richer prediction payload: `source`, `recent_event_count`, `historical_count`
- `recent_trips` limit and counts in status endpoints

### Changed
- Prediction interface: renamed `static_dt` → `reference_time`, improved fallback safety
- Centralized prediction refresh with new `update_prediction` helper
- Tightened event state transitions and validation
- Adjusted `predicted_arrival` handling on `DELAYED` events
- Removed unnecessary `.isoformat()` conversions in API responses
- CIF timetable path now loaded from environment variable
- Consistent 3-tuple return from `get_closest_scheduled_time_to_now`

### Fixed
- Safe unpacking of timetable results with proper type hints
- Edge cases causing negative ETAs after live overrides
- Prediction failures now logged gracefully instead of crashing
- Resource validation (route/stops) with explicit 404/400 status codes
- Various minor bugs across services and API routes
- Type annotations and schema consistency

### Improved
- Confidence scoring accuracy under low-data conditions
- Internal service boundaries for easier future maintenance
- Debuggability with better logging at key decision points
- Overall system stability and predictability

This release focuses purely on hardening the existing system. It lays solid groundwork for v2 features (authentication, real-time updates, richer  modelling).

## [1.2.0] - 2026-02-14 – Backend Updates and Map Support

### Added
- Proper "bus arrived" / "bus departed" reporting with immediate server-side effect
- Endpoint returning latest confirmed event for a route/stop
- Instant propagation of reported events to update route/stop status for all users
- Frontend auto-polling every 20s on route/stop views (near-live feel)
- Smarter next-bus adjustment when timetable is missed and departure reported

### Fixed
- Negative arrival times after departure reports
- "Bus coming in 0 min" spam when timetable stale and no live data

### Changed
- Prediction engine no longer shows impossible future times after confirmed departure

### Limitations (still present)
- Accuracy depends heavily on user reporting volume
- No push notifications — polling only
- Predictions remain rough without recent reports

Keep reporting events — more data = smarter ETAs.

## [1.1.0] - 2026-02-08

### Added
- Weighted averaging of recent journey data
- Confidence scoring for arrival predictions
- Clear visual distinction between predicted times and user-reported events in UI

### Changed
- Prediction logic now strongly prioritizes recent user data over static timetables
- Improved fallback when user data is sparse or missing

### Fixed
- Edge cases with no recent journey data
- Journey creation process improvements
- Better handling of invalid input data

## [1.0.0] - 2026-02-01 – Initial Release

### Added
- Static timetable-based bus arrival predictions
- Stop and route search functionality
- Backend prediction service
- User-reported arrival and delay events
- Public API for fetching stop times and predictions
- Initial frontend for viewing routes and arrivals

[1.3.0]: https://github.com/dillionhuston/RouteReality/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/dillionhuston/RouteReality/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/dillionhuston/RouteReality/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/dillionhuston/RouteReality/releases/tag/v1.0.0

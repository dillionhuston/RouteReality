## Chagelog

# V1.0 - Initial release - 01-02-2026

### Added 
- Static timetable-based bus arrival predictions
- Stop and route search functionality 
- Backend prediction service
- User-reported arrival and delay events 
- Public API for fetching stop times and  predictions
- Initial frontend for viewing routes and arrivals



## V1.1 - 08-02-2026

## Added
- Weighted averaging of recent journey data
- Confidence scoring for arrival predictions
- Clear distinction between predicted times and user-reported events/times in the UI

## Changed 
- Predition logic now prioritises revent user data over static timetables
- Improved fallback behaviour when user data is sparse or unavailable

- Improved handling edge cases where no recent journey data exists
- Improved creating journey process
- Better error handling in terms of invalid data 



## v1.2 — Backend Updates and map support, Feb 14, 2026

## Added
- Users can now properly report "bus arrived" / "bus departed" — server takes it seriously
- New endpoint returns latest confirmed event for route 
- Reported events now instantly update route/stop status for everyone else
- Prediction no longer tells people the bus is coming in -2 min after someone already said it left
- Frontend auto-polls every 20s when you're staring at a route/stop — feels almost live
- If timetable is already missed and someone reports departure → we push the next bus forward instead of lying

## Fixed
- No more negative arrival times after a departure report
- Less "bus coming in 0 min" when timetable is stale and no live data

## Limitations
- Accuracy is only good if enough people bother reporting
- No push notifications yet — still gotta stare at the screen and wait for poll
- Prediction still rough when no recent reports and timetable is way off

Keep reporting — the more people use it, the less stupid the ETAs become.
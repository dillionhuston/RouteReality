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

## Fixed 
- Improved handling edge cases where no recent journey data exists
- Improved creating journey process
- Better error handling in terms of invalid data 
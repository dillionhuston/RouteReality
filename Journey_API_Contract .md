# API Contract – Routes & Journeys

Base URL: `/api` i have not added this yet so bare with me

All endpoints use **JSON**. Authentication is going to be handeld through JWT Anon token

---

## Routes

### GET `/route/routes`
Retrieve all bus routes.
e.g Belfast -> Lisburn

**Response – 200**
```json
[
  {
    "id": "string",
    "name": "string"
  }
]
```

**Notes**
- `id` is the route identifier (string / UUID depending on backend)

---

### GET `/route/routes/{route_id}/stops`
Fetch all stops along a route in sequence order.

**Path Parameters**
| Name | Type | Required | Description |
|----|----|----|----|
| route_id | string | yes | Route identifier |

**Response – 200**
```json
[
  {
    "id": "string",
    "name": "string",
    "sequence": 1
  }
]
```

**Response – 404**
```json
{
  "detail": "No stops found for this route"
}
```

**Notes**
- Results are ordered by `sequence`
- Each stop belongs to the given route

---

## Journeys

### POST `/journeys/start`
Start a new journey.

**Request Body**
```json
{
  "route_id": "string",
  "start_stop_id": "string",
  "end_stop_id": "string"
}
```

**Response – 200**
```json
[
  {
    "id": "uuid",
    "predicted_status": "string",
    "predicted_arrival": "ISO-8601 datetime"
  }
]
```

**Notes**
- Returns an array for consistency with backend implementation
- `predicted_arrival` is server-calculated

---

### POST `/journeys/{journey_id}/event`
Add an event to an active journey (e.g. arrived, delayed, stop reached).

**Path Parameters**
| Name | Type | Required | Description |
|----|----|----|----|
| journey_id | uuid | yes | Journey identifier |

**Request Body**
```json
{
  "type": "ARRIVED | DELAYED | STOP_REACHED",
  "stop_id": "string",
  "timestamp": "ISO-8601 datetime"
}
```

**Response – 200**
```json
{
  "journey_id": "uuid",
  "status": "string"
}
```

**Notes**
- `type` is an enum controlled by backend
- Status is recalculated after each event

---

## Enums

### JourneyEventType
```ts
ARRIVED
DELAYED
STOP_REACHED
```

---

## General Conventions
- All timestamps are **ISO-8601**
- UUIDs are returned as strings
- Errors follow FastAPI default format

---

Any issues. Messagee me please. Again this may look small, it is what is needed for V1 data collection


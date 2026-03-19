import requests

BASE = "http://108.129.33.20:8000"
# ── helpers ──────────────────────────────────────────────────────────────────

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

def print_result(label, res):
    ok = "OK" if res.ok else "FAIL"
    print(f"[{ok}] {label} — {res.status_code}")
    if not res.ok:
        print(f"      {res.text[:200]}")

# ── auth ──────────────────────────────────────────────────────────────────────

def register(email, username, password):
    res = requests.post(f"{BASE}/auth/register", json={
        "email": email,
        "username": username,
        "password": password
    })
    print_result("register", res)
    return res

def login(email, password):
    res = requests.post(f"{BASE}/auth/login", json={
        "email": email,
        "password": password
    })
    print_result("login", res)
    return res.json().get("access_token") if res.ok else None

def anonymous():
    res = requests.post(f"{BASE}/auth/anonymous")
    print_result("anonymous login", res)
    return res.json().get("access_token") if res.ok else None

# ── routes ────────────────────────────────────────────────────────────────────

def get_routes(token):
    res = requests.get(f"{BASE}/route/routes", headers=auth_headers(token))
    print_result("get routes", res)
    return res.json() if res.ok else []

def get_stops(token, route_id):
    res = requests.get(f"{BASE}/route/{route_id}/stops", headers=auth_headers(token))
    print_result(f"get stops for route {route_id}", res)
    return res.json() if res.ok else []

# ── journeys ──────────────────────────────────────────────────────────────────

def start_journey(token, route_id, start_stop_id, end_stop_id):
    res = requests.post(f"{BASE}/journeys/start", headers=auth_headers(token), json={
        "route_id": route_id,
        "start_stop_id": start_stop_id,
        "end_stop_id": end_stop_id
    })
    print_result("start journey", res)
    return res.json().get("journey_id") if res.ok else None

def add_event(token, journey_id, event_type):
    res = requests.post(
        f"{BASE}/journeys/{journey_id}/event",
        headers=auth_headers(token),
        json={"event": event_type}
    )
    print_result(f"add event {event_type}", res)
    return res

# ── push ──────────────────────────────────────────────────────────────────────

def subscribe_push(token, service_id):
    res = requests.post(f"{BASE}/push/subscribe", headers=auth_headers(token), json={
        "service_id": service_id,
        "endpoint": "https://fcm.googleapis.com/test-endpoint-123",
        "keys": {"p256dh": "fake-key", "auth": "fake-auth"}
    })
    print_result("push subscribe", res)
    return res

def unsubscribe_push(token):
    res = requests.post(
        f"{BASE}/push/unsubscribe",
        headers=auth_headers(token),
        params={"endpoint": "https://fcm.googleapis.com/test-endpoint-123"}
    )
    print_result("push unsubscribe", res)
    return res

# ── auth guard checks ─────────────────────────────────────────────────────────

def check_protected_without_token():
    print("\n-- checking protected routes reject unauthenticated requests --")
    endpoints = [
        ("GET",  f"{BASE}/route/routes"),
        ("POST", f"{BASE}/journeys/start"),
    ]
    for method, url in endpoints:
        res = requests.request(method, url)
        ok = "OK" if res.status_code == 401 else "FAIL"
        print(f"[{ok}] {method} {url} — expected 401, got {res.status_code}")

# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n=== auth ===")
    register("test@example.com", "testuser", "password123")
    token = login("test@example.com", "password123")
    anon_token = anonymous()

    if not token:
        print("login failed, stopping")
        exit(1)

    print("\n=== routes ===")
    routes = get_routes(token)
    route_id = routes[0]["id"] if routes else None

    if route_id:
        stops = get_stops(token, route_id)
        start_stop = stops[0]["id"] if len(stops) > 0 else None
        end_stop   = stops[-1]["id"] if len(stops) > 1 else None
    else:
        start_stop = end_stop = None

    print("\n=== journey ===")
    journey_id = None
    if route_id and start_stop and end_stop:
        journey_id = start_journey(token, route_id, start_stop, end_stop)

    if journey_id:
        add_event(token, journey_id, "ARRIVED")
        add_event(token, journey_id, "DELAYED")
        add_event(token, journey_id, "STOP_REACHED")

    print("\n=== push ===")
    if route_id:
        subscribe_push(token, route_id)
        unsubscribe_push(token)

    print("\n=== anon token works on protected routes ===")
    if anon_token:
        get_routes(anon_token)

    check_protected_without_token()

    print("\ndone")
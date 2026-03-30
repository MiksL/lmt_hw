import requests
import time

BASE_URL = "http://localhost:8000"

threats = [ # Should be intercepted by a jet around 57.251040, 24.516280
    {
        "track_id": "TEST-THREAT",
        "speed_ms": 600,
        "altitude_m": 1000,
        "heading_deg": 212,
        "latitude": 57.5,
        "longitude": 24.8,
        "report_time": 1
    }
]

for threat in threats:
    r = requests.post(f"{BASE_URL}/api/radar", json=threat)
    print(f"[SIM] {threat['track_id']} — {r.status_code}")

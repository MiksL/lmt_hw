import requests
import sys

BASE_URL = "http://localhost:8000"

threats = [
    # Heading towards Poligons
    {
        "track_id": "Poligons-1",
        "speed_ms": 900,
        "altitude_m": 5000,
        "heading_deg": 220,
        "latitude": 57.4,
        "longitude": 24.7,
        "report_time": 1
    },
    # Heading towards RIX
    {
        "track_id": "RIX-1",
        "speed_ms": 350,
        "altitude_m": 3000,
        "heading_deg": 245,
        "latitude": 57.05,
        "longitude": 24.6,
        "report_time": 1
    },
    # Heading towards Riga HES
    {
        "track_id": "HES-1",
        "speed_ms": 200,
        "altitude_m": 800,
        "heading_deg": 195,
        "latitude": 57.05,
        "longitude": 24.35,
        "report_time": 1
    },
    # Heading towards Riga Base
    {
        "track_id": "BASE-1",
        "speed_ms": 600,
        "altitude_m": 1000,
        "heading_deg": 212,
        "latitude": 57.5,
        "longitude": 24.8,
        "report_time": 1
    },
    # Heading towards poligons
    {
        "track_id": "Poligons-2",
        "speed_ms": 1500,
        "altitude_m": 15000,
        "heading_deg": 210,
        "latitude": 57.9,
        "longitude": 25.2,
        "report_time": 1
    },
]

selected = sys.argv[1:] if len(sys.argv) > 1 else [t["track_id"] for t in threats]

for threat in threats:
    if threat["track_id"] in selected:
        r = requests.post(f"{BASE_URL}/api/radar", json=threat)
        print(f"[SIM] {threat['track_id']} — {r.status_code}")

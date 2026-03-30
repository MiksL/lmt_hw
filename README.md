## Running with Docker

```bash
docker compose up --build
```

## Usage

- **Map**: http://localhost:8000/map
- **Simulate threats**: `python simulate.py`
- **Simulate specific threats**: `python simulate.py RIX-1 BASE-1`
- **POST a custom threat**:

```bash
curl -X POST http://localhost:8000/api/radar \
  -H "Content-Type: application/json" \
  -d '{
    "track_id":    "TEST_THREAT",
    "speed_ms":    600,
    "altitude_m":  1000,
    "heading_deg": 212,
    "latitude":    57.5,
    "longitude":   24.8,
    "report_time": 1
  }'
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/map` | Interactive map |
| GET | `/api/objects` | All active objects |
| GET | `/api/intercepts` | Active intercepts |
| GET | `/api/intercepts?all=1` | All intercepts, current and destroyed |
| POST | `/api/radar` | Add a new moving threat |

## Running tests

```bash
pytest tests/ -v
```

### Running simulate.py tests

simulate.py can accept arguments - specific threat IDs
```bash
# Send all threats
python simulate.py

# Send only RIX-1
python simulate.py RIX-1

# Send multiple specific threats
python simulate.py RIX-1 HES-1
```

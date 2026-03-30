from radar import coordinate_distance_to_m, calculate_new_position, classify_threat, is_in_range, ThreatLevel, LAT_M_PER_DEGREE, LON_M_PER_DEGREE
from intercept import calculate_cost, latlon_to_meters, meters_to_latlon, time_to_intercept_threat, find_cheapest_interceptor

# AI tests

# --- radar.py tests ---

def test_classify_not_threat_slow():
    assert classify_threat(10, 500) == ThreatLevel.NOT_THREAT

def test_classify_not_threat_low():
    assert classify_threat(200, 100) == ThreatLevel.NOT_THREAT

def test_classify_caution():
    assert classify_threat(20, 300) == ThreatLevel.CAUTION

def test_classify_threat():
    assert classify_threat(200, 300) == ThreatLevel.THREAT

def test_coordinate_distance():
    dist = coordinate_distance_to_m(57.0, 24.0, 57.001, 24.001)
    assert 120 < dist < 140

def test_position_east():
    lat, lon = calculate_new_position(57.0, 24.0, 100, 90)  # East
    assert abs(lat - 57.0) < 0.0001
    assert lon > 24.0

def test_position_north():
    lat, lon = calculate_new_position(57.0, 24.0, 100, 0)  # North
    assert lat > 57.0
    assert abs(lon - 24.0) < 0.0001

def test_is_in_range():
    assert is_in_range(57.0, 24.0, 57.001, 24.001, 100000) == True
    assert is_in_range(57.0, 24.0, 58.0, 25.0, 1000) == False

# --- intercept.py tests ---

def test_cost_flat():
    interceptor = {"cost_type": "flat", "cost": 10000, "speed_ms": 80}
    assert calculate_cost(interceptor, 5000) == 10000

def test_cost_per_minute():
    interceptor = {"cost_type": "per_minute", "cost": 1000, "speed_ms": 700}
    cost = calculate_cost(interceptor, 7000)  # 10s one way, 20s round trip
    assert abs(cost - 333.33) < 1  # (20/60) * 1000

def test_latlon_meters_roundtrip():
    base_lat, base_lon = 57.0, 24.0
    x, y = latlon_to_meters(57.1, 24.1, base_lat, base_lon)
    lat, lon = meters_to_latlon(x, y, base_lat, base_lon)
    assert abs(lat - 57.1) < 1e-9
    assert abs(lon - 24.1) < 1e-9

def test_intercept_time_returns_positive():
    # Threat at 10km east, moving south, interceptor faster
    x0, y0 = 10000, 0
    vx, vy = 0, -200  # 200 m/s south
    t = time_to_intercept_threat(x0, y0, vx, vy, 1500)
    assert t is not None
    assert t > 0

def test_find_cheapest_interceptor_picks_cheapest():
    base = {'latitude': 57.0, 'longitude': 24.0}
    obj = {'latitude': 57.3, 'longitude': 24.0, 'altitude_m': 1000, 'speed_ms': 300, 'heading_deg': 180}
    targets = [{'latitude': 57.0, 'longitude': 24.0, 'exclusion_zone_m': 5000}]  # Base itself
    interceptors = [
        {'type': 'rocket', 'speed_ms': 1500, 'range_m': 10000000, 'max_altitude_m': 300000, 'cost': 300000, 'cost_type': 'flat'},
        {'type': 'jet', 'speed_ms': 700, 'range_m': 3500000, 'max_altitude_m': 15000, 'cost': 1000, 'cost_type': 'per_minute'},
    ]
    result = find_cheapest_interceptor(obj, interceptors, targets, base)
    assert result is not None
    assert result['interceptor_type'] == 'jet'  # Jet is cheaper than rocket

def test_find_cheapest_interceptor_none_when_no_target_threatened():
    base = {'latitude': 57.0, 'longitude': 24.0}
    obj = {'latitude': 57.3, 'longitude': 24.0, 'altitude_m': 1000, 'speed_ms': 300, 'heading_deg': 90}  # Moving east, away from targets
    targets = [{'latitude': 57.0, 'longitude': 24.0, 'exclusion_zone_m': 5000}]
    interceptors = [
        {'type': 'rocket', 'speed_ms': 1500, 'range_m': 10000000, 'max_altitude_m': 300000, 'cost': 300000, 'cost_type': 'flat'},
    ]
    result = find_cheapest_interceptor(obj, interceptors, targets, base)
    assert result is None

def test_find_cheapest_interceptor_respects_altitude():
    base = {'latitude': 57.0, 'longitude': 24.0}
    obj = {'latitude': 57.3, 'longitude': 24.0, 'altitude_m': 5000, 'speed_ms': 300, 'heading_deg': 180}
    targets = [{'latitude': 57.0, 'longitude': 24.0, 'exclusion_zone_m': 5000}]
    interceptors = [
        {'type': 'drone', 'speed_ms': 80, 'range_m': 30000, 'max_altitude_m': 2000, 'cost': 10000, 'cost_type': 'flat'},  # Can't reach 5000m
    ]
    result = find_cheapest_interceptor(obj, interceptors, targets, base)
    assert result is None

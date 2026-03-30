import math
from radar import coordinate_distance_to_m, calculate_new_position, LAT_M_PER_DEGREE, LON_M_PER_DEGREE

def calculate_cost(interceptor, distance_m):
    if interceptor["cost_type"] == "flat":
        return interceptor["cost"] # Flat cost for everything but the jet
    travel_time = (distance_m / interceptor["speed_ms"]) / 60  # One-way travel time in minutes
    return (travel_time * 2) * interceptor["cost"]  # Round trip cost
    
def latlon_to_meters(lat, lon, base_lat, base_lon): # Convert latitude and longitude to x/y coordinates in meters relative to base
    x = (lon - base_lon) * LON_M_PER_DEGREE
    y = (lat - base_lat) * LAT_M_PER_DEGREE
    return x, y

def meters_to_latlon(x, y, base_lat, base_lon): # Convert x/y coordinates in meters back to latitude and longitude
    lat = base_lat + y / LAT_M_PER_DEGREE
    lon = base_lon + x / LON_M_PER_DEGREE
    return lat, lon

# AI method
def _solve_quadratic(a, b, c): # Solves aT^2 + bT + c = 0, returns smallest positive root or None (if no positive root can be found)
    if abs(a) < 1e-9:
        if abs(b) < 1e-9:
            return None
        t = -c / b
        return t if t > 0 else None

    D = b*b - 4*a*c
    if D < 0:
        return None # no real roots, cannot be intercepted

    sqrt_D = math.sqrt(D)
    t1 = (-b - sqrt_D) / (2*a)
    t2 = (-b + sqrt_D) / (2*a)

    candidates = [t for t in (t1, t2) if t > 0]
    return min(candidates) if candidates else None

def time_to_enter_zone(x0, y0, vx, vy, target_x, target_y, radius):
    """time when threat first enters exclusion zone of target"""
    # relative position of threat to target at the start
    dx = x0 - target_x
    dy = y0 - target_y

    if dx*dx + dy*dy <= radius*radius:
        return 0.0 # threat is already in the zone

    a = vx*vx + vy*vy # relative speed of threat towards target
    b = 2*(dx*vx + dy*vy) # relative velocity towards target
    c = dx*dx + dy*dy - radius*radius # c = dx^2 + dy^2 - r^2. r - radius of exclusion zone
    return _solve_quadratic(a, b, c)

def time_to_intercept_threat(x0, y0, vx, vy, interceptor_speed):
    """Earliest possible moment when interceptor can reach threat."""
    a = vx*vx + vy*vy - interceptor_speed**2 # relative speed of threat to interceptor
    b = 2*(x0*vx + y0*vy) # relative velocity
    c = x0*x0 + y0*y0 # distance between threat and base squared
    return _solve_quadratic(a, b, c)

def find_cheapest_interceptor(obj, interceptors, targets, base):
    base_lat = base['latitude']
    base_lon = base['longitude']
    altitude = obj['altitude_m']

    x0, y0 = latlon_to_meters(obj['latitude'], obj['longitude'], base_lat, base_lon) # Convert lat/lon to meters relative to base
    heading_rad = math.radians(obj['heading_deg']) # Heading converted from degrees to radians
    
    # AI - velocity components of the threat in x and y directions
    vx = obj['speed_ms'] * math.sin(heading_rad)
    vy = obj['speed_ms'] * math.cos(heading_rad)

    # Find earliest deadline across all targets
    Ttime_to_enter_zone = None
    for target in targets:
        tx, ty = latlon_to_meters(target['latitude'], target['longitude'], base_lat, base_lon)
        t = time_to_enter_zone(x0, y0, vx, vy, tx, ty, target['exclusion_zone_m'])
        if t is not None: # If threat enters the zone of target
            if Ttime_to_enter_zone is None or t < Ttime_to_enter_zone: # AI - Find the earliest time to enter exclusion zone
                Ttime_to_enter_zone = t

    if Ttime_to_enter_zone is None:
        return None # Threat doesn't reach any protected target

    # Find cheapest possible interceptor that arrives before deadline
    best = None
    for interceptor in interceptors:
        if interceptor['max_altitude_m'] < altitude:
            continue # can't reach given altitude

        T_i = time_to_intercept_threat(x0, y0, vx, vy, interceptor['speed_ms'])

        if T_i is None or T_i > Ttime_to_enter_zone:
            continue # can't intercept in time

        ix = x0 + vx * T_i
        iy = y0 + vy * T_i
        dist = math.sqrt(ix*ix + iy*iy)
        
        
        if dist > interceptor['range_m']:
            continue            # intercept point out of range

        cost = calculate_cost(interceptor, dist)
        if best is None or cost < best['cost']: # If interceptor is cheaper than current best
            ilat, ilon = meters_to_latlon(ix, iy, base_lat, base_lon) # Distance converted to lat/lon
            best = {
                'interceptor_type': interceptor['type'],
                'intercept_lat':    ilat,
                'intercept_lon':    ilon,
                'intercept_time_s': T_i,  # Continuous time — keeps interceptor/threat progress proportional
                'cost':             cost
            }

    return best
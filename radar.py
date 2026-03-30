import math
from enum import IntEnum

# Threat level enum
class ThreatLevel(IntEnum):
    NOT_THREAT = 0
    CAUTION = 1
    POTENTIAL_THREAT = 2
    THREAT = 3
    
'''
    1 deg latitude = 110.574 km
    1 deg longitude = 111.320*cos(latitude) km latitude = 57 - average for Latvia
    https://stackoverflow.com/questions/1253499/simple-calculations-for-working-with-lat-lon-and-km-distance
'''
# Constants for converting a given degree of latitude/longitude to meters
LAT_M_PER_DEGREE = 110574
LON_M_PER_DEGREE = 111320 * math.cos(math.radians(57))

def coordinate_distance_to_m(lat1, lon1, lat2, lon2): # Error will accumulate over longer distances, using base to threat1 start as a test case = ~2.7km error
    # Pythagorean theorem - straight-line distance between 2 points
    dy = (lat2 - lat1) * LAT_M_PER_DEGREE
    dx = (lon2 - lon1) * LON_M_PER_DEGREE
    
    return math.sqrt(dx**2 + dy**2)
    
# Threat classification based on speed (m/s) and altitude (m)
def classify_threat(speed, altitude):
    if speed < 15 or altitude < 200:
        return ThreatLevel.NOT_THREAT
    if speed > 150:
        return ThreatLevel.THREAT
    if speed > 15:
        return ThreatLevel.CAUTION
    return ThreatLevel.POTENTIAL_THREAT

def is_in_range(base_lat, base_lon, ping_lat, ping_lon, radar_range_m):
    distance = coordinate_distance_to_m(base_lat, base_lon, ping_lat, ping_lon)
    return distance <= radar_range_m # Returns True if object is in radar range - will pull radar range from DB

def calculate_new_position(lat, lon, speed, heading):
    heading_rad = math.radians(heading)
    new_lat = lat + (speed * math.cos(heading_rad)) / LAT_M_PER_DEGREE
    new_lon = lon + (speed * math.sin(heading_rad)) / LON_M_PER_DEGREE
    return new_lat, new_lon
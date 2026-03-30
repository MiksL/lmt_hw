from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import HTMLResponse
import folium
from contextlib import asynccontextmanager
import asyncio

from folium.plugins import Realtime

import time
from radar import is_in_range, classify_threat, calculate_new_position, coordinate_distance_to_m, ThreatLevel
from database import close_db, get_all_targets, get_base, init_db, get_all_objects, update_object_classification, update_object_position, save_object, get_all_interceptors, save_intercept_decision, get_all_intercepts, get_intercept_by_track_id, mark_object_destroyed
from intercept import find_cheapest_interceptor

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    asyncio.create_task(simulation_loop())
    yield
    close_db()

'''
Simulation loop:
1. Moves all objects based on speed and heading
2. Simulates a radar ping, checks which objects are in radar range, classifies them and makes an interception decision
3. Waits for 1s (ping interval) and repeats
'''
tick_counter = 0

async def simulation_loop():
    global tick_counter
    while True:
        tick_counter += 1
        move_objects()
        await radar_ping()
        await asyncio.sleep(1)
    
app = FastAPI(lifespan=lifespan)

@app.get("/map", response_class=HTMLResponse)
def get_map():
    map = folium.Map(location=[56.879635, 24.603189], zoom_start=8)

    # Riga base coordinates, pulled from DB
    base = get_base()
    base_coordinates = [base["latitude"], base["longitude"]]

    folium.Marker(
        location=base_coordinates,
        popup="Riga Base",
        icon=folium.Icon(color="green", icon="satellite-dish", prefix="fa"),
    ).add_to(map)

    # 100km circle = range of the radar
    folium.Circle(
        location=base_coordinates,
        radius=100000,
        color="green",
        fill=False,
        weight=2,
    ).add_to(map)
    
    # available defense radiuses for air defense types without country-wide coverage
    folium.Circle(
        location=base_coordinates,
        radius=2000,
        color="white",
        fill=False,
        weight=2,
    ).add_to(map)
    
    folium.Circle(
        location=base_coordinates,
        radius=30000,
        color="orange",
        fill=False,
        weight=2,
    ).add_to(map)
    
    # All potential targets and their exclusion zones
    for target in get_all_targets():
        if target["name"] == "Riga Base": # Already marked
            continue
        folium.Marker(
            location=[target["latitude"], target["longitude"]],
            popup=target["name"],
            icon=folium.Icon(color="blue", icon="crosshairs", prefix="fa"),
        ).add_to(map)
        # Exclusion zone visualization
        if target["exclusion_zone_m"] > 0:
            folium.Circle(
                location=[target["latitude"], target["longitude"]],
                radius=target["exclusion_zone_m"],
                color="blue",
                fill=False,
                weight=2,
            ).add_to(map)
    
    # Updating object position every second on the map with Folium Realtime
    Realtime(
        "/api/objects",
        interval=1000,
        remove_missing=True,
        get_feature_id=folium.JsCode("(f) => f.properties.track_id"),
        # AI - code for marker color and popup info based on object
        point_to_layer=folium.JsCode("""
            (f, latlng) => {
                const colors = { 0: 'grey', 1: 'yellow', 2: 'orange', 3: 'red' };
                const color = colors[f.properties.classification] ?? 'grey';
                const marker = L.circleMarker(latlng, {
                    radius: 6,
                    color: color,
                    fillColor: color,
                    fillOpacity: 1
                });
                marker.bindPopup(
                    'ID: '             + f.properties.track_id   +
                    '<br>Speed: '      + f.properties.speed_ms   + ' m/s' +
                    '<br>Altitude: '   + f.properties.altitude_m + ' m'   +
                    '<br>Class: '      + f.properties.classification
                );
                return marker;
            }
        """),
        # AI - Updating threat classification color without page refresh
        update_feature=folium.JsCode("""
            (f, oldLayer) => {
                if (!oldLayer) return; // If no layers, skip the update
                const colors = { 0: 'grey', 1: 'yellow', 2: 'orange', 3: 'red' };
                const color = colors[f.properties.classification] ?? 'grey';
                oldLayer.setLatLng([f.geometry.coordinates[1], f.geometry.coordinates[0]]);
                oldLayer.setStyle({ color: color, fillColor: color });
                oldLayer.setPopupContent(
                    'ID: '           + f.properties.track_id   +
                    '<br>Speed: '    + f.properties.speed_ms   + ' m/s' +
                    '<br>Altitude: ' + f.properties.altitude_m + ' m'   +
                    '<br>Class: '    + f.properties.classification
                );
                return oldLayer;
            }
        """),
    ).add_to(map)
    
    # AI - Interceptor dot + intercept point marker
    Realtime(
        "/api/intercepts",
        interval=1000,
        remove_missing=True,
        get_feature_id=folium.JsCode("(f) => f.properties.feature_type + '_' + f.properties.track_id"),
        point_to_layer=folium.JsCode("""
            (f, latlng) => {
                if (f.properties.feature_type === 'intercept_point') {
                    const marker = L.circleMarker(latlng, {
                        radius: 8,
                        color: 'purple',
                        fillColor: 'solid',
                        fillOpacity: 0,
                        weight: 4,
                        dashArray: '4,4'
                    });
                    marker.bindPopup(
                        'Intercept point' +
                        '<br>Interceptor: ' + f.properties.interceptor_type +
                        '<br>Cost: '        + f.properties.intercept_cost   + ' EUR'
                    );
                    return marker;
                }
                const marker = L.circleMarker(latlng, {
                    radius: 5,
                    color: 'white',
                    fillColor: 'white',
                    fillOpacity: 1
                });
                marker.bindPopup(
                    'Interceptor: '   + f.properties.interceptor_type          +
                    '<br>Target ID: ' + f.properties.track_id                  +
                    '<br>Progress: '  + (f.properties.progress * 100).toFixed(0) + '%' +
                    '<br>Cost: '      + f.properties.intercept_cost            + ' EUR'
                );
                return marker;
            }
        """),
        update_feature=folium.JsCode("""
            (f, oldLayer) => {
                if (!oldLayer) return;
                oldLayer.setLatLng([f.geometry.coordinates[1], f.geometry.coordinates[0]]);
                return oldLayer;
            }
        """),
    ).add_to(map)

    # Returning HTML representation of the map
    html_map = map.get_root().render()
    
    return html_map

@app.get("/api/intercepts")
def get_intercepts(all: int = 0):
    intercepts = get_all_intercepts(include_destroyed=bool(all))
    if not intercepts:
        return {"type": "FeatureCollection", "features": []}
    base = get_base()
    if not base:
        return {"type": "FeatureCollection", "features": []}
    features = []
    for i in intercepts:
        ticks_elapsed = tick_counter - i['assigned_at']
        progress = min(ticks_elapsed / i['intercept_time_s'], 1.0)
        lat = base['latitude']  + (i['intercept_lat'] - base['latitude'])  * progress
        lon = base['longitude'] + (i['intercept_lon'] - base['longitude']) * progress

        # Moving interceptor dot
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "feature_type":     "interceptor",
                "track_id":         i['track_id'],
                "interceptor_type": i['interceptor_type'],
                "intercept_cost":   i['intercept_cost'],
                "progress":         round(progress, 2)
            }
        })

        # Static intercept point marker
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [i['intercept_lon'], i['intercept_lat']]},
            "properties": {
                "feature_type":     "intercept_point",
                "track_id":         i['track_id'],
                "interceptor_type": i['interceptor_type'],
                "intercept_cost":   i['intercept_cost']
            }
        })

    return {"type": "FeatureCollection", "features": features}

@app.get("/api/objects")
def get_objects():
    objects = get_all_objects()
    features = []
    for obj in objects:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [obj["longitude"], obj["latitude"]]  # GeoJSON format - https://en.wikipedia.org/wiki/GeoJSON
            },
            "properties": {
                "track_id": obj["track_id"],
                "speed_ms": obj["speed_ms"],
                "altitude_m": obj["altitude_m"],
                "classification": obj["classification"]
            }
        })
    return {"type": "FeatureCollection", "features": features}

@app.post("/api/radar")
async def create_object(request: Request):
    data = await request.json()

    # Pull fields from API request
    track_id    = data["track_id"]
    lat         = data["latitude"]
    lon         = data["longitude"]
    speed       = data["speed_ms"]
    altitude    = data["altitude_m"]
    heading     = data["heading_deg"]
    report_time = data["report_time"]
    
    save_object(track_id, lat, lon, speed, altitude, heading, report_time)

    return {
        "detected": True,
        "track_id": track_id,
    }
    
def move_objects():
    objects = get_all_objects()
    for obj in objects:
        if obj['to_be_intercepted']:
            intercept = get_intercept_by_track_id(obj['track_id'])
            if intercept:
                dist = coordinate_distance_to_m(
                    obj['latitude'], obj['longitude'],
                    intercept['intercept_lat'], intercept['intercept_lon']
                )
                if dist <= obj['speed_ms']:
                    # Last step — move fractional distance to land exactly on intercept point
                    fraction = dist / obj['speed_ms'] if obj['speed_ms'] > 0 else 1.0
                    fractional_speed = obj['speed_ms'] * fraction
                    new_lat, new_lon = calculate_new_position(obj['latitude'], obj['longitude'], fractional_speed, obj['heading_deg'])
                    update_object_position(obj['track_id'], new_lat, new_lon)
                else:
                    new_lat, new_lon = calculate_new_position(obj['latitude'], obj['longitude'], obj['speed_ms'], obj['heading_deg'])
                    update_object_position(obj['track_id'], new_lat, new_lon)
            continue
        new_lat, new_lon = calculate_new_position(obj['latitude'], obj['longitude'], obj['speed_ms'], obj['heading_deg'])
        update_object_position(obj['track_id'], new_lat, new_lon)
        #print(f"Moved object {obj['track_id']} to new position: ({new_lat}, {new_lon})")
        
async def radar_ping():
    base         = get_base()
    objects      = get_all_objects()
    interceptors = get_all_interceptors()
    targets      = get_all_targets()

    for obj in objects:
        in_range = is_in_range(base["latitude"], base["longitude"], obj['latitude'], obj['longitude'], base["range_m"])
        if not in_range:
            continue

        classification = classify_threat(obj['speed_ms'], obj['altitude_m'])
        update_object_classification(obj['track_id'], classification)

        if obj['to_be_intercepted']:
            intercept = get_intercept_by_track_id(obj['track_id'])
            if intercept:
                ticks_elapsed = tick_counter - intercept['assigned_at']
                progress = ticks_elapsed / intercept['intercept_time_s']
                dist     = coordinate_distance_to_m(
                    obj['latitude'], obj['longitude'],
                    intercept['intercept_lat'], intercept['intercept_lon']
                )
                # Interceptor position (same lerp as /api/intercepts)
                i_progress = min(progress, 1.0)
                i_lat = base['latitude']  + (intercept['intercept_lat'] - base['latitude'])  * i_progress
                i_lon = base['longitude'] + (intercept['intercept_lon'] - base['longitude']) * i_progress

                # AI debug
                print(f"[DEBUG] {obj['track_id']} | "
                      f"threat=({obj['latitude']:.6f}, {obj['longitude']:.6f}) | "
                      f"interceptor=({i_lat:.6f}, {i_lon:.6f}) | "
                      f"intercept_point=({intercept['intercept_lat']:.6f}, {intercept['intercept_lon']:.6f}) | "
                      f"dist={dist:.1f}m | progress={progress:.3f}")

                # AI check and debug
                # Threat was snapped to intercept point last tick (dist ≈ 0), destroy this tick so the map shows the collision for 1 frame
                if progress >= 1.0 and dist < 1:
                    mark_object_destroyed(obj['track_id'])
                    print(f"[DESTROYED] {obj['track_id']} — {intercept['interceptor_type']}, cost: {intercept['intercept_cost']:.2f} EUR")
                    # Output DB info from intercept_table
                    print(f"[INTERCEPT LOG] track_id={obj['track_id']}, interceptor={intercept['interceptor_type']}, intercept_time={intercept['intercept_time_s']}s, cost={intercept['intercept_cost']:.2f} EUR")
            continue

        if classification >= ThreatLevel.THREAT and not obj['to_be_intercepted']:
            decision = find_cheapest_interceptor(obj, interceptors, targets, base)
            if decision:
                save_intercept_decision(
                    obj['track_id'],
                    decision['interceptor_type'],
                    decision['intercept_lat'],
                    decision['intercept_lon'],
                    decision['intercept_time_s'],
                    decision['cost'],
                    tick_counter
                )
                print(f"[INTERCEPT] {obj['track_id']} → {decision['interceptor_type']} "
                      f"at ({decision['intercept_lat']:.4f}, {decision['intercept_lon']:.4f}) "
                      f"in {decision['intercept_time_s']:.1f}s — {decision['cost']:.2f} EUR")
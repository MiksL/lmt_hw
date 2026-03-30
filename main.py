from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import HTMLResponse
import folium
from contextlib import asynccontextmanager
import asyncio

from radar import is_in_range, classify_threat, calculate_new_position, ThreatLevel
from database import close_db, get_base, init_db, get_all_objects, update_object_position, save_object

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
async def simulation_loop():
    while True:
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

    
    # Imaginary threat starting point and a given trajectory (with the target being the base)
    threat1_coordinates = [57.81792086560779, 28.31858155558174]
    folium.PolyLine(
        locations=[threat1_coordinates, base_coordinates],
        color="red",
        weight=2,
    ).add_to(map)
    
    # Threat start marker
    folium.Marker(location=threat1_coordinates, popup="Origin").add_to(map)
    
    # Returning HTML representation of the map
    html_map = map.get_root().render()

    return html_map

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
    
    # TODO: save object to the DB
    save_object(track_id, lat, lon, speed, altitude, heading, report_time)
    

    return {
        "detected": True,
        "track_id": track_id,
        #"classification": classification # Classification happens in the radar ping part
    }
    
def move_objects():
    objects = get_all_objects()
    for obj in objects:
        # move it
        new_lat, new_lon = calculate_new_position(obj['latitude'], obj['longitude'], obj['speed_ms'], obj['heading_deg'])
        update_object_position(obj['track_id'], new_lat, new_lon)
        #print(f"Moved object {obj['track_id']} to new position: ({new_lat}, {new_lon})")
        
async def radar_ping():
    base = get_base()
    # Simulating a radar "ping"
    objects = get_all_objects()
    for obj in objects:
        in_range = is_in_range(base["latitude"], base["longitude"], obj['latitude'], obj['longitude'], base["range_m"])
        if not in_range:
            continue
        classification = classify_threat(obj['speed_ms'], obj['altitude_m'])
        # Classification test Print
        #print(f"Object {obj['track_id']} classified as {ThreatLevel(classification).name}")
        # TODO: update classification in DB
        if classification >= ThreatLevel.THREAT and not obj['to_be_intercepted']:
            pass #TODO - implement interception logic
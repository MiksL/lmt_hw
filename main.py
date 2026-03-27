from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import HTMLResponse
import folium
from contextlib import asynccontextmanager

from radar import is_in_range, classify_threat
from database import close_db, get_base, init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    close_db()
    
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
async def radar_ping(request: Request):
    data = await request.json()

    # Pull fields from radar ping
    track_id    = data["track_id"]
    lat         = data["latitude"]
    lon         = data["longitude"]
    speed       = data["speed_ms"]
    altitude    = data["altitude_m"]
    heading     = data["heading_deg"]
    report_time = data["report_time"]

    # Get base from DB and check if ping is in range
    base = get_base()  # returns the Riga base row
    in_range = is_in_range(lat, lon, base["latitude"], base["longitude"], base["range_m"])

    if not in_range:
        return {"detected": False, "track_id": track_id}

    # Classify and store
    classification = classify_threat(speed, altitude)

    return {
        "detected": True,
        "track_id": track_id,
        "classification": classification
    }
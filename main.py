from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import folium

app = FastAPI()

@app.get("/map", response_class=HTMLResponse)
def get_map():
    map = folium.Map(location=[56.879635, 24.603189], zoom_start=8)

    # Riga base coordinates
    base_coordinates = [56.97475845607155, 24.1670070219384]

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
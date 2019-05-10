import json
import ipyleaflet as pl
import ipywidgets as pw


# ----------------------------------------------------------------------------
# the above domain

domain_json = 'data/ABoVE_Study_Domain/ABoVE_Study_Domain.json'  
with open(domain_json, 'r') as file:
    above_domain = json.load(file)
    above_domain["features"][0]["properties"]["style"] = {
        "weight": 0.75,
        "color": "#FFFFFF",
        "fillColor": "#FFFFFF",
        "fillOpacity": 0}
    domain_layer = pl.GeoJSON(data=above_domain)


# ----------------------------------------------------------------------------
# map widget interface

# load a basemap layer from ESRI service
esri = pl.basemap_to_tiles(pl.basemaps.Esri.WorldImagery)
gibs = pl.basemap_to_tiles(pl.basemaps.NASAGIBS.ModisTerraTrueColorCR, "2019-01-01")

gridA = pl.LayerGroup()
gridB = pl.LayerGroup()

# initialize map widget
m = pl.Map(
    layers=(esri, domain_layer, gridB, ), #gridA
    center=(65, -150), 
    zoom=5, 
    scroll_wheel_zoom=True)
m.add_control(pl.LayersControl())


# ---------------------------------------------------------------------------- 
# the above grid (not using C because too fine)

grid_table = {"A": {}, "B": {}, "C": {}}
grid_json = ("data/ABoVE_240m_30m_5m_grid_tiles/"
            "ABoVE_240m_30m_5m_grid_tiles.json")

with open(grid_json, 'r') as file:
    above_grid = json.load(file)
    
    for feat in above_grid["features"]:
        prop = feat["properties"]          # collect grid cell properties
        level = prop["grid_level"]         # get level A, B, or C
        feat["properties"]["style"] = {
            "weight": 0.75,
            "color": "aliceblue",
            "fillOpacity": 0}
        
        id = prop["grid_id"]               # get grid cell id
        cell = pl.GeoJSON(
            data=feat,
            hover_style = {
                "weight": 1,
                "color": "aliceblue",
                "fillColor": "#FFFFFF",
                "fillOpacity": 0.4})       # make geojson map layer
        grid_table[level][id] = cell

        if level=="A": 
            gridA.add_layer(cell)
        elif level=="B": 
            gridB.add_layer(cell)
        else:
            pass


# ----------------------------------------------------------------------------
# JSON input interface

# the default json string for selecting collections/granules 
with open('data/geom.json', 'r') as file:
    default_json = file.read().replace('\n', '')

geojson_label = pw.HTML("<h4><b>Paste your GeoJSON: </b></h4>")
geojson_text = pw.Textarea(
    value=default_json,
    placeholder='Paste GeoJSON string here.',
    disabled=False,
    layout=pw.Layout(width="auto", height="200px"))



# -------------------------------------------------------------------------------
# display!
display(pw.VBox([geojson_label, geojson_text, m]))
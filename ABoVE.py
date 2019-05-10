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
# the above grid (not using C because too fine)

grid_json = ("data/ABoVE_240m_30m_5m_grid_tiles/"
            "ABoVE_240m_30m_5m_grid_tiles.json")

gridA, gridB = [], []
with open(grid_json, 'r') as file:
    above_grid = json.load(file)
    
    for feat in above_grid["features"]:
        prop = feat["properties"]
        level = prop["grid_level"]
        prop = prop.update({
            "style": {
                "weight": 0.75,
                "color": "aliceblue",
                "fillOpacity": 0}})
        
        if level in ["A", "B"]:
            
            cell = pl.GeoJSON(
                data=feat,
                hover_style = {
                    "weight": 1,
                    "color": "aliceblue",
                    "fillColor": "#FFFFFF",
                    "fillOpacity": 0.4})       # make geojson map layer

            if level=="A": 
                gridA.append(cell)
            if level=="B": 
                gridB.append(cell)

# ----------------------------------------------------------------------------
# map widget interface

# load a basemap layer from ESRI service
esri = pl.basemap_to_tiles(pl.basemaps.Esri.WorldImagery)
#gibs = pl.basemap_to_tiles(pl.basemaps.NASAGIBS.ModisTerraTrueColorCR, "2019-01-01")

gridA_layer = pl.LayerGroup(layers=tuple(gridA))
gridB_layer = pl.LayerGroup(layers=tuple(gridB))

# initialize map widget
m = pl.Map(
    layers=(esri, gridB_layer, ),
    center=(60, -135), 
    zoom=2, 
    scroll_wheel_zoom=True)

#m.add_control(pl.LayersControl())

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
# map draw controls

draw_control = pw.DrawControl()
draw_control.polyline =  {}
draw_control.polygon = {}
draw_control.circle = {}
draw_control.rectangle = {
    "shapeOptions": {
        "fillColor": "#fca45d",
        "color": "#fca45d",
        "fillOpacity": 1.0}}
m.add_control(draw_control)

# -------------------------------------------------------------------------------
# display!

display(pw.VBox([m, geojson_label, geojson_text]))
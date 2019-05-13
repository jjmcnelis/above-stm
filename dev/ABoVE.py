import json
import requests
import pandas as pd

from shapely.geometry import shape, mapping
from shapely.ops import cascaded_union

import qgrid
from ipyleaflet import Map,LayerGroup,DrawControl,GeoJSON,basemaps,basemap_to_tiles,Polygon
from ipywidgets import HTML,Layout,HBox,VBox,Textarea,Output

from QueryCMR import *

# ---------------------------------------------------------------------------- 
# statics

# the above grid; make layers later
gridf = "data/ABoVE_240m_30m_5m_grid_tiles/ABoVE_240m_30m_5m_grid_tiles.json"
with open(gridf, 'r') as file:
    above_grid = json.load(file)

# the above domain; make layer now
domainf = 'data/ABoVE_Study_Domain/ABoVE_Study_Domain.json'  
with open(domainf, 'r') as file:
    above_domain = json.load(file)

# get some info about ABoVE collection in CMR for ORNL
above_search = collections.keyword("*Boreal Vulnerability Experiment*").get_all()
above_results = [r for r in above_search if any([
    "ABoVE" in r["dataset_id"],
    "ABoVE" in r["summary"]])
]
above_results_df = pd.DataFrame(above_results)

# load a basemap from ESRI #basemaps.NASAGIBS.ModisTerraTrueColorCR
esri = basemap_to_tiles(basemaps.Esri.WorldImagery)

# map draw poly styling
draw_style = {
    "shapeOptions": {
        "fillColor": "lightgreen",
        "color": "lightgreen",
        "fillOpacity": 0.5}}

# ----------------------------------------------------------------------------
# JSON input interface and some other ui elements

geojson_label = HTML("<h4><b> or paste your GeoJSON: </b></h4>")

geojson_text = Textarea(
    placeholder='Paste GeoJSON string here.',
    disabled=False,
    layout=Layout(width="50%", height="200px"))
    
above_domain["features"][0]["properties"]["style"] = {
    "weight": 0.75,
    "color": "#FFFFFF",
    "fillColor": "#FFFFFF",
    "fillOpacity": 0.}

domain_layer = GeoJSON(data=above_domain)

header = HTML(
    "<h4><b>Draw a polygon on the map or paste your GeoJSON: </b></h4>")

instruct =  HTML(
    "<p><b>Instructions:</p><p><b>1.<br>2.<br>3.<br>...</p>",
    layout=Layout(width="50%"))

displaycols = [
    "dataset_id",
    "title",
    "time_start",
    "time_end",
    "boxes",
    "links",
    "id",
    "summary"
]

# ---------------------------------------------------------------------------- 
# class to manage toggled grid cells


class Cell(object):
    """ """

    offstyle = {"fill_opacity": 0, "color": "white", "weight": 0.75}
    onstyle = {"fill_opacity": 0.4, "color": "lightgreen", "weight": 1}

    def __init__(self, feat):
        """Inits with id,lat,lon; makes request string, map point."""

        self.feat = feat
        self.shape = shape(feat["geometry"])

        self.prop = feat["properties"]
        self.feat["properties"]["style"] = {
            "fill_opacity": 0.1,
            "opacity": 0.1, 
            "color": "white", 
            "weight": 0.75}
        self.id = self.prop["grid_id"]
        self.level = self.prop["grid_level"]
        
        self.layer = GeoJSON(
            data=self.feat,
            hover_style = {
                "weight": 1, 
                "color": "white",
                "fillColor": "white",
                "fillOpacity": 0.3})
        self.layer.on_click(self.toggle)
        self.on = False

    def toggle(self, **kwargs):
        """Routine for when a cell is toggled on."""
        self.on = False if self.on else True
        

class App():
    """ """
    
    settings = {"enabled_grid": "B"}


    def __init__(self, session=None):

        self.session = session
        self.use_grid = self.settings["enabled_grid"]

        # generate map grid polygon layers
        self.grid_layers = LayerGroup()
        self.grid_dict = {}
        
        for feat in above_grid["features"]:
            level = feat["properties"]["grid_level"]
            if level==self.use_grid:
                Cell_object = Cell(feat) 
                #Cell_object.layer.on_click()

                grid_id = Cell_object.id
                self.grid_dict[grid_id] = Cell_object
                self.grid_layers.add_layer(self.grid_dict[grid_id].layer)
        
        # make an attribute that will hold selected layer
        self.selected_layer = LayerGroup()

        self.map = Map(
            layers=(esri, self.grid_layers, self.selected_layer, ),
            center=(65, -100), 
            zoom=3, 
            width="auto", 
            height="auto",
            scroll_wheel_zoom=True)

        # map draw controls
        self.draw_control = DrawControl()
        self.draw_control.polyline =  {}
        self.draw_control.circle = {}
        self.draw_control.circlemarker = {}
        self.draw_control.remove = False
        self.draw_control.edit = False
        self.draw_control.polygon = {**draw_style}
        self.draw_control.rectangle = {**draw_style}
        self.draw_control.on_draw(self.update_selected_cells)
        self.map.add_control(self.draw_control)
        
        # output display
        self.output = Output(layout=Layout(width="auto", height="auto"))
        
        # make the widget layout
        self.ui = VBox([
            #header, 
            #HBox([instruct, geojson_text]),
            self.map,
            self.output
        ], layout=Layout(width="auto"))

        # display ui
        display(self.ui)


    def update_selected_cells(self, *args, **kwargs):
        """ """
        # clear all draw and selection layers
        self.draw_control.clear()
        
        # --------------------------------------------------------------------
        # update active cells and make a big merged polgyon for selection

        # make shapely geom from geojson 
        drawn_json = kwargs["geo_json"]
        shapely_geom = shape(drawn_json["geometry"])
        cells = self.grid_dict
        
        # iterate over cells and collect intersecting cells
        on = [] 
        for id, cell in cells.items():
            if shapely_geom.intersects(cell.shape):
                on.append(cell.shape)
        
        # this is blatant abuse of try/except; fix it 
        try:
            # get the union of all of the cells that are toggled on
            union = cascaded_union(on)
            centroid = union.centroid

            # make layer that represents selected cells and add to selected_layer
            self.selected_layer.clear_layers()
            x,y = union.exterior.coords.xy
            self.selected_layer.add_layer(Polygon(locations=list(zip(y,x))))
            self.map.center = (centroid.y, centroid.x)

            # --------------------------------------------------------------
            # find all CMR collections that intersect with merged cells geom

            selected = []
            for index, collection in above_results_df.iterrows():
                box = collection.boxes
                shapely_box = CMR_box_to_Shapely_box(box[0])

                # intersect: use shapely_geom if strictly using drawn poly
                intersect_bool = shapely_box.intersects(union) 
                if intersect_bool:
                    selected.append(index)

            self.coll = above_results_df.iloc[selected]

            self.tab = qgrid.show_grid(
                self.coll[[
                     "dataset_id",
                     "time_start",
                     "time_end",
                     "boxes"]], 
                grid_options={'forceFitColumns': False, 
                              'minColumnWidth': "0",
                              'maxColumnWidth': "400"},
                show_toolbar=False)

            self.output.clear_output()
            with self.output:
                display(self.tab)
                #display(self.coll[[
                #    "dataset_id", "time_start", "time_end", "boxes"]])
                
        except:
            pass


##############################################################################
# launch it braj!
##############################################################################

app = App()
#!/usr/bin/env python
"""
##############################################################################

ABoVE data from CMR

##############################################################################
"""

import json
import requests
import pandas as pd

from shapely.geometry import shape, mapping, box
from shapely.ops import cascaded_union

try:
    import _pickle as pickle
except ModuleNotFoundError:
    import pickle

# path to above-stm
#repo = "/home/jack/Desktop/git/above-stm/"
repo = "./"

"""
------------------------------------------------------------------------------
Data required by ABoVE Collections/Granules notebook
------------------------------------------------------------------------------
"""

# Open a pickled data frame with all ABoVE datasets info required by notebook
with open(repo+'data/above_dataset_table.pkl', 'rb') as input:
    dataset_table = pickle.load(input)

# Make a smaller version of the table that is referenced after interactions
dataset_locator_table = dataset_table[[
    "title",
    "conceptid",
    "short_name",
    "bounds_shapely",
    "start_time",
    "end_time",
    "minlon",
    "maxlon",
    "minlat",
    "maxlat",
    "url_sdat",
    "url_thredds",
    "science_keywords"
]]

# Open the same type of pickled data frame for with all ABoVE granules
with open(repo+'data/above_granules_table.pkl', 'rb') as input:
    above_granules_table = pickle.load(input)

# And make a smaller version of it too
granule_locator_table = above_granules_table[[
    "collection_short_name",
    "conceptid",
    "granuleid",   
    "bounds_shapely",
    "start_time",
    "end_time",
    "minlon",
    "maxlon",
    "minlat",
    "maxlat",
    "granule_params",
    "url_datapool"
]]

# Open a VERY IMPORTANT TABLE that links datasets and granules to ABoVE grid
#   This table takes quite some time to produce so don't delete by mistake
with open(repo+'data/above_grid_table_ab.pkl', 'rb') as input:
    above_grid_table = pickle.load(input)


"""
##############################################################################

App data  

##############################################################################
"""

import qgrid
from ipywidgets import HTML, Layout, HBox, VBox, Textarea, Output, Accordion
from ipyleaflet import Map,\
    LayerGroup,\
    DrawControl,\
    GeoJSON,\
    basemaps,\
    basemap_to_tiles,\
    Polygon


"""
------------------------------------------------------------------------------
UI elements
------------------------------------------------------------------------------
"""

#load a basemap from ESRI #basemaps.NASAGIBS.ModisTerraTrueColorCR
#esri = basemap_to_tiles(basemaps.Esri.DeLorme)
esri = basemap_to_tiles(basemaps.Esri.WorldImagery)

# map draw poly styling
draw_style = {"shapeOptions": {
    "fillColor": "white",
    "color": "white",
    "opacity": 0.5,
    "fillOpacity": 0.5}}

geojson_label = HTML("<h4><b> or paste your GeoJSON: </b>0</h4>")

geojson_text = Textarea(
    placeholder='Paste GeoJSON string here.',
    disabled=False,
    layout=Layout(width="50%", height="200px"))


# the above grid; make layers later
gridf = "data/ABoVE_240m_30m_5m_grid_tiles/ABoVE_240m_30m_5m_grid_tiles.json"
with open(repo+gridf, 'r') as file:
    above_grid = json.load(file)


def get_results_header(text):
    """ """
    return(HTML("<p style='line-height: 1.2;'>"+text+"</b></p>"))


dataset_results_header = get_results_header((
    "The following datasets have bounding boxes that intersect "
    "the selected ABoVE Grid cell(s). Note: Several datasets' "
    "metadata extents span the grid's full coverage area and "
    "will be returned no matter which cells are selected. <br>"
    "<br><b>Click a dataset's row to browse its granules:"))

granules_results_header = get_results_header((
    "The granules in the table below have bounding boxes that "
    "intersect the selected ABoVE Grid cell(s). An empty table "
    "indicates that the publication process is likely in progress. "
    "<br><br>Browsing granules by location is "
    "<br><br><b>Select a granule (or a list of granules with "
    "Ctrl+Click or Ctrl+Shift) to display spatial coverages on "
    "the map:</b>"))


"""
------------------------------------------------------------------------------
Cell class is part of the link between the map's ABoVE grid polygons and the
dataset and granule locator tables. This class stores some information about
each ABoVE grid cell that is useful for current and future search 
functionality.
------------------------------------------------------------------------------
"""


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


"""
------------------------------------------------------------------------------
Functions for selecting from the dataset and granule *_locator_table(s)
------------------------------------------------------------------------------
"""

dfsel = lambda df, sel, val: df.loc[df[sel]==val]
dflistsel = lambda df, sel, lst: df.loc[df[sel].isin(lst)]

def get_by_tiles(tile_list, search):
    """ """
    
    ix_with_duplicates = []        
    shapelies = []
    
    if search=="datasets":
        locator_table = dataset_locator_table
        ixcolumn = "dataset_locator_ix"

    if search=="granules":
        locator_table = granule_locator_table
        ixcolumn = "granule_locator_ix" #indices

    for tile in tile_list:
        tilerow = dfsel(above_grid_table, "grid_id", tile)
        rowix = tilerow[ixcolumn].tolist()
        try:
            ix_with_duplicates.extend(rowix[0])
            shapelies.append(tilerow["bounds_shapely"].item())
        except:
            pass

    ix = list(set(ix_with_duplicates))
    table = locator_table.iloc[ix]

    return((table, shapelies))


"""
------------------------------------------------------------------------------
Functions for generating qgrid tables and reacting to table clicks
------------------------------------------------------------------------------
"""

dataset_column_definitions = {
    "title": {"width": 600},
    "start_time": {"width": 150}, 
    "end_time": {"width": 150}}

granule_column_definitions = {
    "granuleid": {"width": 700}}


def get_qgrid(df, index, column_definitions, grid_options):
    """ 
    Generates a qgrid table with some customization for either
    datasets or granules.
    """
    
    df.set_index(index, inplace=True)
    table = qgrid.show_grid(
        df,
        column_definitions=column_definitions,
        grid_options=grid_options,
        show_toolbar=False)

    return(table)


# ---------------------------------------------------------------------------

# granule selections box styling
granules_box_style = {
    "fill_opacity": 0.1,
    "fill_color": "orange",
    "opacity": 1, 
    "color": "white", 
    "weight": 1}


def get_map_poly_from_shapely(shapely_poly, style):
    """Takes an input shapely geometry; returns ipyleaflet poly layer."""
    x,y = shapely_poly.exterior.coords.xy
    return(Polygon(locations=list(zip(y,x)), **style))


# def get_sum_txt():
#     """ """



def handle_granule_table_select(event, qgrid_widget):
    """
    Handles interactions with the granules table.
    """
    selected_grans.clear_layers()

    # get the short name of the dataset from the dataset_locator_table
    rowdf = qgrid_widget.get_selected_df()
    ixlist = rowdf.index.tolist()
    granules = dflistsel(granule_locator_table, "granuleid", ixlist)

    shapes = []
    for index, granule in granules.iterrows():
        shapely_box = granule["bounds_shapely"]
        gran = get_map_poly_from_shapely(shapely_box, granules_box_style)
        selected_grans.add_layer(gran)
        shapes.append(shapely_box)
    
    union = cascaded_union(shapes)
    centroid = union.centroid
    mapw.center = (centroid.y, centroid.x)
    
    # get the bounding box that contains all selected granules
    allbnds = {"minx": granules["minlon"].min(),
               "miny": granules["minlat"].min(),
               "maxx": granules["maxlon"].max(),
               "maxy": granules["maxlat"].max()}

# ---------------------------------------------------------------------------

# dataset selections grid styling
datasets_grid_style = {
    "fill_opacity": 0.1,
    "opacity": 1, 
    "color": "white", 
    "fill_color": "purple",
    "weight": 1}


def handle_dataset_table_select(event, qgrid_widget):
    """
    Selects granules for the selected dataset; then, calls
    function to generate qgrid table for granules when
    a dataset is selected in the datasets table.
    """

    output_containers.selected_index = 1

    # get the short name of the dataset from the dataset_locator_table
    rowdf = qgrid_widget.get_selected_df()
    dataset = dfsel(dataset_locator_table, "title", rowdf.index[0])
    short_name = dataset["short_name"].item()

    # get the dataset's granules by indexing with the short_name
    granules = dfsel(
        granule_locator_table, 
        "collection_short_name", 
        short_name)
    granules1 = granules[[
        "granuleid", 
        "start_time",
        "end_time",
        "url_datapool"]]
    
    granules_qgrid = get_qgrid(
        granules1, 
        "granuleid", 
        granule_column_definitions,
        {'forceFitColumns': False, "maxVisibleRows": 15})
    granules_qgrid.on("selection_changed", handle_granule_table_select)

    output_granules.clear_output()
    with output_granules:
        display(granules_results_header)
        display(granules_qgrid)    


def update_rendered_dataset_table(dataset_selection_table):
    """ """

    # make new qgrids
    datasets_qgrid = get_qgrid(
        dataset_selection_table, 
        "title", 
        dataset_column_definitions,
        {"forceFitColumns": False, "maxVisibleRows": 8})
    datasets_qgrid.on("selection_changed", handle_dataset_table_select)

    output_containers.selected_index = 0    
    output_datasets.clear_output()
    with output_datasets:
        display(dataset_results_header)
        display(datasets_qgrid)


def update_rendered_granule_table(granule_selection_table):
    """ """

    # make new qgrids
    granules_qgrid = get_qgrid(
        granule_selection_table, 
        "granuleid", 
        granule_column_definitions,
        {"forceFitColumns": False, "maxVisibleRows": 15})
    granules_qgrid.on("selection_changed", handle_granule_table_select)

    output_granules.clear_output()
    with output_granules:
        display(granules_results_header)
        display(granules_qgrid)


"""
------------------------------------------------------------------------------
Functions for handing the "cell-clicked" and "poly-drawn" map interactions.
------------------------------------------------------------------------------
"""


def get_selection_polygon(locations, style):
    """ """
    return(Polygon(locations=list(zip(y,x)), **style))


def update_cell_clicked(*args, **kwargs):
    """ """
    draw_control.clear()

    if "properties" in kwargs.keys():
        on = kwargs["properties"]["grid_id"]

        if output_containers.selected_index==0:

            # get datasets with bboxes that intersect cell
            selections, shapelies = get_by_tiles([on], "datasets")
            selections1 = selections[["title", "start_time", "end_time"]]
            style1 = datasets_grid_style
            function1 = update_rendered_dataset_table

        if output_containers.selected_index==1:

            # get granules with bboxes that intersect cell
            selections, shapelies = get_by_tiles([on], "granules")
            selections1 = selections[[
                "granuleid", 
                "start_time",
                "end_time",
                "url_datapool"]]
            style1 = granules_box_style
            function1 = update_rendered_granule_table

        # make layer that represents selected cell, add to selected_layer
        selected_layer.clear_layers()
        poly = get_map_poly_from_shapely(shapelies[0], style1)

        selected_layer.add_layer(poly)
        # x,y = shapelies[0].exterior.coords.xy
        # selected_layer.add_layer(Polygon(
        #     locations=list(zip(y,x)), 
        #     **datasets_grid_style))
        centroid = shapelies[0].centroid
        mapw.center = (centroid.y, centroid.x)
        mapw.zoom = 6

        # render new results tables
        function1(selections1)


def update_poly_drawn(*args, **kwargs):
    """ """
  
    draw_control.clear()                       # clear draw, selection layers

    if "geo_json" in kwargs.keys():
       
        drawn_json = kwargs["geo_json"]        # make shapely from geojson 
        shapely_geom = shape(drawn_json["geometry"])
        cells = grid_dict

        # iterate over cells and collect intersecting cells
        on, shapes = [], []
        for id, cell in cells.items():
            if shapely_geom.intersects(cell.shape):
                on.append(id)
                shapes.append(cell.shape)
    
        # get the union of all of the cells that are toggled on
        union = cascaded_union(shapes)
        centroid = union.centroid

        # make layer that represents selected cells and add to selected_layer
        selected_layer.clear_layers()
        poly = get_map_poly_from_shapely(union, datasets_grid_style)
        selected_layer.add_layer(poly)
        # x,y = union.exterior.coords.xy
        # selected_layer.add_layer(Polygon(
        #     locations=list(zip(y,x)), 
        #     **datasets_grid_style))
        mapw.center = (centroid.y, centroid.x)
        mapw.zoom = 4

        # --------------------------------------------------------------------
        if output_containers.selected_index==0:

            # get datasets with bboxes that intersect cell
            selections, shapelies = get_by_tiles(on, "datasets")
            selections1 = selections[["title", "start_time", "end_time"]]
            style1 = datasets_grid_style
            function1 = update_rendered_dataset_table

        if output_containers.selected_index==1:

            # get granules with bboxes that intersect cell
            selections, shapelies = get_by_tiles(on, "granules")
            selections1 = selections[[
                "granuleid", 
                "start_time",
                "end_time",
                "url_datapool"]]
            style1 = granules_box_style
            function1 = update_rendered_granule_table

        # render new results tables
        function1(selections1)

        # --------------------------------------------------------------------

        # get datasets and display table(s)
        #datasets, shapelies = get_by_tiles(on, "datasets")
        #datasets1 = datasets[["title", "start_time", "end_time"]]

        # render new results tables
        #update_rendered_dataset_table(datasets1)

    else:
        
        pass


"""
##############################################################################

App initialize

##############################################################################
"""

# generate map grid polygon layers
grid_layers = LayerGroup()
grid_dict = {}

for feat in above_grid["features"]:
    level = feat["properties"]["grid_level"]
    if level=="B":
        Cell_object = Cell(feat) 
        Cell_object.layer.on_click(update_cell_clicked)
        grid_id = Cell_object.id
        grid_dict[grid_id] = Cell_object
        grid_layers.add_layer(grid_dict[grid_id].layer)

# make an attribute that will hold selected layer
selected_layer = LayerGroup()
selected_grans = LayerGroup()

mapw = Map(
    layers=(esri, grid_layers, selected_layer, selected_grans, ),
    center=(65, -100), 
    zoom=3, 
    width="auto", 
    height="auto",
    scroll_wheel_zoom=True)

# map draw controls
draw_control = DrawControl()
draw_control.polyline =  {}
draw_control.circle = {}
draw_control.circlemarker = {}
draw_control.remove = False
draw_control.edit = False
draw_control.polygon = {**draw_style}
draw_control.rectangle = {**draw_style}
draw_control.on_draw(update_poly_drawn)
mapw.add_control(draw_control)


# output displays
output_datasets = Output(layout=Layout(width="auto", height="auto"))
output_granules = Output(layout=Layout(width="auto", height="auto"))
output_containers = Accordion(children=[output_datasets, output_granules])
output_containers.set_title(0, 'CMR Datasets')
output_containers.set_title(1, 'CMR Granules')
output_containers.selected_index = 0
with output_datasets:
    display(HTML(
        "<p><b>Select one or more grid cells by clicking the cell on the map"
        ", or by drawing a polygon with one of the tools on the left.</b></p>"
    ))
with output_granules:
    display(HTML(
        "<p><b>Select one or more grid cells by clicking the cell on the map"
        ", or by drawing a polygon with one of the tools on the left.</b></p>"
    ))

def update_container(*args, **kwargs):
    """ 
    This makes sure granule layers are removed when dataset tab is reopened.
    """
    if output_containers.selected_index==0:
        selected_grans.clear_layers()
    else:
        pass
output_containers.observe(update_container)

# make the widget layout
ui = VBox([
    #map_header, 
    mapw,
    output_containers,
], layout=Layout(width="auto"))

display(ui)


"""
datasets for special above grid tab:

- ABoVE: Landsat-derived Burn Scar dNBR across Alaska

"""
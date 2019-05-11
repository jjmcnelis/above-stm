import pandas as pd
from shapely.geometry import box
from CMR import CollectionQuery, GranuleQuery

collections = CollectionQuery()
granules = GranuleQuery()

# def query_ornl_projects(p="ABoVE"):
#     """ """

#     # get ORNL DAAC collections from CMR
#     ornl_daac = collections.archive_center("ORNL_DAAC")
    
#     # select only records that have the project keyword argument in the title
#     ornl_p = [d for d in ornl_daac.keyword(p).get_all() if p in d["title"]]
    
#     # make pandas data frame
#     ornl_p_df = pd.DataFrame(ornl_p)
    
#     # all datasets returned by this function are from ORNL, so drop columns
#     ornl_p_df = ornl_p_df.drop([
#         'archive_center', 
#         'data_center', 
#         'score'], axis=1)
    
#     return(ornl_p_df)


def CMR_box_to_Shapely_box(cmr_box, id=0):
    """ """

    extent = cmr_box.split(" ")

    shapely_box = box(
        float(extent[1]), 
        float(extent[0]), 
        float(extent[3]), 
        float(extent[2]))

    return(shapely_box)
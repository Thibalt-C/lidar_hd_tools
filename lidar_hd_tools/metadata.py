from owslib.wfs import WebFeatureService
import geopandas as gpd
import io
import numpy as np

wfs_url = "https://data.geopf.fr/wfs/ows"
wfs = WebFeatureService(url=wfs_url, version="2.0.0")

def get_metadata(gdf):

    lidar_layer = "IGNF_NUAGES-DE-POINTS-LIDAR-HD:dalle"
    DSM_layer = "IGNF_MNS-LIDAR-HD:dalle"
    DEM_layer = "IGNF_MNT-LIDAR-HD:dalle"

    bbox = gdf.to_crs("epsg:4326").union_all().bounds

    merged_metadata = []

    for layer_name in [lidar_layer, DSM_layer, DEM_layer]:

        response = wfs.getfeature(typename=layer_name, outputFormat="application/json",
                                  bbox=bbox, srsname="EPSG:4326")

        with io.BytesIO(response.read()) as f:

            metadata = gpd.read_file(f)
            metadata = metadata.loc[metadata.geometry.intersects(gdf.to_crs("epsg:4326").geometry.union_all())].reset_index(drop=True)

            merged_metadata.append(metadata)

    projection = np.unique(merged_metadata[0]["projection"])[0] # assuming only one local projection used
    dem_tiles_urls = np.unique(merged_metadata[2]['url']).tolist()
    dem_tiles_filenames = np.unique(merged_metadata[2]['name_download']).tolist()
    dsm_tiles_urls = np.unique(merged_metadata[1]['url']).tolist()
    dsm_tiles_filenames = np.unique(merged_metadata[1]['name_download']).tolist()
    lidar_tiles_urls = np.unique(merged_metadata[0]['url']).tolist()
    lidar_tiles_filenames = np.unique(merged_metadata[0]['name_download']).tolist()

    return projection, (dem_tiles_urls, dsm_tiles_urls, lidar_tiles_urls), (dem_tiles_filenames, dsm_tiles_filenames, lidar_tiles_filenames)

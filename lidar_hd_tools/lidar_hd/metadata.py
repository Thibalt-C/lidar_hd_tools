from owslib.wfs import WebFeatureService
import geopandas as gpd
import io
import numpy as np
from typing import Optional, Tuple, List


def get_metadata(
        gdf : gpd.GeoDataFrame,
        url : Optional[str] = "https://data.geopf.fr/wfs/ows",
        layer : Optional[str] = "IGNF_LIDAR-HD_METADONNEE:metadata"
) -> Tuple[str, Tuple[List[str], List[str], List[str]], Tuple[List[str], List[str], List[str]]]:
    """
    Gives the URLs and filenames of the tiles corresponding to the given location.

    Parameters:
    ----------
    gdf : `geopandas.GeoDataFrame`
        Geofile of the location of interest
    url : string, optional
        url of the Web File Service containing the metadata
    layer : string, optional
        name of the layer in the Web File Service containing the metadata

    Returns:
    ----------
    projection : str
        CRS projection of the tiles
    urls : tuple of lists of str
        lists of URLs of the tiles
    filenames : tuple of lists of str
        lists of filenames of the tiles
    """

    bbox = gdf.to_crs("epsg:4326").union_all().bounds

    wfs = WebFeatureService(url=url, version="2.0.0")

    response = wfs.getfeature(typename=layer, outputFormat="application/json",
                              bbox=bbox, srsname="EPSG:4326")

    with io.BytesIO(response.read()) as f:

        metadata = gpd.read_file(f)
        metadata = metadata.loc[metadata.geometry.intersects(gdf.to_crs("epsg:4326").geometry.union_all())].reset_index(drop=True)

        if metadata.empty:
            raise ValueError(f"No tile found. Please check the selected location and used CRS.")

    syst_planim = np.unique(metadata["systeme_planimetrique"])[0]

    if syst_planim == "LAMB93":
        projection = "EPSG:2154"
    elif syst_planim == "RGAF09UTM20":
        projection = "EPSG:5490"
    elif syst_planim == "RGR92UTM40S":
        projection = "EPSG:2975"
    elif syst_planim == "RGM23UTM38S":
        projection = "EPSG:10674"
    else:
        raise ValueError(f"Unknown projection: {syst_planim}")

    dem_tiles_urls = np.unique(metadata['url_mnt']).tolist()
    dem_tiles_filenames = [url.split("FILENAME=")[-1] for url in dem_tiles_urls]

    dsm_tiles_urls = np.unique(metadata['url_mns']).tolist()
    dsm_tiles_filenames = [url.split("FILENAME=")[-1] for url in dsm_tiles_urls]

    lidar_tiles_urls = np.unique(metadata['url_npl']).tolist()
    lidar_tiles_filenames = [url.split("/")[-1] for url in lidar_tiles_urls]

    urls = (dem_tiles_urls, dsm_tiles_urls, lidar_tiles_urls)
    filenames = (dem_tiles_filenames, dsm_tiles_filenames, lidar_tiles_filenames)

    return projection, urls, filenames

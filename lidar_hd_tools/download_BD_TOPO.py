from owslib.wfs import WebFeatureService
import geopandas as gpd
import os
from shapely.geometry import Point

wfs_url = "https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities"

# Connexion
wfs = WebFeatureService(url=wfs_url, version="2.0.0")

verbose=True

def get_bdtopo(boundaries,feature, wfs=wfs, path='lidar_hd_tools/BD-TOPO_cache/', verbose=True):

    filepaths = []
    for layer_name in wfs.contents:
        if (f'BDTOPO_V3:{feature}' in layer_name):
            output_file = f"{layer_name.replace(':', '_')}.geojson"
            filepaths.append(path+output_file)
            if verbose:
                print(f"Downloading layer: {layer_name}")
            response = wfs.getfeature(typename=layer_name,
                                      bbox=boundaries,
                                      outputFormat="application/json")
            with open(path+output_file, "wb") as f:
                f.write(response.read())
            if verbose:
                print(f"Saved as: {output_file} in {path}")

    gdfs = {}
    for filepath in filepaths:
        gdfs[filepath.split("BDTOPO_V3_")[-1].split(".")[0]] = gpd.read_file(filepath).to_crs("epsg:2154")

    return gdfs
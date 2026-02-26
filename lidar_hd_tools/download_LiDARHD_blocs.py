from owslib.wfs import WebFeatureService
import geopandas as gpd
import os
from shapely.geometry import Point

wfs_url = "https://data.geopf.fr/wfs/ows"

# Connexion
wfs = WebFeatureService(url=wfs_url, version="2.0.0")

verbose=True

for layer_name in wfs.contents:
    if ('LIDAR-HD' in layer_name):
        path = 'lidar_hd_tools/LIDAR-HD_metadata/'
        output_file = f"{layer_name.replace(':', '_')}.geojson"
        if output_file not in os.listdir(path):
            if verbose:
                print(f"Downloading layer: {layer_name}")
            response = wfs.getfeature(typename=layer_name, outputFormat="application/json")
            with open(path+output_file, "wb") as f:
                f.write(response.read())
            if verbose:
                print(f"Saved as: {output_file} in {path}")


def get_blocs(path='lidar_hd_tools/LIDAR-HD_metadata/'):
    return gpd.read_file(path+'IGNF_NUAGES-DE-POINTS-LIDAR-HD_bloc.geojson')

def bloc_finder(lat,lon):
    blocs = get_blocs()
    blocs = blocs[blocs.contains(Point([lon, lat]))].reset_index(drop=True)
    zone = blocs.loc[0,'name']
    date = blocs.loc[0, 'timestamp'].to_pydatetime()
    return zone, date

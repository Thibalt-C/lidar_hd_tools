import owslib.feature.wfs200
from owslib.wfs import WebFeatureService
import owslib
import geopandas as gpd
import io
import numpy as np
from shapely.geometry import Polygon, Point
import pandas as pd
import xarray as xr
import time
import rioxarray
from tqdm import tqdm
from typing import Tuple, Optional


def connect_wfs(
        url : str = "https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities"
) -> owslib.feature.wfs200.WebFeatureService_2_0_0 :

    wfs = WebFeatureService(url=url, version="2.0.0")

    return wfs


def get_bd_topo(
        boundaries : Tuple[float],
        feature : str,
        epsg : str,
        wfs : owslib.feature.wfs200.WebFeatureService_2_0_0
) -> gpd.GeoDataFrame :

    for layer_name in wfs.contents:
        if (f'BDTOPO_V3:{feature}' in layer_name):

            ok = False
            ntries = 0
            max_tries = 3
            while not ok:

                try:
                    response = wfs.getfeature(typename=layer_name,
                                              bbox=boundaries,
                                              outputFormat="application/json")
                    with io.BytesIO(response.read()) as f:
                        gdf = gpd.read_file(f).to_crs(epsg)
                    ok = True

                except:
                    ntries += 1
                    if ntries > max_tries:
                        raise KeyError(f"Request error: file cannot be downloaded (code {response.status_code})")


    return gdf



def divide_into_smaller_bboxes(
        dataset : xr.Dataset,
        size : Optional[float] = 250.0 # meters
) -> gpd.GeoDataFrame :

    x , y = np.meshgrid(dataset.x, dataset.y)
    decim = int(size/abs(dataset.x.values[0]-dataset.x.values[1]))

    try: # if geographic mask exists
        x[dataset.mask!=1] = np.nan
        y[dataset.mask!=1] = np.nan
    except:
        pass

    x = x[::decim,::decim]
    y = y[::decim,::decim]

    dx = abs(dataset.x.values[0]-dataset.x.values[decim])
    dy = abs(dataset.y.values[0]-dataset.y.values[decim])

    for row in range(x.shape[0]):
        if not np.isnan(x[row]).all():
            min_idx = np.nanargmin(x[row,:])
            max_idx = np.nanargmax(x[row,:])
            if min_idx>0:
                x[row, min_idx-1] = x[row, min_idx] - dx
                y[row, min_idx-1] = y[row, min_idx]
            if max_idx<x.shape[1]-1:
                x[row, max_idx+1] = x[row, max_idx] + dx
                y[row, max_idx+1] = y[row, max_idx]

    for col in range(y.shape[1]):
        if not np.isnan(y[:,col]).all():
            min_idx = np.nanargmin(y[:,col])
            max_idx = np.nanargmax(y[:,col])
            if max_idx>0:
                y[max_idx-1, col] = y[max_idx, col] + dy
                x[max_idx-1, col] = x[max_idx, col]
            if min_idx<y.shape[0]-1:
                y[min_idx+1, col] = y[min_idx, col] - dy
                x[min_idx+1, col] = x[min_idx, col]

    points = np.stack([x[np.isfinite(x)].flatten(),y[np.isfinite(y)].flatten()], axis=1)
    bboxes = []
    for point in points:
        xmin = point[0]-dx/2
        xmax = point[0]+dx/2
        ymin = point[1]-dy/2
        ymax = point[1]+dy/2

        bbox = Polygon([(xmin, ymin),
                        (xmax, ymin),
                        (xmax, ymax),
                        (xmin, ymax)
                        ])

        bboxes.append(bbox)

    bboxes_gdf = gpd.GeoDataFrame(geometry=bboxes, crs=dataset.rio.crs).to_crs("EPSG:4326")

    return bboxes_gdf



def get_buildings(
        dataset : xr.Dataset,
        verbose : Optional[bool] = True
) -> gpd.GeoDataFrame :

    wfs = connect_wfs()

    bboxes_gdf = divide_into_smaller_bboxes(dataset)

    iterator = tqdm(range(len(bboxes_gdf)), total=len(bboxes_gdf), desc="Loading buildings from BD-TOPO") if verbose else range(len(bboxes_gdf))

    for row in iterator:

        bounds = bboxes_gdf.iloc[row].geometry.bounds

        box_gdf = get_bd_topo(bounds,
                             feature="batiment",
                             epsg=f"EPSG:{dataset.rio.crs.to_epsg()}",
                             wfs=wfs)

        time.sleep(0.1) # avoid overloading the server

        if row==0:
            gdf = box_gdf.dropna(axis=1, how='all')

        else:
            gdf = (pd.concat([gdf,box_gdf.dropna(axis=1, how='all')])
                   .drop_duplicates()
                   .reset_index(drop=True))

    return gdf



def get_buildings_mask(
        dataset : xr.Dataset,
        verbose : Optional[bool] = True
) -> xr.Dataset :
    """
    Downloads a rasterised version of the buildings map from BD TOPO (IGN)
    with a resolution matching the used dataset.

    Parameters:
    ----------
    dataset : `xarray.Dataset`
        Dataset of a given spatial resolution and geocoded (using rioxarray)
    verbose : bool, optional
        Controls the verbosity (activated or deactivated). Default is True.

    Returns:
    ----------
    dataset : `xarray.Dataset`
        Input dataset with added buildings mask layer
            """

    gdf = get_buildings(dataset, verbose=verbose)

    x, y = np.meshgrid(dataset.x.values, dataset.y.values)

    points = np.stack([x[dataset.mask == 1], y[dataset.mask == 1]], axis=-1)

    is_building = np.zeros(dataset.mask.shape).astype(np.uint8)
    is_building[dataset.mask == 1] = gdf.union_all().intersects([Point(point) for point in points])

    dataset["buildings_mask"] = xr.DataArray(is_building==1, # bool
                                        dims=('y', 'x'),
                                        attrs={"standard_name": "Building pixels",
                                               "units": "no units",
                                               "plot_kwargs": {"cmap": "Oranges",
                                                               "add_colorbar": False
                                                               }
                                               }
                                        )

    return dataset



def get_water_mask(dataset : xr.Dataset) -> xr.Dataset :
    """
    Downloads a rasterised version of the water map from BD TOPO (IGN)
    with a resolution matching the used dataset.
    Water below bridges or buildings is normally excluded.

    Parameters:
    ----------
    dataset : `xarray.Dataset`
        Dataset of a given spatial resolution and geocoded (using rioxarray)

    Returns:
    ----------
    dataset : `xarray.Dataset`
        Input dataset with added water mask layer
    """

    wfs = connect_wfs()

    bounds = dataset.DSM.rio.reproject("epsg:4326").rio.bounds() # WGS84 bounds
    crs = dataset.rio.crs.to_epsg()

    gdf = get_bd_topo(bounds,
                     feature="surface_hydrographique",
                     epsg=f"EPSG:{crs}",
                     wfs=wfs).dropna(axis=1, how='all').drop_duplicates().reset_index(drop=True)

    is_water = np.zeros(dataset.mask.shape).astype(np.uint8)

    if len(gdf)!=0:
        x, y = np.meshgrid(dataset.x.values, dataset.y.values)
        points = np.stack([x[dataset.mask==1], y[dataset.mask==1]], axis=-1)
        is_water[dataset.mask==1] = gdf.union_all().intersects([Point(point) for point in points])

    gdf = get_bd_topo(bounds,
                      feature="construction_surfacique",
                      epsg=f"EPSG:{crs}",
                      wfs=wfs).dropna(axis=1, how='all').drop_duplicates().reset_index(drop=True)

    if len(gdf)!=0:
        gdf = gdf.loc[(gdf['nature'] == 'Pont') | (gdf['nature'] == 'Ecluse')].reset_index(drop=True)
        is_bridge = np.full(dataset.mask.shape, 0)
        is_bridge[dataset.mask == 1] = gdf.union_all().intersects([Point(point) for point in points])
        is_water[is_bridge == True] = 0

    is_water[is_water==False] = 0

    dataset["water_mask"] = xr.DataArray(is_water == 1, # bool
                                    dims=('y', 'x'),
                                    attrs={"standard_name": "Water pixels",
                                           "units": "no units",
                                           "plot_kwargs":{"cmap":"Blues",
                                                          "add_colorbar":False
                                                          }
                                           },
                                    )

    return dataset
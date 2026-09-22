import laspy
import numpy as np
import requests
import os
import pandas as pd
import xarray as xr
from tqdm import tqdm
from .folder_manager import lidar_tiles
from typing import List, Optional, Tuple


def download_lidar(
        lidar_urls : List[str],
        lidar_filenames : List[str],
        lidar_path : Optional[str] = lidar_tiles,
        decimation_factor : Optional[int] = 10,
        verbose : Optional[bool] = True
) -> List[laspy.LasData] :
    """

    Parameters:
    ----------
    lidar_urls : list of strings
        URLs of the LiDAR files (3D point clouds) to download
    lidar_filenames : list of strings
        filenames of the LiDAR files to download
    lidar_path : string, optional
        location where to save the LiDAR files
    decimation_factor : int, optional
        decimation factor to apply to the LiDAR files (number of points to keep)
    verbose : bool, optional
        controls the verbosity (activated or deactivated). Default is True.

    Returns:
    ----------
    clouds : list of `laspy.LasData`
        list of `laspy.LasData` objects containing the (eventually decimated) 3D point clouds of each tile
    """

    clouds = []

    iterator = tqdm(enumerate(lidar_filenames), total=len(lidar_filenames), desc="Loading LiDAR data") if verbose else enumerate(lidar_filenames)

    for n, filename in iterator:

        if not os.path.exists(lidar_path+filename):
            ntries = 0
            max_tries = 3
            ok=False
            while not ok:
                response = requests.get(lidar_urls[n])
                if response.status_code == 200:
                    with open(lidar_path+filename, "wb") as f:
                        f.write(response.content)
                        ok=True
                else:
                    ntries += 1
                    if ntries > max_tries:
                        raise KeyError(f"Request error: file cannot be downloaded (code {response.status_code})")

        las = laspy.read(lidar_path+filename)
        decimated_las = decimate_points(las, factor=decimation_factor)  # Garde 10% des points
        clouds.append(decimated_las)

    return clouds


def decimate_points(
        las : laspy.LasData,
        factor : int
) -> laspy.LasData:

    points = las.points
    n_points = len(points)
    n_keep = int(n_points / factor)
    keep_indices = np.random.choice(n_points, n_keep, replace=False)

    return las[keep_indices]


def density_per_point(
        x : np.ndarray,
        y : np.ndarray,
        bounds : Tuple[float],
        lengths : Tuple[int],
        name : str
) -> np.ndarray :

    dx = abs(bounds[0]-bounds[2])/lengths[0]
    dy = abs(bounds[1]-bounds[3])/lengths[1]
    x_bins = np.linspace(bounds[0]-dx/2, bounds[2]+dx/2, lengths[0]+1)
    y_bins = np.linspace(bounds[1]-dy/2, bounds[3]+dy/2, lengths[1]+1)

    x_indices = np.digitize(x, x_bins) - 1
    y_indices = np.digitize(y, y_bins) - 1

    valid_mask = (
            (x_indices >= 0) &
            (x_indices < lengths[0]) &
            (y_indices >= 0) &
            (y_indices < lengths[1])
    )

    x_indices = x_indices[valid_mask]
    y_indices = y_indices[valid_mask]

    df = pd.DataFrame({
        'x_idx': x_indices,
        'y_idx': y_indices,
        'class': ['class']*len(x_indices)
    })

    counts = df.groupby(['x_idx', 'y_idx', 'class']).size().unstack(fill_value=0)

    density_map = np.zeros((len(y_bins)-1, len(x_bins)-1))

    iterator = tqdm(counts.iterrows(), total=counts.size, desc=f"Computing {name} density map") if name!="" else counts.iterrows()

    for (x, y), row in iterator:
        density_map[-y, x] = row.get('class',0)

    return density_map



def get_vegetation_cover(
        dataset : xr.Dataset,
        clouds : List[laspy.LasData],
        verbose : Optional[bool] = True
) -> xr.Dataset :
    """
    Parameters:
    ----------
    dataset : `xarray.Dataset`
        dataset of a given spatial resolution and geocoded (using rioxarray)
    clouds : list of `laspy.LasData`
        list of `laspy.LasData` objects containing the (eventually decimated) 3D point clouds of each tile
    verbose : bool, optional
        controls the verbosity (activated or deactivated). Default is True.

    Returns:
    ----------
    dataset : `xarray.Dataset`
        Input dataset with added vegetation cover layer
    """

    x = []
    y = []

    for cloud in clouds:
        vegetation = np.where((cloud.classification>=3) & (cloud.classification<=5))
        x.extend(cloud.x[vegetation])
        y.extend(cloud.y[vegetation])

    bounds = [dataset.x.min().values, dataset.y.min().values,
                  dataset.x.max().values, dataset.y.max().values]
    lengths = [len(dataset.x), len(dataset.y)]
    vegetation = density_per_point(x, y, bounds, lengths, "vegetation cover" if verbose else "")

    dataset["vegetation"] = xr.DataArray(vegetation,
                                     dims=('y', 'x'),
                                     attrs={"standard_name": "Vegetation cover",
                                            "units": "pt/pixel",
                                            "plot_kwargs":{"cmap":"Greens",
                                                           "vmin":0,
                                                           "vmax":vegetation.max()
                                                           }
                                            }
                                     )

    return dataset
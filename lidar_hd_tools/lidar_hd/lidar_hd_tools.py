from .metadata import get_metadata
from .folder_manager import check_folders
from .tiles_tools import download_tiles, dem_dsm_xarray, compute_subproducts
from .point_cloud_tools import download_lidar, get_vegetation_cover
from ..utils import clip_dataset, compress_dataset
from geopandas import GeoDataFrame
from xarray import Dataset
from laspy import LasData
from typing import Optional, Tuple, List, Union


def download_data(
        gdf : GeoDataFrame,
        decimation_factor : Optional[int] = 5,
        lidar_decimation_factor : Optional[int] = 10,
        build_dataset : Optional[bool] = True,
        data_for_derivation : Optional[str] = "DSM",
        threshold_for_warning : Optional[int] = 10,
        verbose : Optional[bool] = True
) -> Union[Dataset, Tuple[Dataset, List[LasData]]] :
    """
    Allows the downloading of the digital elevation model (DEM), the digital surface model (DSM) and
    the 3D point clouds for of a given location.

    Parameters:
    ----------
    gdf : `geopandas.GeoDataFrame`
        geo-file of the location of interest
    decimation_factor : int, optional
        decimation factor to apply to the rasterized DEM and DSM
    lidar_decimation_factor : int, optional
        decimation factor to apply to the LiDAR point clouds
    build_dataset : bool, optional
        whether to compute extra layers or not. Default is True.
    data_for_derivation : string, optional
        digital model to be used to derive part of the extra layers. Must be one of "DSM" or "DEM". The default is "DSM".
    threshold_for_warning : int, optional
        threshold number of tiles at which a warning is raised. Default is 10.
    verbose : bool, optional
        controls the verbosity (activated or deactivated). Default is True.

    Returns:
    ----------
    (for `build_dataset=False`)

    unbuilt_dataset : `xarray.Dataset`
        dataset containing the digital elevation model (DEM) and digital surface model (DSM)
    clouds : list of `laspy.LasData`
        list of `laspy.LasData` objects containing the (eventually decimated) 3D point clouds

    *or* (for `build_dataset=True`)

    dataset : `xarray.Dataset`
        dataset containing the DSM, DEM, and extra-layers (see `compute_subproducts` function)
    """

    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)

    projection, urls, filenames = get_metadata(gdf)

    if len(urls[0]) >= threshold_for_warning:
        print(
            ImportWarning(f"The selected area contains {len(urls[0])} tiles.\n" +
                          "Please insure there is enough storage before proceeding."))
        _ = input("Press any key to continue or [Q] to exit... ").strip().lower()
        if _ == 'q':
            raise KeyboardInterrupt()

    check_folders()

    sets = download_tiles(urls[1], urls[0],
                          filenames[1], filenames[0],
                          decimation_factor=decimation_factor,
                          verbose=verbose)

    unbuilt_dataset = dem_dsm_xarray(sets, projection)
    unbuilt_dataset = clip_dataset(unbuilt_dataset, gdf)

    clouds = download_lidar(urls[2], filenames[2], decimation_factor=lidar_decimation_factor, verbose=verbose)

    if build_dataset:

        dataset = compute_subproducts(unbuilt_dataset,
                                      data_for_derivation=data_for_derivation,
                                      verbose=verbose)
        dataset = get_vegetation_cover(dataset, clouds, verbose=verbose)
        dataset = clip_dataset(dataset, gdf)

        dataset = compress_dataset(dataset, verbose=verbose)

        return dataset

    else:
        return unbuilt_dataset, clouds
from lidar_hd_tools.metadata import get_metadata
from lidar_hd_tools.folder_manager import lidar_tiles, DSM_tiles, DEM_tiles
from lidar_hd_tools.tiles_tools import download_tiles, dem_dsm_xarray, compute_subproducts, original_resolution
from lidar_hd_tools.point_cloud_tools import download_lidar, get_vegetation_cover
from lidar_hd_tools.utils import clip_dataset, compress_dataset, geodataframe_from_coordinates




def download_data(gdf,
                  decimation_factor = 5,
                  lidar_decimation_factor = 10,
                  build_dataset=True,
                  data_for_derivation="DSM",
                  threshold_for_warning=10,
                  verbose=True
                  ):

    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)

    projection, urls, filenames = get_metadata(gdf)

    if len(urls[0]) >= threshold_for_warning:
        print(ImportWarning(f"The selected area contains {len(urls[0])} tiles. Please insure there is enough storage before proceeding."))
        _ = input("Press any key to continue or [Q] to exit...").strip().lower()
        if _ == 'q':
            raise KeyboardInterrupt()

    sets = download_tiles(urls[1], urls[0], filenames[1], filenames[0],
                          decimation_factor=decimation_factor,
                          verbose=verbose)

    unbuilt_dataset = dem_dsm_xarray(sets, projection)
    unbuilt_dataset = clip_dataset(unbuilt_dataset, gdf)

    clouds = download_lidar(urls[2], filenames[2], decimation_factor=lidar_decimation_factor, verbose=verbose)

    if build_dataset:

        dataset = compute_subproducts(unbuilt_dataset,
                                      resolution=original_resolution*decimation_factor,
                                      data_for_derivation=data_for_derivation,
                                      verbose=verbose)
        dataset = get_vegetation_cover(dataset, clouds, verbose=verbose)
        dataset = clip_dataset(dataset, gdf)

        dataset = compress_dataset(dataset, verbose=verbose)

        return dataset

    else:
        return unbuilt_dataset, clouds
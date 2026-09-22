import numpy as np
import requests
import os
import time
import xarray as xr
import rioxarray as rxr
from cmcrameri.cm import cmaps
from tqdm import tqdm
from rvt.vis import sky_view_factor, slope_aspect
from .shadow import add_shadow
from .folder_manager import DSM_tiles, DEM_tiles
from typing import List, Optional, Tuple

original_resolution = 0.5 # m
tile_size = 2000 # m

def download_tiles(
        dsm_tiles_urls : List[str],
        dem_tiles_urls : List[str],
        dsm_tiles_filenames : List[str],
        dem_tiles_filenames : List[str],
        decimation_factor : Optional[int] = 10,
        dem_tiles_path : Optional[str] = DEM_tiles,
        dsm_tiles_path : Optional[str] = DSM_tiles,
        verbose : Optional[bool] = True
) -> Tuple[np.ndarray, np.ndarray] :

    def _process_tiles(urls, filenames, tiles_path, data_type):

        iterator = tqdm(
            enumerate(urls), total=len(urls), desc=f"Loading {data_type}"
        ) if verbose else enumerate(urls)

        for n, url in iterator:
            filename = filenames[n]
            filepath = os.path.join(tiles_path, filename)
            if not os.path.exists(filepath):
                response = requests.get(url)
                with open(filepath, "wb") as f:
                    f.write(response.content)

        datasets = []
        for filename in filenames:
            filepath = os.path.join(tiles_path, filename)
            try:
                da = rxr.open_rasterio(filepath, masked=True)
            except: # avoid corrupted files
                os.remove(filepath)
                response = requests.get(url)
                with open(filepath, "wb") as f:
                    f.write(response.content)
                    time.sleep(1)
                da = rxr.open_rasterio(filepath, masked=True)

            da_coarse = da.coarsen(x=decimation_factor, y=decimation_factor, boundary="trim").mean()
            datasets.append(da_coarse)

        merged = xr.combine_by_coords(datasets)
        X, Y = np.meshgrid(merged.x.values, merged.y.values)
        Z = merged.values.squeeze()

        return np.stack([X, Y, Z])

    dsm = _process_tiles(dsm_tiles_urls, dsm_tiles_filenames, dsm_tiles_path, "DSM")
    dem = _process_tiles(dem_tiles_urls, dem_tiles_filenames, dem_tiles_path, "DEM")

    return dsm, dem



def dem_dsm_xarray(
        sets : Tuple[np.ndarray, np.ndarray],
        projection : str
) -> xr.Dataset :

    dataset = xr.Dataset(
        {

            'DSM': xr.DataArray(
                sets[0][2], dims=['y', 'x'],
                coords={'x': sets[0][0, 0, :], 'y': sets[0][1, :, 0]},
                attrs={'standard_name': "Digital surface model",
                       'units': 'm',
                       'plot_kwargs':{"cmap":cmaps["batlow"]}}
            ),

            'DEM': xr.DataArray(
                sets[1][2], dims=['y', 'x'],
                coords={'x': sets[1][0, 0, :], 'y': sets[1][1, :, 0]},
                attrs={'standard_name': "Digital elevation model",
                       'units': 'm',
                       'plot_kwargs':{"cmap":cmaps["batlow"]}}
            )

        }
    )

    dataset.rio.write_crs(projection, inplace=True)

    return dataset



def compute_subproducts(
        dataset : xr.Dataset,
        data_for_derivation : Optional[str] = "DSM",
        verbose : Optional[bool] = True
) -> xr.Dataset :

    resolution = dataset.rio.resolution()[0]

    dataset = add_shadow(dataset, resolution=resolution, data_for_derivation=data_for_derivation, verbose=verbose)

    if verbose:
        print("Computing DHM, SVF, slope gradient, slope aspect...")
    dataset['DHM'] = dataset.DSM - dataset.DEM

    dataset["SVF"] = (('y','x') , sky_view_factor(dataset[data_for_derivation],
                                                  resolution=resolution,
                                                  svf_n_dir=8,
                                                  svf_r_max=10
                                                  )['svf']
                      )

    slope = slope_aspect(dataset[data_for_derivation],resolution_x=resolution,resolution_y=resolution)
    dataset["slope_grad"] = (('y','x') , slope['slope'])
    dataset["aspect"] = (('y','x') , slope['aspect'])



    dataset.DHM.attrs = {'standard_name': "Digital height model",
                         'units': 'm',
                         'plot_kwargs': {'cmap': cmaps["batlow"],
                                         'vmin':dataset.DHM.min(),
                                         'vmax':dataset.DHM.max()}
                         }

    dataset.SVF.attrs = {'standard_name': "Sky view factor",
                         'units': 'no units',
                         'plot_kwargs':{'cmap':cmaps["grayC"],
                                        'vmin':0, 'vmax':1}
                         }

    dataset.slope_grad.attrs = {'standard_name': "Slope gradient",
                                'units': 'rd',
                                'plot_kwargs':{'cmap':cmaps["tofino"],
                                               'vmin':0, 'vmax':np.pi}
                                }

    dataset.aspect.attrs = {'standard_name': "Slope aspect",
                            'units': 'rd',
                            'plot_kwargs':{'cmap':cmaps["vikO"],
                                           'vmin':-np.pi, 'vmax':np.pi}
                            }

    return dataset
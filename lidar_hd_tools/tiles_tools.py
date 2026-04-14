import numpy as np
import requests
import os
import time
import xarray as xr
import rioxarray as rxr
import cmcrameri.cm as cm
from tqdm import tqdm
from rvt.vis import sky_view_factor, slope_aspect
from lidar_hd_tools.shadow import add_shadow
from lidar_hd_tools.folder_manager import DSM_tiles, DEM_tiles

original_resolution = 0.5 # m
tile_size = 2000 # m

def download_tiles(dsm_tiles_urls,
                   dem_tiles_urls,
                   dsm_tiles_filenames,
                   dem_tiles_filenames,
                   decimation_factor = 10,
                   dem_tiles_path=DEM_tiles,
                   dsm_tiles_path=DSM_tiles,
                   verbose=True
                   ):

    def _process_tiles(urls, filenames, tiles_path, data_type):

        iterator = tqdm(enumerate(urls), total=len(urls), desc=f"Loading {data_type}") if verbose else enumerate(urls)

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



def dem_dsm_xarray(sets,
                   projection
                   ):

    dataset = xr.Dataset(
        {

            'DSM': xr.DataArray(
                sets[0][2], dims=['y', 'x'],
                coords={'x': sets[0][0, 0, :], 'y': sets[0][1, :, 0]},
                attrs={'standard_name': "Digital surface model",
                       'units': 'm',
                       'plot_kwargs':{"cmap":cm.batlow}}
            ),

            'DEM': xr.DataArray(
                sets[1][2], dims=['y', 'x'],
                coords={'x': sets[1][0, 0, :], 'y': sets[1][1, :, 0]},
                attrs={'standard_name': "Digital elevation model",
                       'units': 'm',
                       'plot_kwargs':{"cmap":cm.batlow}}
            )

        }
    )

    dataset.rio.write_crs(projection, inplace=True)

    return dataset



def compute_subproducts(dataset, resolution, data_for_derivation="DSM", verbose=True):

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
                         'plot_kwargs': {'cmap': cm.batlow,
                                         'vmin':dataset.DHM.min(),
                                         'vmax':dataset.DHM.max()}
                         }

    dataset.SVF.attrs = {'standard_name': "Sky view factor",
                         'units': 'no units',
                         'plot_kwargs':{'cmap':cm.grayC,
                                        'vmin':0, 'vmax':1}
                         }

    dataset.slope_grad.attrs = {'standard_name': "Slope gradient",
                                'units': 'rd',
                                'plot_kwargs':{'cmap':cm.tofino,
                                               'vmin':0, 'vmax':np.pi}
                                }

    dataset.aspect.attrs = {'standard_name': "Slope aspect",
                            'units': 'rd',
                            'plot_kwargs':{'cmap':cm.vikO,
                                           'vmin':-np.pi, 'vmax':np.pi}
                            }

    return dataset
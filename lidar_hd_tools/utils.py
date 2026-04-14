import numpy as np
import rioxarray
import xarray as xr



def clip_dataset(dataset, gdf):

    dataset = dataset.rio.clip(gdf.geometry.values, gdf.crs)

    mask = np.where(np.isfinite(dataset.DEM.values), True, False)

    if "mask" in list(dataset.keys()):
        dataset.mask.data = mask
    else:
        dataset['mask'] = xr.DataArray(mask,
                                       dims=('y', 'x'),
                                       coords={"y": dataset.y, "x": dataset.x},
                                       attrs={"standard_name": "Geographic mask",
                                              "plot_kwargs": {"cmap": "grey", "add_colorbar": False}
                                              }
                                       )
    return dataset


def compress_dataset(dataset, verbose=False):

    original_size = dataset.nbytes / 1e9 # GB

    for layer in dataset.keys():
        dtype = dataset[layer].dtype
        if dtype == float:
            dataset[layer] = dataset[layer].astype("float32")
        elif (dtype == int) & (dtype != np.uint8):
            dataset[layer] = dataset[layer].astype("uint8")

        unique = np.unique(dataset[layer].values)
        valid_mask = ~np.isnan(dataset[layer].values)
        if len(unique[np.isfinite(unique)]) <= 2:
            dataset[layer] = dataset[layer].astype("bool")
            dataset[layer] = dataset[layer].where(valid_mask, False)

    for coord in list(dataset.coords):
        dtype = dataset.coords[coord].dtype
        if dtype == float:
            dataset.coords[coord] = dataset.coords[coord].astype("float32")

    compressed_size = dataset.nbytes / 1e9

    if verbose:
        print(f"Compressed, {original_size:.2f} GB -> {compressed_size:.2f} GB")

    return dataset




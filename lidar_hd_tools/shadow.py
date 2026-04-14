import numpy as np
from rvt.vis import horizon_generate_pyramids
from scipy.interpolate import RectBivariateSpline
import xarray as xr
import cmcrameri.cm as cm
from tqdm import tqdm


def get_shadow(dem,
                     resolution,
                     shadow_az=315,
                     shadow_el=35,
                     max_fine_radius=100,
                     num_directions=32,
                     ve_factor=1,
                     no_data=None
                     ):
    """
    Modified from rvt.vis module (Žiga Kokalj, Žiga Maroh, Krištof Oštir, Klemen Zakšek and Nejc Čož, 2022).
    Original code: https://rvt-py.readthedocs.io/en/latest/_modules/rvt/vis.html#sky_illumination
    """
    pyramid_scale = 2
    max_pyramid_radius = 20

    if not (10000 >= ve_factor >= -10000):
        raise Exception("rvt.visualization.sky_illumination: ve_factor must be between -10000 and 10000!")
    if shadow_az > 360 or shadow_az < 0:
        raise Exception("rvt.visualization.sky_illumination: shadow_az must be between 0 and 360!")
    if shadow_el > 90 or shadow_el < 0:
        raise Exception("rvt.visualization.sky_illumination: shadow_el must be between 0 and 90!")
    if resolution < 0:
        raise Exception("rvt.visualization.sky_illumination: resolution must be a positive number!")

    if no_data is not None:
        dem[dem == no_data] = np.nan

    dem = dem.astype(np.float32)
    dem = dem * ve_factor

    pyramid = horizon_generate_pyramids(dem,
                                        num_directions=num_directions,
                                        max_fine_radius=max_fine_radius,
                                        max_pyramid_radius=max_pyramid_radius,
                                        pyramid_scale=pyramid_scale, )
    n_levels = np.max([i for i in pyramid])

    conv_to = int(np.floor(pyramid_scale / 2.))
    if (pyramid_scale % 2) == 0:
        conv_from = 1 - conv_to
    else:
        conv_from = -conv_to
    da = np.pi / num_directions

    shadow_out = np.zeros(dem.shape, dtype=np.float32)
    horizon_out = np.zeros(dem.shape, dtype=np.float32)

    _ = np.array([d for d in pyramid[0]["shift"]])
    i = np.argmin(np.abs(_ - (360 - shadow_az)))
    shadow_az = _[i]

    for i_dir, direction in enumerate(pyramid[0]["shift"]):
        dir_rad = np.radians(direction)
        max_slope = np.zeros(pyramid[n_levels]["dem"].shape, dtype=np.float32) - 1000

        for i_level in reversed(range(n_levels + 1)):
            height = pyramid[i_level]["dem"]
            move = pyramid[i_level]["shift"]

            for i_rad, radius in enumerate(move[direction]["distance"]):
                shift_indx = move[direction]["shift"][i_rad]
                _ = np.fmax((np.roll(height, shift_indx, axis=(0, 1)) - height) / radius, 0.)
                max_slope = np.fmax(max_slope, _)

            if i_level > 0:
                lin_fine = pyramid[i_level - 1]["i_lin"] + (
                        conv_from + max_pyramid_radius * pyramid_scale - max_pyramid_radius)
                col_fine = pyramid[i_level - 1]["i_col"] + (
                        conv_from + max_pyramid_radius * pyramid_scale - max_pyramid_radius)
                lin_coarse = pyramid[i_level]["i_lin"] * pyramid_scale
                col_coarse = pyramid[i_level]["i_col"] * pyramid_scale
                interp_spline = RectBivariateSpline(lin_coarse, col_coarse, max_slope, kx=1, ky=1)
                max_slope = interp_spline(lin_fine, col_fine)

        _ = np.arctan(max_slope)
        if direction == shadow_az:
            horizon_out = np.degrees(_[max_pyramid_radius:-max_pyramid_radius, max_pyramid_radius:-max_pyramid_radius])
            shadow_out = (horizon_out < shadow_el) * 1

            return shadow_out



def add_shadow(dataset, resolution, data_for_derivation, verbose=True):

    dataset.coords['sun_elevation'] = np.linspace(0, 90, 9)
    dataset.coords['sun_azimuth'] = np.linspace(0, 360 - 360 / 16, 16)
    dataset.sun_elevation.attrs = {"standard_name": "Sun elevation", "units": "°"}
    dataset.sun_azimuth.attrs = {"standard_name": "Sun azimuth", "units": "°"}

    def shadow_wrapper(dem, sun_azimuth, sun_elevation, resolution):
        return get_shadow(
            dem,
            shadow_az=sun_azimuth,
            shadow_el=sun_elevation,
            resolution=resolution,
        ) == 0  # is shadow

    sun_azimuths = dataset.coords["sun_azimuth"].values
    sun_elevations = dataset.coords["sun_elevation"].values
    combinations = [(az, el) for el in sun_elevations for az in sun_azimuths]

    shadow_results = np.zeros((len(sun_elevations), len(sun_azimuths), *dataset[data_for_derivation].shape), dtype=bool)

    iter_combinations = tqdm(combinations, total=len(combinations),
                             desc="Computing shadow") if verbose else combinations

    for idx, (az, el) in enumerate(iter_combinations):
        shadow_results[idx // len(sun_azimuths), idx % len(sun_azimuths)] = shadow_wrapper(
            dataset[data_for_derivation], az, el, resolution
        )

    dataset["shadow"] = xr.DataArray(
        shadow_results,
        dims=("sun_elevation", "sun_azimuth", "y", "x"),
        coords={
            "sun_elevation": dataset.coords["sun_elevation"],
            "sun_azimuth": dataset.coords["sun_azimuth"],
            "y": dataset.coords["y"],
            "x": dataset.coords["x"],
        },
    )


    # dataset["shadow"] = xr.apply_ufunc(
    #     shadow_wrapper,
    #     dataset[data_for_derivation],
    #     dataset.coords["sun_azimuth"],
    #     dataset.coords["sun_elevation"],
    #     input_core_dims=[
    #         ["y", "x"],  # DSM
    #         [],  # sun_azimuth (scalar)
    #         [],  # sun_elevation (scalar)
    #     ],
    #     output_core_dims=[["y", "x"]],
    #     kwargs={
    #         "resolution": resolution,
    #     },
    #     vectorize=True,
    #     output_dtypes=[np.bool_],
    #     exclude_dims=set(),
    # )

    dataset.shadow.attrs = {'standard_name': "Shadow",
                            'units': 'no units',
                            'plot_kwargs': {'cmap': cm.grayC_r,
                                            'vmin': 0,
                                            'vmax': 1,
                                            "add_colorbar": False
                                            }
                            }

    return dataset
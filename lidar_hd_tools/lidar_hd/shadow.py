import numpy as np
from rvt.vis import horizon_generate_pyramids
from scipy.interpolate import RectBivariateSpline
import xarray as xr
from cmcrameri.cm import cmaps
from tqdm import tqdm
from pandas import DatetimeIndex
import pvlib
from typing import Optional


def get_shadow(
        dem : np.ndarray,
        resolution : float,
        shadow_az : Optional[float] = 315,
        shadow_el : Optional[float] = 35,
        max_fine_radius : Optional[float] = 100,
        num_directions : Optional[int] = 32,
        ve_factor : Optional[float] = 1,
        no_data : Optional[float] = None
) -> np.ndarray :
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



def add_shadow(
        dataset : xr.Dataset,
        resolution : float,
        data_for_derivation : str,
        timestamps : Optional[DatetimeIndex] = None,
        azimuth_resolution : Optional[float] = 22.5,
        elevation_resolution : Optional[float] = 5.0,
        verbose : Optional[bool] = True
) -> xr.Dataset :


    if timestamps is None: # tries all combinations

        dataset.coords['sun_elevation'] = np.arange(0, 90+elevation_resolution, elevation_resolution)
        dataset.coords['sun_azimuth'] = np.arange(0, 360, azimuth_resolution)
        sun_azimuths = dataset.coords["sun_azimuth"].values
        sun_elevations = dataset.coords["sun_elevation"].values
        combinations = [(az, el) for el in sun_elevations for az in sun_azimuths]
        shadow_results = np.zeros((len(sun_elevations), len(sun_azimuths), *dataset[data_for_derivation].shape),
                                  dtype=bool)
        dims = ("sun_elevation", "sun_azimuth", "y", "x")
        coords = {"sun_elevation": dataset.coords["sun_elevation"],
                  "sun_azimuth": dataset.coords["sun_azimuth"],
                  "y": dataset.coords["y"],
                  "x": dataset.coords["x"]
                  }

    else: # adds time coordinate to determine the Sun's position
        dataset.coords["time"] = timestamps.to_numpy(dtype="datetime64[ns]")
        wgs84_coords = dataset.DSM.rio.reproject(dst_crs="EPSG:4326").coords
        loc = pvlib.location.Location(latitude=wgs84_coords["y"].values.mean(),
                                      longitude=wgs84_coords["x"].values.mean(),
                                      altitude=dataset.DSM.mean().values)
        sun_pos = loc.get_solarposition(dataset.time.values)
        for angle in ["azimuth", "elevation"]:
            dataset[f'sun_{angle}'] = xr.DataArray(data=sun_pos[angle].values,
                                                    dims=["time"], coords={"time": dataset.time})
        combinations = [(dataset.sun_azimuth.values[i], dataset.sun_elevation.values[i])
                        for i in range(len(dataset.time))
                        ]
        shadow_results = np.zeros((len(dataset.time), *dataset[data_for_derivation].shape),
                                  dtype=bool)
        dims = ("time", "y", "x")
        coords = {"time": dataset.time, "y": dataset.y, "x": dataset.x}

    dataset.sun_elevation.attrs = {"standard_name": "Sun elevation", "units": "°"}
    dataset.sun_azimuth.attrs = {"standard_name": "Sun azimuth", "units": "°"}

    def shadow_wrapper(dem, sun_azimuth, sun_elevation, resolution):
        return get_shadow(
            dem,
            shadow_az=sun_azimuth,
            shadow_el=sun_elevation,
            resolution=resolution,
        ) == 0  # is shadow

    iter_combinations = tqdm(combinations, total=len(combinations),
                             desc="Computing shadow") if verbose else combinations

    for idx, (az, el) in enumerate(iter_combinations):
        if timestamps is None:
            shadow_results[idx // len(sun_azimuths), idx % len(sun_azimuths)] = shadow_wrapper(
                dataset[data_for_derivation], az, el, resolution
            )
        else:
            if (el <= 90) & (el >= 0):
                shadow_results[idx] = shadow_wrapper(dataset[data_for_derivation], az, el, resolution)

    dataset["shadow"] = xr.DataArray(
        shadow_results,
        dims=dims,
        coords=coords
    )

    dataset.shadow.attrs = {'standard_name': "Shadow",
                            'units': 'no units',
                            'plot_kwargs': {'cmap': cmaps["grayC_r"],
                                            'vmin': 0,
                                            'vmax': 1,
                                            "add_colorbar": False
                                            }
                            }

    return dataset
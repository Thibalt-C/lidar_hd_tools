import cartopy.mpl.geoaxes
import matplotlib.pyplot as plt
from matplotlib.collections import QuadMesh
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import cartopy.crs as ccrs
import numpy as np
from xarray import Dataset
from pyproj import CRS
from typing import Tuple, Optional, Union

def get_projection(crs : CRS) -> ccrs.Projection :
    """
    Converts a CRS object from pyproj to cartopy projection for visualisation.

    Parameters:
    ----------
    crs : `pyproj.CRS`
        Projection object from pyproj

    Returns:
    ----------
    projection : `cartopy.crs.Projection`
        Projection object for cartopy
    """

    epsg = crs.to_epsg()
    if epsg == 4326:
        projection = ccrs.PlateCarree()
    else:
        projection = ccrs.epsg(epsg)

    return projection


def plot_dataset(
        dataset : Dataset,
        layer : str,
        ax : Optional[Union[cartopy.mpl.geoaxes.GeoAxes, cartopy.mpl.geoaxes.GeoAxesSubplot]] = None,
        gridlines : Optional[bool] = True,
        **kwargs
) -> Tuple[
    Union[cartopy.mpl.geoaxes.GeoAxes,
    cartopy.mpl.geoaxes.GeoAxesSubplot],
    QuadMesh
] :
    """
    Generates a plot of a given layer from a geocoded dataset.

    Parameters:
    ----------
    dataset : `xarray.Dataset`
        dataset geocoded using rioxarray
    layer : str
        layer name to plot, must be a 2-dimensional spatial layer and exist in the dataset
    ax : `cartopy.mpl.geoaxes.GeoAxes` | `cartopy.mpl.geoaxes.GeoAxesSubplot`, optional
        existing cartopy axis to plot on, if None, a new axis is created. Default is None
    gridlines : bool, optional
        whether to draw gridlines for geographic coordinates or not. Default is True
    **kwargs : dict
        Accepts kwargs from matplotlib.pyplot.pcolormesh function (e.g. cmap, vmin, vmax, ...)

    Returns:
    ----------
    ax : `cartopy.mpl.geoaxes.GeoAxes` | `cartopy.mpl.geoaxes.GeoAxesSubplot`
        cartopy axis containing the plot
    quadmesh : `matplotlib.collections.QuadMesh`
        object containing the plotted data and its properties
    """

    if layer not in dataset.data_vars:
        raise Exception(f"Layer {layer} not found in dataset.")

    if dataset[layer].dims != ('y','x'):
        raise Exception(f"Layer {layer} is not a spatial layer. Reduce the other dimensions first.")

    if dataset.rio.crs is None:
        raise Exception("Dataset has no CRS. Use `dataset.rio.write_crs()` to set the CRS.")

    projection = get_projection(dataset.rio.crs)

    if ax==None:
        fig, ax = plt.subplots(subplot_kw={"projection": projection}, figsize=(20, 8))
    elif (type(ax) != cartopy.mpl.geoaxes.GeoAxesSubplot) | (type(ax) != cartopy.mpl.geoaxes.GeoAxes):
        raise Exception("ax must be a `cartopy.mpl.geoaxes.GeoAxesSubplot` or `cartopy.mpl.geoaxes.GeoAxes`.")

    if "plot_kwargs" in dataset[layer].attrs:
        plot_kwargs = dataset[layer].plot_kwargs.copy()
    else:
        plot_kwargs = {}

    plot_kwargs.update(kwargs)

    to_plot = dataset[layer].copy()

    if to_plot.dtype == 'bool':
        to_plot = to_plot.where(to_plot, np.nan) # mask False values

    if "mask" in dataset.data_vars:
        to_plot = to_plot.where(dataset.mask)

    quadmesh = to_plot.plot(ax=ax, **plot_kwargs)

    if gridlines:
        gl = ax.gridlines(
            draw_labels=True,  # Enable labels for the gridlines
            linewidth=1,  # Line width of the gridlines
            color='black',  # Color of the gridlines
            alpha=0.5,  # Transparency of the gridlines
            linestyle='--',  # Line style of the gridlines
        )
        gl.xformatter = LONGITUDE_FORMATTER
        gl.yformatter = LATITUDE_FORMATTER

    ax.axis('off')

    plt.tight_layout()

    return ax, quadmesh


def plot_orthophoto(
        dataset : Dataset,
        ax : Optional[Union[cartopy.mpl.geoaxes.GeoAxes, cartopy.mpl.geoaxes.GeoAxesSubplot]] = None
) -> Union[cartopy.mpl.geoaxes.GeoAxes,
cartopy.mpl.geoaxes.GeoAxesSubplot] :
    """
    Generates a plot of the ortho-image layer of a geocoded dataset.

    Parameters:
    ----------
    dataset : `xarray.Dataset`
        dataset geocoded using rioxarray, must contain an ortho-image layer as "orthoimage"
    ax : `cartopy.mpl.geoaxes.GeoAxes` | `cartopy.mpl.geoaxes.GeoAxesSubplot`, optional
        existing cartopy axis to plot on, if None, a new axis is created. Default is None

    Returns:
    ----------
    ax : `cartopy.mpl.geoaxes.GeoAxes` | `cartopy.mpl.geoaxes.GeoAxesSubplot`
        cartopy axis containing the plot
    """

    if "orthoimage" not in dataset.data_vars:
        raise Exception("Dataset has no orthoimage.\n" +
                        "Use `lidar_hd_tools.get_orthoimage(dataset)` to add the orthoimage.")

    projection = get_projection(dataset.rio.crs)

    if ax is None:
        fig, ax = plt.subplots(subplot_kw={"projection": projection}, figsize=(20, 8))

    dataset.orthoimage.plot.imshow(ax=ax, robust=True)

    ax.axis('off')

    plt.tight_layout()

    return ax
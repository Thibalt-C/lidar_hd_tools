from owslib.wms import WebMapService
from rasterio.io import MemoryFile
import rioxarray as rxr
import xarray as xr
from typing import Optional
import numpy as np
from .utils import split_bbox


def get_orthoimage(
        dataset : xr.Dataset,
        url : Optional[str] = "https://data.geopf.fr/wms-r?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities",
        layer : Optional[str] = "HR.ORTHOIMAGERY.ORTHOPHOTOS"
) -> xr.Dataset :
    """
    Downloads the ortho-image from BD ORTHO (IGN) with a resolution matching the used dataset.

    Parameters:
    ----------
    dataset : `xarray.Dataset`
        Dataset of a given spatial resolution and geocoded (using rioxarray)
    url : string, optional
        url of the Web Map Service providing the ortho-image
    layer : string, optional
        name of the layer in the Web Map Service providing the ortho-image

    Returns:
    ----------
    dataset : `xarray.Dataset`
        Input dataset with added ortho-image
    """

    wms = WebMapService(url, version="1.3.0")

    # bbox
    xmin = dataset.x[0].values
    xmax = dataset.x[-1].values
    ymin = dataset.y[-1].values
    ymax = dataset.y[0].values

    tiles = split_bbox(xmin, ymin, xmax, ymax, width=len(dataset.x), height=len(dataset.y))

    ortho = np.zeros((3, len(dataset.y), len(dataset.x)), dtype=np.uint8)

    for tile in tiles:

        img = wms.getmap(
            layers=[layer],
            size=tile["size"],
            bbox=tile["bbox"],
            srs=f"EPSG:{dataset.rio.crs.to_epsg()}",
            format="image/geotiff"
        )

        with MemoryFile(img.read()) as memfile:
            tile_data = (
                rxr.open_rasterio(memfile)
                .squeeze()
                .values
            )

        ortho[:,tile["row_slice"],tile["col_slice"]] = tile_data

    dataset["orthoimage"] = xr.DataArray(
        data=ortho,
        coords={
            "channel": ["red", "green", "blue"],
            "y": dataset.y,
            "x": dataset.x,
        },
        dims=("channel", "y", "x"),
        attrs={
            "standard_name": "Orthographic image",
            "original resolution": "20 cm",
            "units": "no units",
        },
    )

    return dataset
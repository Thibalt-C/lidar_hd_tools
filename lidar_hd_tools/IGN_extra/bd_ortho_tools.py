from owslib.wms import WebMapService
from rasterio.io import MemoryFile
import rioxarray as rxr
import xarray as xr
from typing import Optional


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

    # download WMS data
    img = wms.getmap(layers=[layer],
                     size=(len(dataset.x), len(dataset.y)),
                     bbox=(xmin, ymin, xmax, ymax),
                     srs=f"EPSG:{dataset.rio.crs.to_epsg()}",
                     format='image/geotiff')

    # save as a rioxarray instance
    with MemoryFile(img) as memfile:
        orthophoto = rxr.open_rasterio(memfile).squeeze()
        orthophoto = orthophoto.rename({"band": "channel"})
        orthophoto.coords["channel"] = ["red", "green", "blue"]
        orthophoto.assign_attrs({"standard_name": "Orthographic image",
                                 "original resolution": "20 cm",
                                 "units": "no units"})

        dataset["orthoimage"] = xr.DataArray(
            data=orthophoto.data,
            attrs=orthophoto.attrs,
            dims=('channel', 'y', 'x')
        )

    return dataset
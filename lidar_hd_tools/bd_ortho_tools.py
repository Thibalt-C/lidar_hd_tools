from owslib.wms import WebMapService
from rasterio.io import MemoryFile
import rioxarray as rxr
import xarray as xr

url = "https://data.geopf.fr/wms-r?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities"
wms = WebMapService(url, version="1.3.0")
layer = "HR.ORTHOIMAGERY.ORTHOPHOTOS"

def get_orthoimage(dataset):

    xmin = dataset.x[0].values
    xmax = dataset.x[-1].values
    ymin = dataset.y[-1].values
    ymax = dataset.y[0].values

    img = wms.getmap(layers=[layer],
                     size=(len(dataset.x), len(dataset.y)),
                     bbox=(xmin, ymin, xmax, ymax),
                     srs=f"EPSG:{dataset.rio.crs.to_epsg()}",
                     format='image/geotiff')

    with MemoryFile(img) as memfile:
        orthophoto = rxr.open_rasterio(memfile).squeeze()
        orthophoto = orthophoto.rename({"band": "channel"})
        orthophoto.coords["channel"] = ["red", "green", "blue"]
        orthophoto.assign_attrs({"standard_name": "Orthographic image",
                                 "original resolution": "20 cm",
                                 "units": "no units"})

        dataset["orthoimage"] = xr.DataArray(data=orthophoto.data, attrs=orthophoto.attrs, dims=('channel', 'y', 'x'))

    return dataset
from owslib.wms import WebMapService
from rasterio.io import MemoryFile
import rioxarray as rxr
import xarray as xr
import numpy as np

url = "https://data.geopf.fr/wms-r/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities"
wms = WebMapService(url, version="1.3.0")
layer = "OCSGE.COUVERTURE.2021-2023" #"OCSGE.ARTIF.2021-2023"


def get_land_occupation(dataset):

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
        land_occupation = rxr.open_rasterio(memfile).squeeze()

        r = land_occupation.sel(band=1).values
        g = land_occupation.sel(band=2).values
        b = land_occupation.sel(band=3).values
        rgb = np.stack([r, g, b],axis=-1)

        red = (rgb[:,:,0]>rgb[:,:,1]) & (rgb[:,:,0]>rgb[:,:,2])
        red_mask = np.where(red, True, False)

        blue = (rgb[:,:,2]>rgb[:,:,0]) & (rgb[:,:,2]>rgb[:,:,1])
        blue_mask = np.where(blue, True, False)

        green = (rgb[:,:,1]>rgb[:,:,0]) & (rgb[:,:,1]>rgb[:,:,2])
        green_mask = np.where(green, True, False)

        yellow = (rgb[:,:,0]>rgb[:,:,2]) & (rgb[:,:,1]>rgb[:,:,2]) & (rgb[:,:,2]>150)
        yellow_mask = np.where((~red)&(~green)&(~blue), True, False)

        dataset["vegetalized"] = xr.DataArray(green_mask,
                                              dims=('y', 'x'),
                                              attrs={"standard_name": "Vegetation/grass pixels",
                                                     "units": "no units",
                                                     "plot_kwargs": {"cmap": "Greens",
                                                                     "add_colorbar": False
                                                                     }
                                                     }
                                              )
        dataset["mineralized"] = xr.DataArray(yellow_mask,
                                              dims=('y', 'x'),
                                              attrs={"standard_name": "Mineralized pixels",
                                                     "units": "no units",
                                                     "plot_kwargs": {"cmap": "Greys",
                                                                     "add_colorbar": False
                                                                     }
                                                     }
                                              )
        dataset["water_mask"] = xr.DataArray(blue_mask,
                                              dims=('y', 'x'),
                                              attrs={"standard_name": "Water pixels",
                                                     "units": "no units",
                                                     "plot_kwargs": {"cmap": "Blues",
                                                                     "add_colorbar": False
                                                                     }
                                                     }
                                              )

        dataset["artificial"] = xr.DataArray(red_mask,
                                              dims=('y', 'x'),
                                              attrs={"standard_name": "Artificial pixels",
                                                     "units": "no units",
                                                     "plot_kwargs": {"cmap": "Reds",
                                                                     "add_colorbar": False
                                                                     }
                                                     }
                                              )

    return dataset
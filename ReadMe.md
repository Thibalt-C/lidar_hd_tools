# `lidar_hd_tools`: for a quick and efficient loading of IGN’s LiDAR HD data


<div align=center>
	
![PyPI Python Version](https://img.shields.io/pypi/pyversions/lidar_hd_tools?link=www.pypi.org%2Fp%2Flidar-hd-tools)
![PyPI Version](https://img.shields.io/pypi/v/lidar_hd_tools?link=www.pypi.org%2Fp%2Flidar-hd-tools)
![GitHub last commit](https://img.shields.io/github/last-commit/Thibalt-C/lidar_hd_tools)

![ ](https://github.com/Thibalt-C/lidar_hd_tools/blob/95b48b9a84f3e573f3af6222947d57a9d781d3ec/example_figures/fig1.png)

</div>

- [Module overview](#module-overview)
- [About LiDAR HD programme](#about-lidar-hd-programme)
- [Requirements](#requirements)
- [Getting started](#getting-started)
	- [Importing the library](#importing-the-library)
	- [Default folders](#default-folders)
	- [Workflow starting from a `geopandas.GeoDataFrame` object](#workflow-starting-from-a-geopandasgeodataframe-object)
	- [Workflow starting from coordinates](#workflow-starting-from-coordinates)
	- [BD-TOPO implementations](#bd-topo-implementations)
	- [OCS-GE implementations](#ocs-ge-implementations)
	- [BD-ORTHO implementations](#bd-ortho-implementations)
- [Visualisation](#visualisation)
- [Command-line-interface tools](#command-line-interface-tools)

## Module overview

As IGN (Institut national de l’information géographique et forestière, France) is progressively covering French territory with high density LiDAR data (LiDAR HD), the parsing of this data using the currently provided API is not well efficient yet. The `lidar_hd_tools`  python package aims to provide an easy-to-use framework for loading LiDAR HD data, with very few mandatory parameters to provide while keeping the possibility to personalise the query to fit various uses, from urban morphology to research in mountainous context.

![ ](https://github.com/Thibalt-C/lidar_hd_tools/blob/95b48b9a84f3e573f3af6222947d57a9d781d3ec/example_figures/fig2.png)


## About LiDAR HD programme

LiDAR HD programme is one of the main projects currently managed by IGN, with numerous implications for public action in territories, as well as research works at local or regional scale. All the French territory (except French Guyana) is expected to be covered by the end of 2026 — current coverage is provided [here](https://macarte.ign.fr/carte/mThSup/diffusionMNxLiDARHD). Digital models, namely elevation (DEM), surface (DSM) and height (DHM) are produced and delivered by IGN, as well as 3D point clouds. All of these products are grouped by 4 km² tiles, that can be downloaded using API requests or the dedicated [online platform](https://cartes.gouv.fr/telechargement/IGNF_NUAGES-DE-POINTS-LIDAR-HD). If the online platform provides tools to manually select several tools efficiently, there is for now no automated downloading of such data for geocoded polygons.

## Installation

`lidar_hd_tools` can be installed from the PyPI repository:

```
pip install lidar-hd-tools
```

## Getting started

### Importing the library

To import `lidar_hd_tools`, simply use:

```
import lidar_hd_tools
```

Further in this tutorial we will use the alias `lhd`, as we will assume that we did the following command:

```
import lidar_hd_tools as lhd
```

### Default folders

When imported, `lidar_hd_tools` will look for folders where to store imported data. You can check the configured folders by typing on a python script / Jupyter notebook:

```
lhd.current_folders()
```

This will show the folders associated to each type of data.

If you want to edit those folders, you can use the following command, with `key='DSM'` or `key='DEM'` or `key='lidar'`:

```
lhd.change_folder(key)
```

### Workflow starting from a `geopandas.GeoDataFrame` object

As many geographic data can be converted into `geopandas.GeoDataFrame` class objects, `lidar_hd_tools` has been optimised to work with this kind of object.

The only requirement is to have a **known coordinate reference system (CRS)**. This will allow projection into other CRS when necessary. As the conversion is done by module’s functions, there is no sensitivity to the initial CRS of the provided `geopandas.GeoDataFrame`.

You might use the following to launch the workflow:

```
dataset = download_data(gdf,
                  	decimation_factor = 5,
                  	lidar_decimation_factor = 10,
                  	build_dataset=True,
                  	data_for_derivation="DSM",
                  	threshold_for_warning=10,
                  	verbose=True
                  	):
```

Below is a description of such function and its parameters. Decimation factors make more efficient the loading and computation of data as python objects, but are not affecting the size of the stored files (that are full-sized data). Derived data computed when `build_dataset` is `True` are: sky viewing factor (SVF), slope aspect, slope gradient and shadow — shadow is computed for 9 by 16 different sun positions, for now there is no handy parameter to change this amount. The `data_for_derivation` parameter is to change depending on the context: sometimes it is meaningful to use the DSM (e.g. urban studies) and other times the DEM (e.g. landslide monitoring). DHM is also derived by subtracting DSM with DEM, as well as vegetation cover by counting the number of classified points of LiDAR data per pixel.

Unbuilt mode (`build_dataset=False`) can be used if you are more interested by the point cloud itself, as it outputs both the unbuilt dataset (containing only DSM and DEM) and the list of point clouds associated to the same area of interest.

Built and unbuilt dataset are both `xarray.Dataset` objects, with a `rio` accessor from `rioxarray` (see [here](https://corteva.github.io/rioxarray/html/getting_started/getting_started.html) for detail). This allows them to be reprojected easily, using `xarray.Dataset.rio.reproject`.

### Workflow starting from coordinates

If you want to extract information around a given point (of coordinates `lon` and `lat` in EPSG:4326), you can use the following to create a geocoded rectangle (here of 200 by 200 meters) around your point as a `geopandas.GeoDataFrame` class object:

```
gdf = lhd.geodataframe_from_coordinates(lat, lon, size=200)
```

Then you can use the workflow described above.


### BD-TOPO® (IGN) implementations

Using BD-TOPO data from IGN, `lidar_hd_tools` offers the possibility to add two extra-layers to your built/unbuilt dataset.

To enrich the previously obtained `dataset` with a water mask, you may use the following:

```
dataset = lhd.get_water_mask(dataset)
```

Water mask uses the BD-TOPO vectorised inventory of rivers, basins and reservoirs, mapped at a high spatial resolution. Bridges are also recovered to not count the overlapping area as water, although it is observed that not all the bridges are on the database.

Note that this is one of the two methods existing to get a water mask. Using it on a given `dataset ` will overwrite the water mask obtained using the other method, if it has been computed (see OCS-GE implementations).

Similarly, enriching a `dataset` with a buildings mask can be done using:

```
dataset = lhd.get_buildings_mask(dataset)
```


### OCS-GE® (IGN) implementations

*More to come... The functions can be tested but documentation and more solid version of the code are not here yet.*


### BD-ORTHO® (IGN) implementations

*More to come... The functions can be tested but documentation and more solid version of the code are not here yet.*

## Visualisation

As datasets are `xarray.Dataset` objects, it is easy to visualise them (e.g. using `dataset.SVF.plot()`. Hence, some visualisation tools are provided if you want to have rapid results without fine-tuning yourself the figures.

The following sub-library can be used for visualisation:

```
import lidar_hd_tools.visualisation as vis
```

Spatial and 2-dimensional layers of the dataset can then be visualised with:

```
ax, quadmesh = vis.plot_dataset(dataset, layer)
```

The ortho-image eventually added to the dataset using `lhd.get_orthoimage(dataset)` function can be visualised using:

```
ax = vis.plot_orthophoto(dataset)
```

## Command-line-interface tools

The `lidar_hd_tools` module can be called on a terminal using the following command:

```
python -m lidar_hd_tools
```

This will open a command-line-interface (CLI) from which it is possible to download the LiDAR data (3D point clouds + DEM + DSM) by:
1. giving a squared area of interest based on the center’s geographic coordinates and an extent in meters
2. giving a path towards a geofile that can be opened using `geopandas.read_file` function / `pickle.load` function.

It is also possible from this CLI to change the location of the downloaded data.

After the data is downloaded, it is possible to:
1. compute extra-layers after having specified whether it has to be done using the DEM or the DSM
2. plot layers of the dataset, including shadow (sun elevation and azimuth angles will be prompted in this case)
3. save the dataset as a netcdf4 (`.nc` format) file

A command with arguments that would automate a download without prompts is not available for now. It is then better to import the module (see [getting started](#getting-started) chapter) and to create a dedicated python script.

# `lidar_hd_tools`: for a quick and efficient loading of IGN’s LiDAR HD data

**Module’s name**: `lidar_hd_tools` \
**Release**: 0.01 \
**Date**: March 2026 \
**Author**: Thibault CHARDON (IPGP, Université Paris Cité) \
\
***CC-BY 4.0 licence** (https://creativecommons.org/licenses/by/4.0/deed.fr).*

{{TOC}}

## Module overview

As IGN (Institut national de l’information géographique et forestière, France) is progressively covering French territory with high density LiDAR data (LiDAR HD), the parsing of this data using the currently provided API is not well efficient yet. The `lidar_hd_tools`  python package aims to provide an easy-to-use framework for loading LiDAR HD data, with very few mandatory parameters to provide while keeping the possibility to personalise the query to fit various uses, from urban morphology to research in mountainous context.

## About LiDAR HD programme

LiDAR HD programme is one of the main projects currently managed by IGN, with numerous implications for public action in territories, as well as research works at local or regional scale. All the French territory (except French Guyana) is expected to be covered by the end of 2026 — current coverage is provided [here](https://macarte.ign.fr/carte/mThSup/diffusionMNxLiDARHD). Digital models, namely elevation (DEM), surface (DSM) and height (DHM) are produced and delivered by IGN, as well as 3D point clouds. All of these products are grouped by 1 km$^2$ tiles, that can be downloaded using API requests or the dedicated [online platform](https://cartes.gouv.fr/telechargement/IGNF_NUAGES-DE-POINTS-LIDAR-HD). If the online platform provides tools to manually select several tools efficiently, there is for now no automated downloading of such data for geocoded polygons.

## Requirements

Several libraries are required to work with a fully functional `lidar_hd_tools` module. See below the code to create an ideal environment for the module to work properly. First we create an empty environment:

```
conda create --name lidar_hd_env python=3.10
```

We can activate it using:

```
conda activate lidar_hd_env 
```

Then we install the required libraries available on channel `conda-forge`:

```
conda install -c conda-forge numpy pandas xarray \
							 matplotlib cartopy cmcrameri \
							 geopandas shapely pyproj \
							 laspy pillow \
							 owslib requests
```

and one extra library for relief visualisation, based on [Zakšek et al. (2011)](https://www.mdpi.com/2072-4292/3/2/398) & [Kokalj (2025)](https://doi.org/10.1002/arp.70002):

```
conda install -c rvtpy rvt_py
```

If the installation fails on your environment please consider using an empty environment as described above.

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

When imported, `lidar_hd_tools` will look for folders where to store imported data. If not existing it will try to create them. The name and path of those folder can be set on the `folders.json` file, which can be found inside the `lidar_hd_tools/` library folder. If this process fails, the module can be imported anyway but there is a risk of further error while saving downloaded data in your computer. 

You can check the configured folders by typing on a python script / Jupyter notebook:

```
lhd.current_folders()
```

This will show the folders associated to each type of data.

### 
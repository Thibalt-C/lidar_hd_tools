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

LiDAR HD programme is one of the main projects currently managed by IGN, with numerous implications for public action in territories, as well as research works at local or regional scale. All the French territory (except French Guyana) is expected to be covered by the end of 2026 — current coverage is provided [here](https://macarte.ign.fr/carte/mThSup/diffusionMNxLiDARHD). Digital models, namely elevation (DEM), surface (DSM) and height (DHM) are produced and delivered by IGN, as well as 3D point clouds. All of these products are grouped by 1 km^2 tiles, that can be downloaded using API requests or the dedicated [online platform](https://cartes.gouv.fr/telechargement/IGNF_NUAGES-DE-POINTS-LIDAR-HD). If the online platform provides tools to manually select several tools efficiently, there is for now no automated downloading of such data for geocoded polygons.

## Requirements

Several libraries are required to work with a fully functional `lidar_hd_tools` module. See below the code to create an ideal environment for the module to work properly. First we create an empty environment:

```
conda create --name lidar_hd_env python=3.10
conda activate lidar_hd_env 
```

Then we install the required libraries:

```
conda install numpy,
conda install -c conda-forge geopandas,
```

## Getting started
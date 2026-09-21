"""Python library for quick use of IGN's LiDAR-HD data.

Author: Thibault Chardon
Creation date: 2026-01-06

The lidar_hd_tools python package aims to provide an easy-to-use framework for loading LiDAR HD data,
with very few mandatory parameters to provide while keeping the possibility to personalise the query
to fit various uses, from urban morphology to research in mountainous context.
"""


__all__ = [
    "folders",
    "current_folders",
    "change_folder",
    "download_data",
    "clip_dataset",
    "compress_dataset",
    "geodataframe_from_coordinates",
    "get_buildings_mask",
    "get_water_mask",
    "get_land_occupation",
    "get_orthoimage",
    "visualisation"
]

from .folder_manager import folders, current_folders, change_folder
from .lidar_hd_tools import download_data, clip_dataset, compress_dataset
from .bd_topo_tools import get_buildings_mask, get_water_mask
from .ocs_ge_tools import get_land_occupation
from .bd_ortho_tools import get_orthoimage
from .utils import clip_dataset, compress_dataset, geodataframe_from_coordinates
from . import visualisation


from importlib_metadata import version
__version__ = version("lidar_hd_tools")
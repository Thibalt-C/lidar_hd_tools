'''
lidar_hd_tools INITIALIZATION SCRIPT
Description: Initializes the lidar_hd_tools module.
Author: Thibault Chardon
Creation date: 2026-01-06
'''


from lidar_hd_tools.folder_manager import folders, current_folders, change_folder
from lidar_hd_tools.lidar_hd_tools import download_data, clip_dataset, compress_dataset, geodataframe_from_coordinates
from lidar_hd_tools.bd_topo_tools import get_buildings_mask, get_water_mask
from lidar_hd_tools.ocs_ge_tools import get_land_occupation
from lidar_hd_tools.bd_ortho_tools import get_orthoimage
import lidar_hd_tools.visualisation as visualisation

__version__ = "0.1.3"
__authors__ = ['<CHARDON_Thibault>']
__release__ = '2026-09-19'
__releasecomment__ = """ 
Added a CLI when calling the module from a terminal -> python -m lidar_hd_tools
"""

def about():
    print('lidar_hd_tools module\n')
    print(f'version {__version__}\n')
    print(f'Developed by: {__authors__}')
    print(f'{__release__}\n')
    print(f"Comment: {__releasecomment__}")
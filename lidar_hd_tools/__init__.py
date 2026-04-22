'''
lidar_hd_tools INITIALIZATION SCRIPT
Description: Initializes the lidar_hd_tools module.
Author: Thibault Chardon
Creation date: 2026-01-06
'''


from lidar_hd_tools.folder_manager import current_folders
from lidar_hd_tools.lidar_hd_tools import download_data, clip_dataset, compress_dataset, geodataframe_from_coordinates
from lidar_hd_tools.bd_topo_tools import get_buildings_mask, get_water_mask
from lidar_hd_tools.ocs_ge_tools import get_land_occupation
from lidar_hd_tools.bd_ortho_tools import get_orthoimage
import lidar_hd_tools.visualisation as visualisation

version = "0.1.2"
authors = ['<CHARDON_Thibault>']
release_date = '2026-04-22'
comment = """ 
Enahancement of visualisation functions.
Exception added if the folders where to store the downloaded tiles are not found.
"""

def about():
    print('lidar_hd_tools module\n')
    print(f'version {version}\n')
    print(f'Developed by: {authors}')
    print(f'{release_date}\n')
    print(f"Comment: {comment}")
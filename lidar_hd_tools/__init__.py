'''
lidar_hd_tools INITIALIZATION SCRIPT
Description: Initializes the lidar_hd_tools module.
Author: Thibault Chardon
Creation date: 2026-01-06
'''


from lidar_hd_tools.folder_manager import current_folders
from lidar_hd_tools.lidar_hd_tools import download_data
from lidar_hd_tools.bd_topo_tools import get_buildings_mask, get_water_mask
from lidar_hd_tools.ocs_ge_tools import get_land_occupation
from lidar_hd_tools.bd_ortho_tools import get_orthoimage
import lidar_hd_tools.visualisation as visualisation

version = 0.1
authors = ['<CHARDON_Thibault>']
release_date = '2026-04-14'
comment = """ 
More reliable parsing method. 
User interface improved with loading bars. 
Cache data of BD-TOPO and LIDAR HD removed
Implementation of ortho-image superimposition using BD-ORTHO 
Implementation of land-cover superimposition using OCS-GE
"""

def about():
    print('lidar_hd_tools module\n')
    print(f'version {version}\n')
    print(f'Developed by: {authors}')
    print(f'{release_date}\n')
    print(f"Comment: {comment}")
'''
lidar_hd_tools INITIALIZATION SCRIPT
Description: Initializes the lidar_hd_tools module.
Author: Thibault Chardon
Date: 2026-01-06
'''


from lidar_hd_tools.lidar_hd_tools import *
import lidar_hd_tools.visualisation as visualisation

version = 0.01
authors = ['<CHARDON_Thibault>']
release_date = '2026-01-06'
comment = """ First release. """

def about():
    print('lidar_hd_tools module\n')
    print(f'version {version}\n')
    print(f'Developed by: {authors}')
    print(f'{release_date}\n')
    print(f"Comment: {comment}")
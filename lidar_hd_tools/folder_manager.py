import json
import warnings
import os

try:
    with open("lidar_hd_tools/folders.json", "r", encoding="utf-8") as file:
        folders = json.load(file)
except FileNotFoundError:
    warnings.warn("`folders.json` not found. You need to configure a json file.")
    print("Data will be saved in the CWD.")
    folders = {"lidar":"", "DSM":"", "DEM":""}
except json.JSONDecodeError:
    warnings.warn("decode error caused by `folders.json`. Please set a correct json file.")
    print("Data will be saved in the CWD.")
    folders = {"lidar": "", "DSM": "", "DEM": ""}

lidar_tiles = folders["lidar"]
DSM_tiles = folders["DSM"]
DEM_tiles = folders["DEM"]

def current_folders():
    for key in folders.keys():
        print(f"{key}: {folders[key]}")
    return

def check_folders():
    for key in folders.keys():
        if not os.path.exists(folders[key]):
            raise FileNotFoundError(f"Folder {folders[key]} not found.")
    return
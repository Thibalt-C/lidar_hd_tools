import json
import warnings
import os

json_path = "lidar_hd_tools/folders.json"

try:
    with open(json_path, "r", encoding="utf-8") as file:
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

def change_folder(key):

    if key in folders.keys():
        folders[key] = input(f"Enter the path to the {key} folder: ")
    else:
        raise Exception(f"Key {key} not found in folders.json.")

    if not os.path.exists(folders[key]):
        raise FileNotFoundError(f"Folder {folders[key]} not found.")

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(folders, file, indent=4)

    return print(f"-> Saved {key} folder to {folders[key]}")
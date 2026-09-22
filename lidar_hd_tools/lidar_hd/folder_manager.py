"""
folder_manager module
------------------------------
Manages the location of the downloaded data.
"""

import json
import warnings
import os
from typing import Optional
from pathlib import Path

json_path = Path(__file__).parent / "folders.json"
default = {"lidar":".", "DSM":".", "DEM":"."}

try:

    with open(json_path, "r", encoding="utf-8") as file:
        folders = json.load(file)

except FileNotFoundError:

    warnings.warn("`folders.json` not found. You need to configure a json file.")

except json.JSONDecodeError:

    os.remove(json_path) # removing corrupted json file

    warnings.warn("decode error caused by `folders.json`. Corrupted file will be replaced.")

if not os.path.exists(json_path):
    print("Data will be saved in the CWD.")
    folders = default
    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(folders, file, indent=4)

lidar_tiles = folders["lidar"]
DSM_tiles = folders["DSM"]
DEM_tiles = folders["DEM"]


def current_folders():
    """
    Returns the location of each type of downloaded data.
    """
    for key in folders.keys():
        print(f"{key}: {folders[key]}")
    return


def check_folders():
    """
    Verifies the existence of the locations set in folders.json.
    """
    for key in folders.keys():
        if not os.path.exists(folders[key]):
            raise FileNotFoundError(f"Folder {folders[key]} not found.")
    return

def change_folder(
        key : str,
        path : Optional[str] = None
) -> None :
    """
    Allows to change the location of each type of downloaded data.

    Parameters:
    ----------
    key : string
        type of downloaded data. Must be one of "lidar", "DSM" or "DEM".
    path : string, optional
        location where to save the data. Must exist.
    """

    if key in folders.keys():

        if path is None:
            path = input(f"Enter the path to the {key} folder: ")

        if not os.path.exists(path):
            raise FileNotFoundError(f"Folder {path} not found.")

    else:
        raise Exception(f"Key {key} not found in folders.json.")

    folders[key] = path

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(folders, f, indent=4)

    return print(f"-> Saved {key} folder location to {folders[key]}")
"""
Command-line interface of the lidar_hd_tools package.
"""

import lidar_hd_tools as lhd
import geopandas as gpd
import os

if __name__ == "__main__":

    print('\033[1m' +
          "\n\n---------- lidar_hd_tools module ----------" +
          "\nauthor: Thibault CHARDON" +
          "\nhttps://github.com/Thibalt-C/lidar_hd_tools" +
          f"\nVersion {lhd.__version__} from {lhd.__release__}" +
          "\n--------------------------------------------------------------------\n" +
          '\033[0m')

    key = "m" # go to menu


    while key.lower() != "q":

        if key == "m":

            print("\nWelcome! Please choose an option from the menu.\n")

            print("[S] select an squared area of interest based on center coordinates.")
            print("[G] use a geofile as the area of interest")
            print("[F] manage the downloaded file's location")
            print("[Q] quit")

            key = input("\n-> ")


        elif key.lower() == "s":

            lon = float(input("Enter a longitude in decimal degrees: "))
            lat = float(input("Enter a latitude in decimal degrees: "))
            size = float(input("Enter a size in meters: "))

            gdf = lhd.geodataframe_from_coordinates(lon=lon, lat=lat, size=size)

            key = "r" # ready for processing


        elif key.lower() == "g":

            success = False

            while not success:

                filepath = input("\nEnter the file path of the geodata you want to use: ")

                if not os.path.exists(filepath):
                    print("File not found.")
                else:
                    try:
                        gdf = gpd.read_file(filepath)
                        success = True
                    except:
                        print("Error while reading the geodata file.")

                lon, lat = gdf.union_all().centroid.coords[0]

                key = "r"  # ready for processing


        elif key.lower() == "f":

            print("\nHere are the currently configured folders:")

            lhd.current_folders()

            success = False

            while not success:

                name = input("\nType the name of the folder you want to change: ")

                if name not in lhd.folders.keys():
                    print("Folder name not found.")

                try:
                    lhd.change_folder(name)
                    success = True
                except:
                    print("Error while changing the folder. Check if the path is correct.")

            key = "m"  # go to menu


        elif key.lower() == "r":

            resolution = float(input("\nEnter the resolution of the lidar tiles in meters: "))
            decimation_factor = int(resolution * 2) # // 0.5

            outputs = lhd.download_data(gdf,
                                        decimation_factor,
                                        build_dataset=False)

            dataset, _ = outputs

            a = input("Do you want to save the decimated dataset (DSM+DEM) on the CWD? [y]/[n]: ")

            if a.lower() == "y":
                for layer in dataset.data_vars:
                    dataset[layer].attrs["plot_kwargs"] = str(dataset[layer].attrs["plot_kwargs"]) # for netcdf4 compatibility
                filename = f"{str(lon).replace(".","_")}_{str(lat).replace(".","_")}.nc"
                filepath = os.path.join(os.getcwd(), filename)
                dataset.to_netcdf(filepath)
                print(f"Successfully saved dataset -> {filepath}")

            key = "m" # go to menu


        else:

            print("Invalid command!\n")
            key = "m" # go to menu

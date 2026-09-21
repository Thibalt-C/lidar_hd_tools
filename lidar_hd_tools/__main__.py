"""
Command-line interface of the lidar_hd_tools package.
"""

import lidar_hd_tools as lhd
import geopandas as gpd
import pickle
import os
import matplotlib.pyplot as plt

if __name__ == "__main__":

    print('\033[1m' +
          "\n\n---------- lidar_hd_tools module ----------" +
          "\nauthor: Thibault CHARDON" +
          "\nhttps://github.com/Thibalt-C/lidar_hd_tools" +
          f"\nVersion {lhd.__version__}" +
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

            key = input("\n-> ").lower().replace("p","").replace("m","")


        elif key == "s":

            lon = float(input("Enter a longitude in decimal degrees: "))
            lat = float(input("Enter a latitude in decimal degrees: "))
            size = float(input("Enter a size in meters: "))

            gdf = lhd.geodataframe_from_coordinates(lon=lon, lat=lat, size=size)

            key = "r" # ready for processing


        elif key == "g":

            gdf = None

            while gdf is None:

                filepath = input("\nEnter the file path of the geodata you want to use: ")

                if not os.path.exists(filepath):
                    print("File not found.")
                else:
                    try:
                        gdf = gpd.read_file(filepath)
                    except:
                        try:
                            gdf = pickle.load(open(filepath, "rb"))
                        except:
                            print("Error while reading the geodata file.")

            lon, lat = gdf.union_all().centroid.coords[0]

            key = "r"  # ready for processing


        elif key == "f":

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


        elif key == "r":

            resolution = float(input("\nEnter the resolution of the lidar tiles in meters: "))
            decimation_factor = int(resolution * 2) # // 0.5

            outputs = lhd.download_data(gdf,
                                        decimation_factor,
                                        build_dataset=False)

            dataset, clouds = outputs

            key = "p" # go to processing options

        elif key == "p":

            a = ""

            while a != "m":

                print("\nWhat do you want to do with this dataset?:")
                print("[P] plot layers of the dataset")
                print("[D] compute extra-layers (SVF, slope, etc...)")
                print("[S] save the dataset on the CWD")
                print("[M] go back to the menu")

                a = input("\n-> ").lower()

                if a == "s":
                    ds = dataset.copy()
                    for layer in ds.data_vars: # for netcdf4 compatibility
                        ds[layer].attrs["plot_kwargs"] = str(ds[layer].attrs["plot_kwargs"])
                    filename = f"{str(lon).replace(".", "_")}_{str(lat).replace(".", "_")}.nc"
                    filepath = os.path.join(os.getcwd(), filename)
                    ds.to_netcdf(filepath)
                    print(f"\nSuccessfully saved dataset -> {filepath}")

                elif a == "p":
                    print(f"\nAvailable layers: {dataset.data_vars.keys()}")
                    layer = ""
                    while layer not in dataset.data_vars.keys():
                        layer = input("Enter the name of the layer you want to plot: ")
                    if layer == "shadow":
                        az = float(input("Enter the azimuth of the sun in degrees: "))
                        el = float(input("Enter the elevation of the sun in degrees: "))
                        ds = dataset.sel(sun_azimuth=az, sun_elevation=el, method="nearest")
                        lhd.visualisation.plot_dataset(ds, layer)
                    else:
                        lhd.visualisation.plot_dataset(dataset, layer)
                    plt.show()

                elif a == "d":
                    dataset = lhd.tiles_tools.compute_subproducts(dataset,
                                                                  dataset.rio.resolution()[0]
                                                                  )
                    dataset = lhd.point_cloud_tools.get_vegetation_cover(dataset, clouds)
                else:
                    pass

            key = "m"  # go to menu

        else:

            print("Invalid command!\n")
            key = "m" # go to menu

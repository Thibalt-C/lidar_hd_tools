import numpy as np
from PIL import Image
import os
import requests
from pyproj import CRS
import xarray as xr
from pyproj import Transformer
import geopandas as gpd
from shapely.geometry import Point, Polygon
from rvt.vis import sky_view_factor, slope_aspect, hillshade
import laspy
import pandas as pd
import datetime
from sklearn.cluster import DBSCAN
import time
from lidar_hd_tools.download_LiDARHD_blocs import bloc_finder
from lidar_hd_tools.download_BD_TOPO import get_bdtopo
from lidar_hd_tools.folder_manager import lidar_tiles, DSM_tiles, DEM_tiles
import cmcrameri.cm as cm



def download_tiles(dsm_tiles_file='dsm_tiles.txt',
                   dem_tiles_file='dem_tiles.txt',
                   query_mode=False,
                   dem_tiles_path=DEM_tiles,
                   dsm_tiles_path=DSM_tiles,
                   relative_index_x = slice(8,12),
                   relative_index_y = slice(13,17),
                   tile_size=2000,
                   tile_resolution=0.5,
                   decimation_factor = 10,
                   verbose=True
                   ):

    sets = []

    for tiles_file, tiles_path in zip([dsm_tiles_file, dem_tiles_file],
                                      [dsm_tiles_path, dem_tiles_path]):

        if query_mode:

            urls = tiles_file
            filenames = [url.split("=")[-1] for url in urls]

        else:

            if not os.path.exists(tiles_file):
                raise FileNotFoundError(f"file {tiles_file} not found")

            with open(tiles_file, 'r') as f:
                urls = [row.replace('\n','') for row in f]
                filenames = [url.split("=")[-1] for url in urls]

        x_index = [int(filename[relative_index_x]) for filename in filenames]
        y_index = [int(filename[relative_index_y]) for filename in filenames]

        size = tile_size//decimation_factor
        resolution = tile_resolution*decimation_factor

        x = np.full(size*(max(x_index)-min(x_index)+1),np.nan)
        y = np.full(size*(max(y_index)-min(y_index)+1),np.nan)
        X , Y = np.meshgrid(x, y)
        Z = np.full_like(X,np.nan)

        for n,filename in enumerate(filenames):

            if not os.path.exists(tiles_path+filename):
                if verbose:
                    print(f"[{n+1}/{len(filenames)}] Downloading file {filename}",end="\r")
                response = requests.get(urls[n])
                with open(tiles_path+filename, "wb") as f:
                    f.write(response.content)

            if verbose:
                print(f"[{n+1}/{len(filenames)}] Loading file {filename}",end="\r")

            data = Image.open(tiles_path+filename)
            data = np.array(data)[::decimation_factor,::decimation_factor]

            idx_x = x_index[n] - min(x_index)
            idx_y = -y_index[n] + max(y_index)
            rows = slice(idx_y*size, (idx_y+1)*size)
            cols = slice(idx_x*size, (idx_x+1)*size)

            bounds = np.array(urls[n].split("BBOX=")[-1].split("&")[0].split(",")).astype(float)

            X_range = np.arange(cols.start*resolution,
                                cols.stop*resolution,
                                resolution)
            Y_range = np.arange(rows.start*resolution,
                                rows.stop*resolution,
                                resolution)

            easting_range = np.linspace(bounds[0],bounds[2],len(X_range))
            northing_range = np.linspace(bounds[1],bounds[3],len(Y_range))

            Z[rows,cols] = data
            X[rows,cols], Y[rows,cols] = np.meshgrid(easting_range,northing_range)

        x = np.linspace(np.nanmin(X),np.nanmax(X),X.shape[1])
        y = np.linspace(np.nanmin(Y),np.nanmax(Y),X.shape[0])[::-1]
        X , Y = np.meshgrid(x,y)

        set_1 = np.stack([X,Y,Z])
        sets.append(set_1)

    return sets # DSM , DEM



def build_xarray(sets,
                 epsg_data=2154,  # Lambert 93
                 epsg_wgs84=4326 # WGS84
                 ):

    dataset = xr.Dataset(
        {

            'DSM': xr.DataArray(
                sets[0][2], dims=['y', 'x'],
                coords={'x': sets[0][0, 0, :], 'y': sets[0][1, :, 0]},
                attrs={'standard_name': "Digital surface model",
                       'units': 'm',
                       'projection': str(CRS.from_epsg(2154)),
                       'plot_kwargs':{"cmap":cm.batlow}}
            ),

            'DEM': xr.DataArray(
                sets[1][2], dims=['y', 'x'],
                coords={'x': sets[1][0, 0, :], 'y': sets[1][1, :, 0]},
                attrs={'standard_name': "Digital elevation model",
                       'units': 'm',
                       'projection': str(CRS.from_epsg(epsg_data)),
                       'plot_kwargs':{"cmap":cm.batlow}}
            )

        }
    )

    transformer = Transformer.from_crs(f"EPSG:{epsg_data}",
                                       f"EPSG:{epsg_wgs84}",
                                       always_xy=True)

    x_grid, y_grid = np.meshgrid(dataset.x.values, dataset.y.values)
    lons, lats = transformer.transform(x_grid.ravel(), y_grid.ravel())
    dataset.coords['lon'] = (('y', 'x'), lons.reshape(x_grid.shape))
    dataset.coords['lat'] = (('y', 'x'), lats.reshape(y_grid.shape))

    return dataset



def get_tile_id(x,y,
                epsg=2154 # Lambert 93
                ):

    if epsg != 2154:
        transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:2154", always_xy=True)
        x , y = transformer.transform(x,y)

    tile_ids = []
    for x0,y0 in zip(x.ravel(),y.ravel()):
        tile_id = (int(str(x0).split('.')[0][:-3]) , int(str(y0).split('.')[0][:-3])+1)
        tile_ids.append(tile_id)
    return list(np.unique(tile_ids,axis=0))



def generate_tiles_list(gpd_dataframe,
                        epsg=2154, # Lambert 93
                        point_res=50
                        ):

    gpd_dataframe = gpd_dataframe.to_crs(f"EPSG:{epsg}")
    boundaries = gpd_dataframe.geometry.union_all()
    bounds = boundaries.bounds

    X = np.arange(bounds[0],bounds[2],point_res)
    Y = np.arange(bounds[1],bounds[3],point_res)
    X,Y = np.meshgrid(X,Y)
    xy_points = np.column_stack((X.ravel(), Y.ravel()))

    all_points = gpd.GeoDataFrame(
        geometry=[Point(x, y) for x, y in xy_points],
        crs=gpd_dataframe.crs
    )

    points_inside = all_points[all_points.within(boundaries)].reset_index(drop=True)
    tile_ids = get_tile_id(points_inside.geometry.x.values,points_inside.geometry.y.values, epsg=epsg)
    tile_ids = np.unique(tile_ids,axis=0)

    query= "https://data.geopf.fr/wms-r?SERVICE=WMS&VERSION=1.3.0&EXCEPTIONS=text/xml&REQUEST=GetMap&LAYERS=IGNF_LIDAR-HD_{model}_ELEVATION.ELEVATIONGRIDCOVERAGE.LAMB93&FORMAT=image/geotiff&STYLES=&CRS=EPSG:2154&BBOX={x-1}999.75,{y-1}000.25,{x}999.75,{y}000.25&WIDTH=2000&HEIGHT=2000&FILENAME=LHD_FXX_{str_x}_{str_y}_{model}_O_0M50_LAMB93_IGN69.tif"

    queries_set = []

    for model in ['MNS','MNT']:

        queries = []

        for tile_id in list(tile_ids):

            str_tile_id = tile_id.astype(int).astype(str)
            str_tile_id[0] = '0'*(4-len(str_tile_id[0])) + str_tile_id[0]
            str_tile_id[1] = '0'*(4-len(str_tile_id[1])) + str_tile_id[1]

            tile_query = query
            tile_query = tile_query.replace('{x-1}',str(int(tile_id[0]-1)))
            tile_query = tile_query.replace('{y-1}',str(int(tile_id[1]-1)))
            tile_query = tile_query.replace('{x}',str(int(tile_id[0])))
            tile_query = tile_query.replace('{y}',str(int(tile_id[1])))
            tile_query = tile_query.replace('{str_x}',str_tile_id[0])
            tile_query = tile_query.replace('{str_y}',str_tile_id[1])
            tile_query = tile_query.replace('{model}', model)

            queries.append(tile_query)

        queries_set.append(queries)

    DSM_queries , DEM_queries = queries_set

    return DSM_queries, DEM_queries



def compute_subproducts(dataset,resolution,data_for_derivation="DEM"):

    dataset['DHM'] = dataset.DSM - dataset.DEM

    dataset["SVF"] = (('y','x') , sky_view_factor(dataset[data_for_derivation],
                                                  resolution=resolution,
                                                  svf_n_dir=8,
                                                  svf_r_max=10
                                                  )['svf']
                      )

    slope = slope_aspect(dataset[data_for_derivation],resolution_x=resolution,resolution_y=resolution)
    dataset["slope_grad"] = (('y','x') , slope['slope'])
    dataset["aspect"] = (('y','x') , slope['aspect'])

    dataset.coords['sun_elevation'] = np.linspace(0, 90, 5)
    dataset.coords['sun_azimuth'] = np.linspace(0, 360-360/8, 8)
    dataset.sun_elevation.attrs = {"standard_name": "Sun elevation", "units": "°"}
    dataset.sun_azimuth.attrs = {"standard_name": "Sun azimuth", "units": "°"}

    def hillshade_wrapper(dem, sun_azimuth, sun_elevation, resolution_x, resolution_y):
        return hillshade(
            dem,
            resolution_x=resolution_x,
            resolution_y=resolution_y,
            sun_azimuth=sun_azimuth,
            sun_elevation=sun_elevation
        )

    hillshading = xr.apply_ufunc(
        hillshade_wrapper,
        dataset[data_for_derivation],
        dataset.coords["sun_azimuth"],
        dataset.coords["sun_elevation"],
        input_core_dims=[
            ["y", "x"],  # DSM
            [],          # sun_azimuth (scalar)
            [],          # sun_elevation (scalar)
        ],
        output_core_dims=[["y", "x"]],
        kwargs={
            "resolution_x": resolution,
            "resolution_y": resolution,
        },
        vectorize=True,
        exclude_dims=set(),
    )
    dataset["hillshade"] = hillshading

    dataset.DHM.attrs = {'standard_name': "Digital height model",
                         'units': 'm',
                         'projection': dataset.DEM.projection,
                         'plot_kwargs': {'vmin':dataset.DHM.min(),
                                         'vmax':dataset.DHM.max()}
                         }
    dataset.SVF.attrs = {'standard_name': "Sky viewing factor",
                         'units': 'no units',
                         'projection': dataset.DEM.projection,
                         'plot_kwargs':{'cmap':cm.grayC,
                                        'vmin':0, 'vmax':1} }
    dataset.slope_grad.attrs = {'standard_name': "Slope gradient",
                                'units': 'rd',
                                'projection': dataset.DEM.projection,
                                'plot_kwargs':{'cmap':cm.tofino,
                                               'vmin':0, 'vmax':np.pi}
                                }
    dataset.aspect.attrs = {'standard_name': "Slope aspect",
                            'units': 'rd',
                            'projection': dataset.DEM.projection,
                            'plot_kwargs':{'cmap':cm.vikO,
                                           'vmin':-np.pi, 'vmax':np.pi}
                            }
    dataset.hillshade.attrs = {'standard_name': "Hillshade",
                               'units': 'no units',
                               'projection': dataset.DEM.projection,
                               'plot_kwargs':{'cmap':cm.grayC,
                                              'vmin':dataset.hillshade.min(),
                                              'vmax':dataset.hillshade.max(),
                                              "cbar_kwargs": {'orientation': 'horizontal',
                                                              'shrink': 0.75}
                                              }
                               }

    return dataset



def clip_dataset(dataset, gpd_dataframe):

    points = gpd.points_from_xy(dataset.lon.values.flatten(),dataset.lat.values.flatten())
    grid_gdf = gpd.GeoDataFrame(geometry=points)
    clipped_grid = gpd.clip(grid_gdf, gpd_dataframe.union_all())

    xy = np.stack([clipped_grid.geometry.x, clipped_grid.geometry.y], axis=1)

    dx = (dataset.lon.max().values - dataset.lon.min().values) / dataset.sizes['x']
    dy = (dataset.lat.max().values - dataset.lat.min().values) / dataset.sizes['y']

    x_indices = ((xy[:, 0] - dataset.lon.min().values) / dx).astype(int)
    y_indices = ((dataset.lat.max().values-xy[:, 1]) / dy).astype(int)

    mask = np.zeros((dataset.sizes['y'], dataset.sizes['x']), dtype=bool)
    mask[y_indices, x_indices] = True

    dataset['mask'] = (('y','x'), mask)
    dataset.mask.attrs["standard_name"] = "Geographic mask"

    dataset = dataset.where(dataset.mask, drop=True)

    return dataset



def lidar_query_from_dsm(zone, date, dsm_requests,
                         relative_index_x = slice(8,12),
                         relative_index_y = slice(13,17)
                         ):

    text = "https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_{zone}_{date}/LHD_FXX_{x_idx}_{y_idx}_PTS_LAMB93_IGN69.copc.laz"

    lidar_requests = []

    files = [request.split("FILENAME=")[-1] for request in dsm_requests]
    for file in files:
        x_idx, y_idx = file[relative_index_x], file[relative_index_y]
        request = text.replace('{zone}',zone).replace('{date}',date).replace('{x_idx}',x_idx).replace('{y_idx}',y_idx)
        lidar_requests.append(request)

    return lidar_requests



def decimate_points(las, factor=10):
    """Décime les points en gardant un pourcentage aléatoire."""
    points = las.points
    n_points = len(points)
    n_keep = int(n_points / factor)
    keep_indices = np.random.choice(n_points, n_keep, replace=False)
    return las[keep_indices]



def download_lidar(lidar_requests,
                   lidar_path=lidar_tiles,
                   decimation_factor = 10,
                   verbose=True
                   ):

    filenames = [request.split("/")[-1] for request in lidar_requests]
    clouds = []

    for n,filename in enumerate(filenames):

        if not os.path.exists(lidar_path+filename):
            if verbose:
                print(f"[{n+1}/{len(filenames)}] Downloading file {filename}",end="\r")
            response = requests.get(lidar_requests[n])
            if response.status_code == 200:
                with open(lidar_path+filename, "wb") as f:
                    f.write(response.content)
            else:
                raise KeyError(f"Request error: file cannot be downloaded (code {response.status_code})")

        if verbose:
            print(f"[{n+1}/{len(filenames)}] Loading file {filename}",end="\r")

        las = laspy.read(lidar_path+filename)
        decimated_las = decimate_points(las, factor=decimation_factor)  # Garde 10% des points
        clouds.append(decimated_las)


    return clouds



def density_per_point(x,
                      y,
                      bounds,
                      lengths
                      ):

    dx = abs(bounds[0]-bounds[2])/lengths[0]
    dy = abs(bounds[1]-bounds[3])/lengths[1]
    x_bins = np.linspace(bounds[0]-dx/2, bounds[2]+dx/2, lengths[0]+1)
    y_bins = np.linspace(bounds[1]-dy/2, bounds[3]+dy/2, lengths[1]+1)

    x_indices = np.digitize(x, x_bins) - 1
    y_indices = np.digitize(y, y_bins) - 1

    valid_mask = (
            (x_indices >= 0) &
            (x_indices < lengths[0]) &
            (y_indices >= 0) &
            (y_indices < lengths[1])
    )

    x_indices = x_indices[valid_mask]
    y_indices = y_indices[valid_mask]

    df = pd.DataFrame({
        'x_idx': x_indices,
        'y_idx': y_indices,
        'class': ['class']*len(x_indices)
    })

    counts = df.groupby(['x_idx', 'y_idx', 'class']).size().unstack(fill_value=0)

    density_map = np.zeros((len(y_bins)-1, len(x_bins)-1))
    for (x, y), row in counts.iterrows():
        density_map[-y, x] = row.get('class',0)

    return density_map



def get_vegetation_cover(dataset, clouds):

    x = []
    y = []
    for cloud in clouds:
        vegetation = np.where((cloud.classification>=3) & (cloud.classification<=5))
        x.extend(cloud.x[vegetation])
        y.extend(cloud.y[vegetation])
    bounds = [dataset.x.min().values, dataset.y.min().values,
                  dataset.x.max().values, dataset.y.max().values]
    lengths = [len(dataset.x), len(dataset.y)]
    vegetation = density_per_point(x, y, bounds, lengths)

    dataset["vegetation"] = xr.DataArray(vegetation,
                                     dims=('y', 'x'),
                                     attrs={"standard_name": "Vegetation cover",
                                            "units": "pt/pixel",
                                            "plot_kwargs":{"cmap":"Greens",
                                                           "vmin":0,
                                                           "vmax":vegetation.max()
                                                           }
                                            }
                                     )

    return dataset



def get_buildings_cover(dataset, clouds):

    x = []
    y = []
    for cloud in clouds:
        buildings = np.where(cloud.classification==6)
        x.extend(cloud.x[buildings])
        y.extend(cloud.y[buildings])
        bounds = [dataset.x.min().values, dataset.y.min().values,
                  dataset.x.max().values, dataset.y.max().values]
    lengths = [len(dataset.x), len(dataset.y)]
    buildings = density_per_point(x, y, bounds, lengths)

    dataset["buildings"] = xr.DataArray(buildings,
                                    dims=('y', 'x'),
                                    attrs={"standard_name": "Built cover",
                                           "units": "pt/pixel",
                                           "plot_kwargs":{"cmap":"Oranges",
                                                          "vmin":0,
                                                          "vmax":buildings.max()
                                                          }
                                           }
                                    )

    return dataset



def geodataframe_from_coordinates(lat, lon,  # degrees (WGS84)
                                  size=200  # meters
                                  ):
    # plane approximation
    lat_degree = size / 111320.0
    lon_degree = size / (111320.0 * abs(np.cos(np.radians(lat))))

    top = lat + lat_degree / 2
    bottom = lat - lat_degree / 2
    right = lon + lon_degree / 2
    left = lon - lon_degree / 2

    polygon = Polygon([
        (left, top),
        (right, top),
        (right, bottom),
        (left, bottom)
    ])

    gdf = gpd.GeoDataFrame(
        geometry=[polygon],
        crs="EPSG:4326"  # WGS84
    )

    return gdf



def build(sets, clouds, gdf, resolution, data_for_derivation="DSM"):

    dataset = build_xarray(sets)

    dataset = get_vegetation_cover(dataset, clouds)
    dataset = get_buildings_cover(dataset, clouds)

    dataset = clip_dataset(dataset, gdf)

    dataset = compute_subproducts(dataset, resolution, data_for_derivation)

    return dataset


def routine_from_gdf(gdf,
                     decimation_factor=2,
                     lidar_decimation_factor=10,
                     build_dataset=True,
                     original_resolution=0.5,
                     data_for_derivation="DSM",
                     threshold_for_warning=10
                     ):

    gdf = gdf.to_crs(epsg=4326) # WGS89

    DSM_queries, DEM_queries = generate_tiles_list(gdf)
    print(f"There are {len(DSM_queries)} tiles to download.")

    if len(DSM_queries)>=threshold_for_warning:
        print(f"WARNING: LiDAR files would require between {len(DSM_queries)*0.5} and {len(DSM_queries)*2} GB of storage.")
        yes = ''
        while yes not in ['Y','y','n']:
            yes = input("Continue? [Y/n]")
        if yes == 'n':
            raise SystemExit

    print("Loading DSM/DEM tiles...")
    sets = download_tiles(dsm_tiles_file=DSM_queries,
                          dem_tiles_file=DEM_queries,
                          query_mode=True,
                          dem_tiles_path=DEM_tiles,
                          dsm_tiles_path=DSM_tiles,
                      decimation_factor=decimation_factor, verbose=False)

    centroids = [gdf.geometry[i].centroid.coords[0] for i in range(len(gdf))]
    zones_list = [bloc_finder(lon=centroid[0],lat=centroid[1])[0] for centroid in centroids]
    dates_list = [bloc_finder(lon=centroid[0],lat=centroid[1])[1] for centroid in centroids]
    zones = np.unique(zones_list)
    dates = np.unique(dates_list)

    try:

        print("Loading LiDAR data...")

        if len(zones)>1:
            clouds = []
            for n in range(len(zones_list)):
                zone = zones_list[n]
                date = dates_list[n]
                ok = False
                while not ok:
                    try:
                        lidar_request = lidar_query_from_dsm(zone,
                                                             date.strftime("%Y-%m-%d"),
                                                             DSM_queries[n])
                        cloud = download_lidar(lidar_requests=lidar_request,
                                               decimation_factor=lidar_decimation_factor,
                                               lidar_path=lidar_tiles, verbose=False)
                        clouds.append(cloud[0])
                        ok = True
                    except:
                        if date <= datetime.datetime.today():
                            date = date + datetime.timedelta(days=1)
                            time.sleep(0.1) # to limit at 10 requests per second
                        else:
                            raise KeyError("Failed to retrieve the LiDAR data.")

        else:
            date = dates[0]
            ok = False
            while not ok:
                try:
                    lidar_requests = lidar_query_from_dsm(zones[0],
                                                          date.strftime("%Y-%m-%d"),
                                                          DSM_queries)
                    clouds = download_lidar(lidar_requests=lidar_requests,
                                            decimation_factor=lidar_decimation_factor,
                                            lidar_path=lidar_tiles, verbose=False)
                    ok = True
                except:

                    if date <= datetime.datetime.today():
                        date = date + datetime.timedelta(days=1)
                        time.sleep(0.1) # to limit at 10 requests per second
                    else:
                        raise KeyError("Failed to retrieve the LiDAR data.")

    except:
        print("-> LiDAR download failed, please check the zone ID and date of acquisition.")
        clouds = None

    if build_dataset:
        print("Building dataset...")
        try:
            dataset = build(sets, clouds, gdf,
                            resolution=decimation_factor*original_resolution,
                            data_for_derivation=data_for_derivation
                            )
            return dataset
        except:
            raise ImportError("No LiDAR file to use for building.")

    else:
        return sets, clouds, gdf

def save_dataset(dataset, filename):
    dataset_to_save = dataset.copy()
    for key in dataset_to_save.keys():
        for subkey in dataset_to_save[key].attrs.keys():
            if subkey == 'plot_kwargs':
                dataset_to_save[key].attrs[subkey] = str(dataset_to_save[key].attrs[subkey])
    if '.nc' not in filename:
        filename += '.nc'
    dataset_to_save.to_netcdf(filename)
    print(f'Successfully saved as {filename}')
    return



def cluster_buildings(dataset, eps, min_samples=1):

    buildings = dataset.where(dataset['buildings']>0)
    x , y =  np.meshgrid(buildings.x, buildings.y)
    x = x[np.isfinite(buildings.buildings)]
    y = y[np.isfinite(buildings.buildings)]
    points = np.stack([x,y], axis=1)
    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(points)
    labels = clustering.labels_

    labeled = np.full((buildings.y.shape[0], buildings.x.shape[0]), np.nan)
    labeled[np.isfinite(buildings.buildings)] = labels

    dataset['clustered_buildings'] = xr.DataArray(labeled, dims=('y','x'),
                                                  attrs={'standard_name': "Clustered buildings",
                                                         'units': 'number of buildings',
                                                         'projection': str(CRS.from_epsg(2154)),
                                                         'plot_kwargs': {'cmap':'Spectral'}
                                                         }
                                                  )
    return dataset



def divide_into_smaller_bboxes(dataset, size=250):

    x , y = np.meshgrid(dataset.x, dataset.y)
    decim = int(size/abs(dataset.x.values[0]-dataset.x.values[1]))

    x[dataset.mask!=1] = np.nan
    y[dataset.mask!=1] = np.nan

    x = x[::decim,::decim]
    y = y[::decim,::decim]

    dx = abs(dataset.x.values[0]-dataset.x.values[decim])
    dy = abs(dataset.y.values[0]-dataset.y.values[decim])

    for row in range(x.shape[0]):
        if not np.isnan(x[row]).all():
            min_idx = np.nanargmin(x[row,:])
            max_idx = np.nanargmax(x[row,:])
            if min_idx>0:
                x[row, min_idx-1] = x[row, min_idx] - dx
                y[row, min_idx-1] = y[row, min_idx]
            if max_idx<x.shape[1]-1:
                x[row, max_idx+1] = x[row, max_idx] + dx
                y[row, max_idx+1] = y[row, max_idx]

    for col in range(y.shape[1]):
        if not np.isnan(y[:,col]).all():
            min_idx = np.nanargmin(y[:,col])
            max_idx = np.nanargmax(y[:,col])
            if max_idx>0:
                y[max_idx-1, col] = y[max_idx, col] + dy
                x[max_idx-1, col] = x[max_idx, col]
            if min_idx<y.shape[0]-1:
                y[min_idx+1, col] = y[min_idx, col] - dy
                x[min_idx+1, col] = x[min_idx, col]

    points = np.stack([x[np.isfinite(x)].flatten(),y[np.isfinite(y)].flatten()], axis=1)
    bboxes = []
    for point in points:
        xmin = point[0]-dx/2
        xmax = point[0]+dx/2
        ymin = point[1]-dy/2
        ymax = point[1]+dy/2

        bbox = Polygon([(xmin, ymin),
                        (xmax, ymin),
                        (xmax, ymax),
                        (xmin, ymax)
                        ])

        bboxes.append(bbox)

    return gpd.GeoDataFrame(geometry=bboxes, crs=dataset.DSM.projection).to_crs("EPSG:4326")



def get_buildings(dataset, gdf_to_clip=None):

    bboxes = divide_into_smaller_bboxes(dataset)
    for row in range(len(bboxes)):
        bounds = bboxes.iloc[row].geometry.bounds
        gdfs = get_bdtopo(bounds, feature="batiment", verbose=False)
        if row==0:
            gdf = gdfs["batiment"].dropna(axis=1, how='all')
        else:
            gdf = (pd.concat([gdf,gdfs["batiment"].dropna(axis=1, how='all')])
                   .drop_duplicates()
                   .reset_index(drop=True))

    if gdf_to_clip is not None:
        gdf = gdf.loc[gdf.intersects(gdf_to_clip.to_crs("epsg:2154").union_all())]
        gdf = gdf.drop_duplicates(subset=['geometry']).reset_index(drop=True)

    return gdf



def get_water_mask(dataset):

    bounds = [dataset.lon.min().values, dataset.lat.min().values,
              dataset.lon.max().values, dataset.lat.max().values]
    gdfs = get_bdtopo(bounds, feature="surface_hydrographique", verbose=False)
    gdf = gdfs["surface_hydrographique"].dropna(axis=1, how='all').drop_duplicates().reset_index(drop=True)

    x, y = np.meshgrid(dataset.x.values, dataset.y.values)
    points = np.stack([x[dataset.mask==1], y[dataset.mask==1]], axis=-1)

    is_water = np.full(dataset.mask.shape, np.nan)
    is_water[dataset.mask==1] = gdf.union_all().intersects([Point(point) for point in points])

    gdfs = get_bdtopo(bounds, feature="construction_surfacique", verbose=False)
    gdf = gdfs["construction_surfacique"].dropna(axis=1, how='all').drop_duplicates().reset_index(drop=True)
    gdf = gdf.loc[(gdf['nature'] == 'Pont') | (gdf['nature'] == 'Ecluse')].reset_index(drop=True)

    is_bridge = np.full(dataset.mask.shape, np.nan)
    is_bridge[dataset.mask == 1] = gdf.union_all().intersects([Point(point) for point in points])

    is_water[is_water==False] = np.nan
    is_water[is_bridge==True] = np.nan

    dataset["water_mask"] = xr.DataArray(is_water,
                                    dims=('y', 'x'),
                                    attrs={"standard_name": "Water pixels",
                                           "units": "no units",
                                           "plot_kwargs":{"cmap":"Blues",
                                                          "add_colorbar":False
                                                          }
                                           }
                                    )

    return dataset



def get_buildings_mask(dataset):
    gdf = get_buildings(dataset, gdf_to_clip=None)
    x, y = np.meshgrid(dataset.x.values, dataset.y.values)
    points = np.stack([x[dataset.mask == 1], y[dataset.mask == 1]], axis=-1)

    is_building = np.full(dataset.mask.shape, np.nan)
    is_building[dataset.mask == 1] = gdf.union_all().intersects([Point(point) for point in points])
    is_building[is_building == False] = np.nan

    dataset["buildings_mask"] = xr.DataArray(is_building,
                                        dims=('y', 'x'),
                                        attrs={"standard_name": "Building pixels",
                                               "units": "no units",
                                               "plot_kwargs": {"cmap": "Oranges",
                                                               "add_colorbar": False
                                                               }
                                               }
                                        )

    return dataset
import matplotlib.pyplot as plt
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import cartopy.crs as ccrs


lambert93 = ccrs.LambertConformal(
    central_longitude=3,  # Méridien central pour la France
    central_latitude=46.5,  # Latitude centrale
    false_easting=700000,  # Décalage est (en mètres)
    false_northing=6600000,  # Décalage nord (en mètres)
    standard_parallels=(44, 49),  # Parallèles standards
    globe=ccrs.Globe(semimajor_axis=6378137, semiminor_axis=6356752.314245)  # Ellipsoïde GRS80
)


def plot_dataset(dataset,attribute, ax=None, projection=ccrs.PlateCarree()):

    if ax==None:
        fig, ax = plt.subplots(subplot_kw={"projection": projection}, figsize=(20, 8))

    dataset[attribute].plot(ax=ax,
                                  transform=lambert93,
                                  **dataset[attribute].plot_kwargs
                                  )

    gl = ax.gridlines(
        draw_labels=True,  # Enable labels for the gridlines
        linewidth=1,  # Line width of the gridlines
        color='black',  # Color of the gridlines
        alpha=0.5,  # Transparency of the gridlines
        linestyle='--',  # Line style of the gridlines
    )
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER

    ax.axis('off')

    return ax
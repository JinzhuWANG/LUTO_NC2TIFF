# LUTO NC2TIFF

A standalone helper module for converting [LUTO2](https://github.com/land-use-trade-offs/luto-2.0) simulation outputs from NetCDF format into standard GeoTIFF rasters.

If you have received a LUTO output folder, use this tool to extract any spatial layer as a `.tif` file that can be opened in QGIS, ArcGIS, or any other GIS software.

## What you need

A LUTO output folder contains two things this tool depends on:

| File | Description |
| --- | --- |
| `Data_RES<N>.lz4` | The LUTO data object — holds the geospatial metadata (CRS, transform, mask) needed to reconstruct 2-D rasters |
| `out_<YYYY>/xr_<variable>_<YYYY>.nc` | NetCDF output files, one per variable per year |

## Installation

```bash
pip install xarray cf_xarray rioxarray rasterio joblib numpy
```

## Usage

Open [Get_spatial_layer_from_NC.py](Get_spatial_layer_from_NC.py) and update the three paths:

```python
import xarray as xr
import cf_xarray as cfxr
import joblib
from helpers import arr_to_xr

# 1. Load the LUTO data object (provides geospatial metadata)
data = joblib.load("path/to/Data_RES10.lz4")

# 2. Open a NetCDF output file and decode its multi-index dimension
re_2030 = cfxr.decode_compress_to_multi_index(
    xr.open_dataset("path/to/out_2030/xr_renewable_energy_2030.nc"), 'layer'
)['data'].unstack('layer')

# 3. Select the specific layer you want
#    Dimensions vary by variable — use re_2030.coords to explore available values
re_2030_solar = re_2030.sel(am='Utility Solar PV', lm='ALL', lu='ALL')

# 4. Reshape the 1-D cell array to a 2-D georeferenced raster
raster_2d = arr_to_xr(data, re_2030_solar)

# 5. Write to GeoTIFF
raster_2d.rio.to_raster(
    "path/to/output/renewable_energy_solar_2030.tif",
    dtype='float32',
    compress='LZW'
)
```

Then run:

```bash
python Get_spatial_layer_from_NC.py
```

## Available variables and units

| NetCDF file | Variable | Unit |
| --- | --- | --- |
| `xr_area_<YYYY>.nc` | Area | ha |
| `xr_water_<YYYY>.nc` | Water use | ML |
| `xr_ghg_<YYYY>.nc` | GHG emissions | tCO2e |
| `xr_profit_<YYYY>.nc` | Profit | $AUD |
| `xr_biodiversity_<YYYY>.nc` | Biodiversity | weighted area (ha) |
| `xr_renewable_energy_<YYYY>.nc` | Renewable energy | MW |
| `xr_production_<YYYY>.nc` | Productivity | t/ML |

To explore what dimension values (land use, management, etc.) are available for a given file:

```python
ds = cfxr.decode_compress_to_multi_index(xr.open_dataset("xr_renewable_energy_2030.nc"), 'layer')
print(ds['data'].unstack('layer').coords)
```

## How it works

LUTO stores spatial data as a 1-D array indexed by valid land cells. `arr_to_xr()` in [helpers.py](helpers.py):

1. Detects whether the array is full-resolution (~6.95 M cells) or resfactored
2. Places cell values back into a 2-D grid using the spatial mask from the data object
3. Sets nodata cells to `NaN`
4. Attaches the correct CRS and affine transform via `rioxarray`

The returned `xr.DataArray` is immediately ready for `.rio.to_raster()`.

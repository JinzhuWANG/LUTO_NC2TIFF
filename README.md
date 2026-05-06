# LUTO NC2TIFF

A desktop GUI for converting [LUTO2](https://github.com/land-use-trade-offs/luto-2.0) NetCDF outputs into GeoTIFF rasters.

The tool lets you:

1. choose a `.nc` file,
2. let the app automatically load the matching cached metadata from `spatial_meta\rf_<N>.lz4`,
3. inspect the available hierarchical dimensions and items such as `lu`, `lm`, and `am`,
4. select the item you want from each dimension, and
5. export the selected layer to a `.tif` file for QGIS, ArcGIS, or other GIS tools.

## What you need

A LUTO output folder plus this repository's cached metadata folder contain what the tool depends on:

| File | Description |
| --- | --- |
| `out_<YYYY>\xr_<variable>_<YYYY>.nc` | A NetCDF output file containing the spatial layer values |
| `spatial_meta\rf_<N>.lz4` | Cached lightweight spatial metadata for each supported RESFACTOR |

## Installation

Run the GUI directly:

```bash
python Get_spatial_layer_from_NC.py
```

Or on Windows, just double-click:

```text
LUTO_NC2TIFF_GUI.pyw
```

To build a zip you can send to other Windows users without asking them to install Python packages:

```text
build_portable_bundle.bat
```

On first launch, the script checks for the required Python packages and installs any missing ones automatically with `pip`.

If you prefer to install them yourself first:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python Get_spatial_layer_from_NC.py
```

For the most app-like experience on Windows, double-click `LUTO_NC2TIFF_GUI.pyw`.

To create a portable distributable:

1. Double-click `build_portable_bundle.bat`.
2. Wait for the build to finish.
3. Send `dist\LUTO_NC2TIFF_GUI.zip`.

The recipient can unzip it and run `LUTO_NC2TIFF_GUI.exe`.

In the GUI:

1. Select a NetCDF file via **Browse…** or drag-and-drop a `.nc` file onto the window.
2. The app automatically matches the NetCDF `cell` count to the cached metadata in `spatial_meta` and populates the dimension dropdowns.
3. Choose one value from each available dimension.
4. Choose the output `.tif` path via **Browse…** (a default path is suggested automatically).
5. Click **Export to GeoTIFF**.

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

## How it works

LUTO stores spatial data as a 1-D array indexed by valid land cells. `arr_to_xr()` in [helpers.py](helpers.py):

1. Detects whether the array is full-resolution (~6.95 M cells) or resfactored
2. Places cell values back into a 2-D grid using the spatial mask from the data object
3. Sets nodata cells to `NaN`
4. Attaches the correct CRS and affine transform via `rioxarray`

The GUI opens NetCDF files lazily with Dask-backed chunks, matches the `cell` count to the correct cached spatial metadata file in `spatial_meta`, exposes each hierarchy as a dropdown, and exports the selected 1-D cell layer as a georeferenced GeoTIFF. It does not depend on `luto` at runtime.

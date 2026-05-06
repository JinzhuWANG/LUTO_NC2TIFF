from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import rasterio
import rioxarray as rxr
import xarray as xr


@dataclass
class SpatialDataMeta:
    LUMASK: np.ndarray
    NLUM_MASK: np.ndarray
    NODATA: float
    GEO_META_FULLRES: dict[str, Any]
    GEO_META: dict[str, Any]
    LUMAP_2D_RESFACTORED: np.ndarray
    COORD_ROW_COL_RESFACTORED: tuple[np.ndarray, np.ndarray]


CELL_COUNT_TO_RESFACTOR = {
    6956407: 1,
    1100964: 2,
    501629: 3,
    287300: 4,
    186648: 5,
    131219: 6,
    97511: 7,
    75355: 8,
    60131: 9,
    49027: 10,
}


def build_spatial_data_meta(data: Any) -> SpatialDataMeta:
    return SpatialDataMeta(
        LUMASK=data.LUMASK,
        NLUM_MASK=data.NLUM_MASK,
        NODATA=data.NODATA,
        GEO_META_FULLRES=data.GEO_META_FULLRES,
        GEO_META=data.GEO_META,
        LUMAP_2D_RESFACTORED=data.LUMAP_2D_RESFACTORED,
        COORD_ROW_COL_RESFACTORED=(
            data.COORD_ROW_COL_RESFACTORED[0],
            data.COORD_ROW_COL_RESFACTORED[1],
        ),
    )


def data_meta_path_for(data_path: str | Path) -> Path:
    return Path(data_path).with_name("data_meta.lz4")


def create_data_meta_file(data_path: str | Path, meta_path: str | Path | None = None) -> Path:
    data_path = Path(data_path)
    meta_path = data_meta_path_for(data_path) if meta_path is None else Path(meta_path)

    data = joblib.load(data_path)
    meta = build_spatial_data_meta(data)
    joblib.dump(meta, meta_path, compress=("lz4", 3))
    return meta_path


def load_cached_spatial_data_meta(meta_dir: str | Path, ncells: int) -> SpatialDataMeta:
    if ncells not in CELL_COUNT_TO_RESFACTOR:
        raise KeyError(f"Unsupported active-cell count: {ncells}")

    meta_path = Path(meta_dir) / f"rf_{CELL_COUNT_TO_RESFACTOR[ncells]}.lz4"
    if not meta_path.is_file():
        raise FileNotFoundError(f"Cached spatial metadata not found: {meta_path}")

    data = joblib.load(meta_path)
    return SpatialDataMeta(**data) if isinstance(data, dict) else data



def arr_to_xr(data: Any, arr: np.ndarray) -> xr.DataArray:
    '''
    This function converts a 1D numpy array to an 2D xarray DataArray with `transform` and `lon/lat`.
    
    Inputs
    ------
    data: Data | SpatialDataMeta
        The Data object or lightweight metadata object that contains the metadata of the 2D array.  
    arr: np.ndarray
        The 1D array that will be converted to an xarray DataArray.
        Should be either a full-res 1D arrary (len = 6956407) or a resfactored 1D array (len = data.MASK.sum()).
        
    Returns
    -------
        The xarray DataArray that contains the 2D array.
    '''
    
    # Get the geo metadata of the array
    if arr.size == data.LUMASK.size:
        geo_meta = data.GEO_META_FULLRES
        arr_2d = np.full(data.NLUM_MASK.shape, data.NODATA).astype(np.float32) 
        np.place(arr_2d, data.NLUM_MASK, arr)
    elif arr.size == data.LUMASK.sum():
        geo_meta = data.GEO_META_FULLRES
        arr_2d = np.full(data.NLUM_MASK.shape, data.NODATA).astype(np.float32)
        np.place(arr_2d, data.NLUM_MASK, arr)
    else:
        geo_meta = data.GEO_META
        arr_2d = data.LUMAP_2D_RESFACTORED.copy().astype(np.float32)
        arr_2d[*data.COORD_ROW_COL_RESFACTORED] = arr

    # Mask the nodata values to nan
    arr_2d = np.where(arr_2d == data.NODATA, np.nan, arr_2d)   

    with rasterio.io.MemoryFile() as memfile:
        with memfile.open(**geo_meta) as dataset:
            # Write the array data to the virtual dataset
            dataset.write(arr_2d, 1)
            # Read the virtual dataset into an xarray DataArray
            da_raster = rxr.open_rasterio(memfile).squeeze(drop=True)
            # Make sure the DataArray has the correct values. The rxr.open_rasterio function will loss the values of the array
            da_raster.values = arr_2d
            # Drop all attributes
            da_raster.attrs = {}
            
    return da_raster

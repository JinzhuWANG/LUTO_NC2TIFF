import numpy as np
import rasterio
import rioxarray as rxr
import xarray as xr



def arr_to_xr(data, arr:np.ndarray) -> xr.DataArray:
    '''
    This function converts a 1D numpy array to an 2D xarray DataArray with `transform` and `lon/lat`.
    
    Inputs
    ------
    data: Data
        The Data object that contains the metadata of the 2D array.  
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

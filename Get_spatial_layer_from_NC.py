
import xarray as xr
import cf_xarray as cfxr
import joblib
from helpers import arr_to_xr



# Get data object
data = joblib.load("F:/Users/jinzhu/Documents/luto-2.0/output/2026_04_23__14_10_15_RF10_2010-2050/Data_RES10.lz4")


# Get Ag-Area for 2030
'''
Unit
Area             - ha
Productivity     - t/ML
Water use        - ML
GHG emissions    - tCO2e
Profit           - $AUD
Biodiversity     - weighted area (ha)
Renewable energy - MW
'''
re_2030 = cfxr.decode_compress_to_multi_index(
    xr.open_dataset("F:/Users/jinzhu/Documents/luto-2.0/output/2026_04_23__14_10_15_RF10_2010-2050/out_2030/xr_renewable_energy_2030.nc"), 'layer'
)['data'].unstack('layer')



# Select dry beef modified land
re_2030_dry_beef_mod = re_2030.sel(am='Utility Solar PV', lm='ALL', lu='ALL')




# 1D to 2D
re_2030_dry_beef_mod_2d = arr_to_xr(data, re_2030_dry_beef_mod)
re_2030_dry_beef_mod_2d.plot()



# To GTIFF
re_2030_dry_beef_mod_2d.rio.to_raster(
    "F:/Users/jinzhu/Documents/luto-2.0/output/2026_04_23__14_10_15_RF10_2010-2050/out_2030/renewable_energy_dry_beef_mod.tif",
    dtype='float32',
    compress='LZW'
)



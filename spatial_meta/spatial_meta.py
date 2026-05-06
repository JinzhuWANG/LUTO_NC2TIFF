"""
Standalone loader for LUTO2 spatial metadata.

Usage (import):
    from spatial_meta import SpatialMeta
    meta = SpatialMeta(186648)   # SpatialDataMeta for the RF with that many active cells

Usage (CLI):
    python spatial_meta.py 186648
"""

import os
import joblib
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class SpatialDataMeta:
    LUMASK: np.ndarray                           # 1D bool  – True = active land-use cell
    NLUM_MASK: np.ndarray                        # 2D int8  – 1 = land, 0 = ocean
    NODATA: float                                # -9999
    GEO_META_FULLRES: dict[str, Any]             # rasterio meta at full resolution
    GEO_META: dict[str, Any]                     # rasterio meta at current RESFACTOR
    LUMAP_2D_RESFACTORED: np.ndarray             # 2D int16 land-use map at RESFACTOR
    COORD_ROW_COL_RESFACTORED: tuple[np.ndarray, np.ndarray]   # (row_arr, col_arr)


def SpatialMeta(ncells: int) -> SpatialDataMeta:
    """Return SpatialDataMeta for the RESFACTOR whose active-cell count equals *ncells*.

    Parameters
    ----------
    ncells : int
        Number of active land-use cells.  Call ``SpatialMeta_index()`` to list
        all available values and their corresponding RESFACTOR.
    """
    index = {
        "6956407": 1,
        "1100964": 2,
        "501629": 3,
        "287300": 4,
        "186648": 5,
        "131219": 6,
        "97511": 7,
        "75355": 8,
        "60131": 9,
        "49027": 10
    }

    if ncells not in index:
        raise KeyError('Only support RESFACTOR between 1 and 10.')

    rf = index[ncells]
    data = joblib.load(os.path.join(_DIR, f"rf_{rf}.lz4"))
    return SpatialDataMeta(**data) if isinstance(data, dict) else data






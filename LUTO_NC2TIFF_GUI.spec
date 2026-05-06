# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules


datas = []
binaries = []
hiddenimports = []

for package_name in [
    "affine",
    "cf_xarray",
    "customtkinter",
    "dask",
    "joblib",
    "lz4",
    "netCDF4",
    "numpy",
    "rasterio",
    "rioxarray",
    "tkinterdnd2",
    "xarray",
]:
    package_datas, package_binaries, package_hiddenimports = collect_all(package_name)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

hiddenimports += ["customtkinter", "dask", "dask.base", "tkinterdnd2"]
hiddenimports += collect_submodules("customtkinter")
hiddenimports += collect_submodules("dask")
hiddenimports += collect_submodules("tkinterdnd2")

spatial_meta_dir = Path("spatial_meta")
for file_path in spatial_meta_dir.glob("*.lz4"):
    datas.append((str(file_path), "spatial_meta"))


a = Analysis(
    ["LUTO_NC2TIFF_GUI.pyw"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=True,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LUTO_NC2TIFF_GUI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="LUTO_NC2TIFF_GUI",
)

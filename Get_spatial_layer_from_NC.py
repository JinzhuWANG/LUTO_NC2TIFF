from __future__ import annotations

import importlib
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from typing import Any
from tkinter import filedialog, messagebox, ttk


REQUIRED_PACKAGES = {
    "affine": "affine",
    "cf_xarray": "cf_xarray",
    "customtkinter": "customtkinter",
    "dask": "dask",
    "joblib": "joblib",
    "lz4": "lz4",
    "netCDF4": "netCDF4",
    "numpy": "numpy",
    "rasterio": "rasterio",
    "rioxarray": "rioxarray",
    "tkinterdnd2": "tkinterdnd2",
    "xarray": "xarray",
}


def _show_startup_message(title: str, message: str, *, is_error: bool = False) -> None:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        if is_error:
            messagebox.showerror(title, message, parent=root)
        else:
            messagebox.showinfo(title, message, parent=root)
    finally:
        root.destroy()


def ensure_dependencies() -> None:
    if getattr(sys, "frozen", False):
        return

    missing_packages: list[str] = []

    for module_name, package_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing_packages.append(package_name)

    if not missing_packages:
        return

    package_list = ", ".join(sorted(set(missing_packages)))
    _show_startup_message(
        "Installing dependencies",
        "The app needs to install missing Python packages before it can start.\n\n"
        f"Missing packages: {package_list}\n\n"
        "Click OK to continue.",
    )

    install_window = tk.Tk()
    install_window.title("Starting LUTO NC2TIFF")
    install_window.resizable(False, False)
    install_window.attributes("-topmost", True)

    frame = tk.Frame(install_window, padx=16, pady=16)
    frame.grid(sticky="nsew")
    tk.Label(
        frame,
        text="Installing required packages.\nThis may take a few minutes on first launch.",
        justify="left",
    ).grid(row=0, column=0, sticky="w")
    progress = ttk.Progressbar(frame, mode="indeterminate", length=280)
    progress.grid(row=1, column=0, sticky="ew", pady=(12, 0))
    progress.start(10)
    install_window.update_idletasks()

    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", *sorted(set(missing_packages))],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "Dependency installation failed. Please run "
            f"'{sys.executable} -m pip install -r requirements.txt' manually."
        ) from exc
    finally:
        progress.stop()
        install_window.destroy()

ensure_dependencies()

import customtkinter as ctk
import cf_xarray as cfxr
import xarray as xr
from tkinterdnd2 import DND_FILES, TkinterDnD

from helpers import arr_to_xr, load_cached_spatial_data_meta


IGNORED_OUTPUT_DIMS = {"cell", "x", "y", "band"}

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

SPATIAL_META_DIRNAME = "spatial_meta"


def format_coord_value(value: Any) -> str:
    if hasattr(value, "item"):
        try:
            value = value.item()
        except ValueError:
            pass
    return str(value)


def sanitize_filename_part(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in value)
    return safe.strip("_") or "selection"


class CTkDnD(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

class NcToGtiffApp:
    def __init__(self, root: ctk.CTk) -> None:
        self.root = root
        self.root.title("LUTO NC to GeoTIFF")
        self.root.minsize(1080, 760)

        self.nc_path_var = tk.StringVar()
        self.export_path_var = tk.StringVar()
        self.status_var = tk.StringVar(
            value="Select a NetCDF file."
        )

        self.dataset: xr.Dataset | None = None
        self.decoded_array: xr.DataArray | None = None
        self.data_meta: Any = None
        self.loaded_ncells: int | None = None
        self.selector_vars: dict[str, tk.StringVar] = {}
        self.selector_value_lookup: dict[str, dict[str, Any]] = {}
        self.selector_widgets: list[Any] = []

        self._build_layout()
        self._enable_file_drop()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_section(self, parent: ctk.CTkFrame, row: int, title: str) -> ctk.CTkFrame:
        section = ctk.CTkFrame(parent)
        section.grid(row=row, column=0, sticky="nsew", pady=(0 if row == 0 else 12, 0))
        section.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            section,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))
        return section

    def _build_layout(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        main = ctk.CTkFrame(self.root, corner_radius=0)
        main.grid(row=0, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)
        main.grid_rowconfigure(3, weight=1)

        file_section = self._build_section(main, 0, "Files")
        file_frame = ctk.CTkFrame(file_section, fg_color="transparent")
        file_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        file_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(file_frame, text="NetCDF file").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=6)
        self.nc_entry = ctk.CTkEntry(file_frame, textvariable=self.nc_path_var)
        self.nc_entry.grid(row=0, column=1, sticky="ew", pady=6)
        ctk.CTkButton(file_frame, text="Browse...", width=110, command=self._browse_nc_file).grid(
            row=0, column=2, padx=(10, 10), pady=6
        )

        export_section = self._build_section(main, 1, "Export")
        export_frame = ctk.CTkFrame(export_section, fg_color="transparent")
        export_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        export_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(export_frame, text="GeoTIFF path").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=6)
        ctk.CTkEntry(export_frame, textvariable=self.export_path_var).grid(row=0, column=1, sticky="ew", pady=6)
        ctk.CTkButton(export_frame, text="Browse...", width=110, command=self._browse_export_path).grid(
            row=0, column=2, padx=(10, 10), pady=6
        )
        self.export_button = ctk.CTkButton(
            export_frame,
            text="Export to GeoTIFF",
            width=180,
            command=self._export_to_gtiff,
            state="disabled",
        )
        self.export_button.grid(row=0, column=3, sticky="w", pady=6)

        selections_section = self._build_section(main, 2, "Hierarchical selections")
        selections_section.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(
            selections_section,
            text="Each dropdown lists the available items for one dimension in the selected NetCDF layer.",
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        self.selectors_container = ctk.CTkScrollableFrame(selections_section)
        self.selectors_container.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.selectors_container.grid_columnconfigure(1, weight=1)

        summary_section = self._build_section(main, 3, "Available items summary")
        summary_section.grid_rowconfigure(1, weight=1)
        self.summary_text = ctk.CTkTextbox(summary_section, wrap="word")
        self.summary_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.summary_text.configure(state="disabled")

        status_bar = ctk.CTkLabel(
            main,
            textvariable=self.status_var,
            anchor="w",
            justify="left",
        )
        status_bar.grid(row=4, column=0, sticky="ew", padx=16, pady=(8, 12))

    def _browse_nc_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select NetCDF file",
            filetypes=[("NetCDF files", "*.nc"), ("All files", "*.*")],
        )
        if path:
            self._handle_nc_file_selected(path)

    def _enable_file_drop(self) -> None:
        for widget in (self.root, self.nc_entry):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_file_drop)

    def _on_file_drop(self, event: Any) -> str:
        try:
            dropped_paths = [Path(item) for item in self.root.tk.splitlist(event.data)]
        except tk.TclError:
            dropped_paths = [Path(str(event.data).strip().strip("{}"))]

        nc_path = next((path for path in dropped_paths if path.suffix.lower() == ".nc"), None)
        if nc_path is None:
            messagebox.showerror("Unsupported file", "Please drop a NetCDF (.nc) file.")
            return "break"

        self._handle_nc_file_selected(str(nc_path))
        return "break"

    def _handle_nc_file_selected(self, path: str) -> None:
        self._reset_loaded_nc_state()
        self.nc_path_var.set(path)
        self._suggest_export_path(force=True)
        self._load_available_selections()

    def _reset_loaded_nc_state(self) -> None:
        if self.dataset is not None:
            self.dataset.close()
            self.dataset = None

        self.decoded_array = None
        self.export_button.configure(state="disabled")
        self._rebuild_selectors()
        self._set_summary_text("")
        self.status_var.set("Loading selected NetCDF file...")

    def _browse_export_path(self) -> None:
        initial_path = self.export_path_var.get().strip()
        initial_dir = None
        initial_file = None

        if initial_path:
            initial_dir = str(Path(initial_path).parent)
            initial_file = Path(initial_path).name
        elif self.nc_path_var.get().strip():
            initial_dir = str(Path(self.nc_path_var.get().strip()).parent)

        path = filedialog.asksaveasfilename(
            title="Choose GeoTIFF output path",
            defaultextension=".tif",
            filetypes=[("GeoTIFF", "*.tif"), ("All files", "*.*")],
            initialdir=initial_dir,
            initialfile=initial_file,
        )
        if path:
            self.export_path_var.set(path)

    def _load_available_selections(self) -> None:
        nc_path = Path(self.nc_path_var.get().strip())
        if not nc_path.is_file():
            messagebox.showerror("Missing NetCDF file", "Please choose a valid NetCDF file first.")
            return

        try:
            self._set_busy(True, "Loading cached spatial metadata and NetCDF dimensions...")

            if self.dataset is not None:
                self.dataset.close()

            self.dataset = xr.open_dataset(nc_path, chunks={})
            decoded_dataset = cfxr.decode_compress_to_multi_index(self.dataset, "layer")
            if "data" not in decoded_dataset:
                raise KeyError("The selected NetCDF file does not contain a 'data' variable.")

            self.decoded_array = decoded_dataset["data"].unstack("layer")
            self._ensure_spatial_meta_loaded(self.decoded_array.sizes["cell"])
            self._rebuild_selectors()
            self._suggest_export_path(force=True)

            dimension_names = self._get_selectable_dimensions()
            if dimension_names:
                self.status_var.set(f"Loaded {len(dimension_names)} hierarchical dimensions from {nc_path.name}.")
            else:
                self.status_var.set(f"Loaded {nc_path.name}. No extra hierarchical dimensions were found.")

            self.export_button.configure(state="normal")
        except Exception as exc:
            self.export_button.configure(state="disabled")
            messagebox.showerror("Load failed", str(exc))
            self.status_var.set("Failed to load the selected files.")
        finally:
            self._set_busy(False)

    def _spatial_meta_dir(self) -> Path:
        candidates = [
            Path(__file__).resolve().parent / SPATIAL_META_DIRNAME,
            Path(sys.executable).resolve().parent / SPATIAL_META_DIRNAME,
            Path(sys.executable).resolve().parent / "_internal" / SPATIAL_META_DIRNAME,
        ]
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        raise FileNotFoundError("Could not find the spatial_meta cache directory.")

    def _ensure_spatial_meta_loaded(self, ncells: int) -> None:
        if self.data_meta is not None and self.loaded_ncells == ncells:
            return

        meta_dir = self._spatial_meta_dir()
        self.data_meta = load_cached_spatial_data_meta(meta_dir, ncells)
        self.loaded_ncells = ncells
        self.status_var.set(
            f"Using cached spatial metadata from {meta_dir} for {ncells:,} active cells."
        )

    def _rebuild_selectors(self) -> None:
        for widget in self.selector_widgets:
            widget.destroy()
        self.selector_widgets.clear()
        self.selector_vars.clear()
        self.selector_value_lookup.clear()

        summary_lines: list[str] = []

        for row_index, dim_name in enumerate(self._get_selectable_dimensions()):
            coord_values = list(self.decoded_array.coords[dim_name].values)
            display_lookup = {format_coord_value(value): value for value in coord_values}
            display_values = list(display_lookup.keys())

            var = tk.StringVar(value=display_values[0] if display_values else "")
            self.selector_vars[dim_name] = var
            self.selector_value_lookup[dim_name] = display_lookup

            label = ctk.CTkLabel(self.selectors_container, text=dim_name, anchor="w")
            label.grid(row=row_index, column=0, sticky="w", padx=(0, 12), pady=6)

            combo = ctk.CTkComboBox(
                self.selectors_container,
                variable=var,
                values=display_values,
                state="readonly",
                command=lambda _choice: self._suggest_export_path(),
            )
            combo.grid(row=row_index, column=1, sticky="ew", pady=6)

            self.selector_widgets.extend([label, combo])
            summary_lines.append(f"{dim_name}: {display_values}")

        if not summary_lines:
            summary_lines.append("No hierarchical dimensions found. This file can be exported directly.")

        for dim_name in self._get_empty_dimensions():
            summary_lines.append(f"{dim_name}: []")

        self._set_summary_text("\n".join(summary_lines))

    def _set_summary_text(self, text: str) -> None:
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", "end")
        self.summary_text.insert("1.0", text)
        self.summary_text.configure(state="disabled")

    def _get_selectable_dimensions(self) -> list[str]:
        if self.decoded_array is None:
            return []
        return [
            dim for dim in self.decoded_array.dims
            if dim not in IGNORED_OUTPUT_DIMS and self.decoded_array.sizes.get(dim, 0) > 0
        ]

    def _get_empty_dimensions(self) -> list[str]:
        if self.decoded_array is None:
            return []
        return [
            dim for dim in self.decoded_array.dims
            if dim not in IGNORED_OUTPUT_DIMS and self.decoded_array.sizes.get(dim, 0) == 0
        ]

    def _current_selection(self) -> dict[str, Any]:
        selection: dict[str, Any] = {}

        for dim_name, var in self.selector_vars.items():
            label = var.get().strip()
            if not label:
                raise ValueError(f"Please choose a value for '{dim_name}'.")
            selection[dim_name] = self.selector_value_lookup[dim_name][label]

        return selection

    def _suggest_export_path(self, force: bool = False) -> None:
        if not self.nc_path_var.get().strip():
            return

        nc_path = Path(self.nc_path_var.get().strip())
        base_parts = [nc_path.stem]

        for dim_name, var in self.selector_vars.items():
            selected_value = var.get().strip()
            if selected_value:
                base_parts.append(f"{dim_name}_{sanitize_filename_part(selected_value)}")

        file_name = "__".join(base_parts) + ".tif"
        self.export_path_var.set(str(nc_path.with_name(file_name)))

    def _export_to_gtiff(self) -> None:
        if self.decoded_array is None or self.data_meta is None:
            messagebox.showerror("Nothing loaded", "Load a NetCDF file and its available selections first.")
            return

        export_path = self.export_path_var.get().strip()
        if not export_path:
            messagebox.showerror("Missing output path", "Please choose where to save the GeoTIFF file.")
            return

        try:
            self._set_busy(True, "Exporting the selected layer to GeoTIFF...")

            selected_layer = self.decoded_array.sel(**self._current_selection()).squeeze(drop=True)
            remaining_dims = [dim for dim in selected_layer.dims if dim != "cell"]
            if remaining_dims:
                raise ValueError(
                    "The selected layer is still multi-dimensional after applying the current selections: "
                    + ", ".join(remaining_dims)
                )

            raster_2d = arr_to_xr(self.data_meta, selected_layer.values)
            Path(export_path).parent.mkdir(parents=True, exist_ok=True)
            raster_2d.rio.to_raster(export_path, dtype="float32", compress="LZW")

            self.status_var.set(f"Exported GeoTIFF to {export_path}.")
            messagebox.showinfo("Export complete", f"GeoTIFF saved to:\n{export_path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))
            self.status_var.set("Export failed.")
        finally:
            self._set_busy(False)

    def _set_busy(self, is_busy: bool, status_message: str | None = None) -> None:
        self.root.configure(cursor="watch" if is_busy else "")
        self.export_button.configure(
            state="disabled" if is_busy else ("normal" if self.decoded_array is not None else "disabled")
        )
        if status_message is not None:
            self.status_var.set(status_message)
        self.root.update_idletasks()

    def _on_close(self) -> None:
        if self.dataset is not None:
            self.dataset.close()
        self.root.destroy()


def main() -> None:
    root = CTkDnD()
    NcToGtiffApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

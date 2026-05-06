import tkinter as tk
from tkinter import messagebox


try:
    from Get_spatial_layer_from_NC import main
except Exception as exc:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        messagebox.showerror("LUTO NC2TIFF", str(exc), parent=root)
    finally:
        root.destroy()
else:
    main()

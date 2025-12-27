import os
import rasterio
import numpy as np


def convert_tif_to_geopng(vmin=0, vmax=300):
    tif_folder = os.path.join(os.getcwd(), "static", "data", "tif")
    png_folder = os.path.join(os.getcwd(), "static", "data", "rain", "png")
    os.makedirs(png_folder, exist_ok=True)
    print(f"Converting TIF files from {tif_folder} to PNG in {png_folder}")
    for tif_file in os.listdir(tif_folder):
        if not tif_file.endswith(".tif"):
            continue

        tif_path = os.path.join(tif_folder, tif_file)
        png_path = os.path.join(png_folder, tif_file.replace(".tif", ".png"))

        with rasterio.open(tif_path) as src:
            data = src.read(1).astype(np.float32)
            profile = src.profile.copy()

            # Handle nodata
            nodata = src.nodata
            if nodata is not None:
                data[data == nodata] = np.nan

            # Normalize rainfall to 0–255
            data_norm = np.clip((data - vmin) / (vmax - vmin) * 255, 0, 255)

            data_norm = np.nan_to_num(data_norm, nan=0).astype(np.uint8)

            profile.update(driver="PNG", dtype="uint8", count=1, nodata=0)

            with rasterio.open(png_path, "w", **profile) as dst:
                dst.write(data_norm, 1)
                dst.update_tags(SCALE_MIN=vmin, SCALE_MAX=vmax, UNITS="mm")

        print(f"Converted {tif_file} → PNG (Rainfall {vmin}-{vmax} mm)")


convert_tif_to_geopng()

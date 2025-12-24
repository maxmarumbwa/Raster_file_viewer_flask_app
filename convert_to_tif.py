import os
import rasterio
from PIL import Image
import numpy as np


def convert_tif_to_png():
    tif_folder = os.path.join(os.getcwd(), "data", "tif")
    png_folder = os.path.join(os.getcwd(), "data", "png")
    os.makedirs(png_folder, exist_ok=True)

    for tif_file in os.listdir(tif_folder):
        if tif_file.endswith(".tif"):
            tif_path = os.path.join(tif_folder, tif_file)
            png_file = tif_file.replace(".tif", ".png")
            png_path = os.path.join(png_folder, png_file)

            with rasterio.open(tif_path) as src:
                data = src.read(1)
                # Normalize to 0-255 for PNG
                data_norm = ((data + 1) / 2 * 255).astype(np.uint8)
                img = Image.fromarray(data_norm)
                img.save(png_path)
            print(f"Converted {tif_file} to {png_file}")


if __name__ == "__main__":
    convert_tif_to_png()

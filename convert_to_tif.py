import os
import rasterio
import numpy as np


def convert_tif_to_geopng():
    tif_folder = os.path.join(os.getcwd(), "static", "data", "tif")
    png_folder = os.path.join(os.getcwd(), "static", "data", "png")
    os.makedirs(png_folder, exist_ok=True)

    for tif_file in os.listdir(tif_folder):
        if tif_file.endswith(".tif"):
            tif_path = os.path.join(tif_folder, tif_file)
            png_file = tif_file.replace(".tif", ".png")
            png_path = os.path.join(png_folder, png_file)

            with rasterio.open(tif_path) as src:
                # Read the data and georeferencing info
                data = src.read(1)
                crs = src.crs  # Coordinate system (e.g., EPSG:4326)
                transform = src.transform  # Affine transform for pixel positioning
                profile = src.profile.copy()  # Copy source metadata

                # Normalize to 0-255 for PNG (assuming NDVI range [-1, 1])
                data_norm = ((data + 1) / 2 * 255).astype(np.uint8)

                # Update profile for PNG output with preserved CRS
                profile.update(
                    {
                        "driver": "PNG",
                        "height": src.height,
                        "width": src.width,
                        "count": 1,
                        "dtype": "uint8",
                        "nodata": None,
                        "crs": crs,  # KEEP the CRS
                        "transform": transform,  # KEEP the transform
                    }
                )

                # Write the PNG file with rasterio to embed georeferencing
                with rasterio.open(png_path, "w", **profile) as dst:
                    dst.write(data_norm, 1)  # Write normalized data to band 1
                    # Optionally add metadata tags
                    dst.update_tags(
                        TIFFTAG_SOFTWARE="rasterio/PIL conversion",
                        spatial_ref=crs.to_wkt() if crs else "",
                    )

            print(f"Converted {tif_file} to {png_file} (CRS preserved: {crs})")


if __name__ == "__main__":
    convert_tif_to_geopng()

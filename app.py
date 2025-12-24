# CORRECTED IMPORTS - Add Flask and all other necessary imports
from flask import Flask, render_template, send_file, abort, jsonify
import rasterio
from rasterio.mask import mask
import json
import os
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
import numpy as np

app = Flask(__name__)


# Your original route remains unchanged
@app.route("/")
def index():
    """Serve the main map page."""
    return render_template("index.html")


@app.route("/api/ndvi_image/<date_str>")  # e.g., /api/ndvi_image/2023-10-01
def get_clipped_ndvi(date_str):
    """
    Returns a PNG image of NDVI, clipped to Zimbabwe, for the given date.
    """
    try:
        # 1. Convert date and find the correct file
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        file_name = f"gsod_{date_obj.strftime('%Y%m%d')}.tif"

        # CORRECTED: Use proper file system path, not URL path
        # Your TIFF files should be in a folder relative to your app.py
        file_path = os.path.join(os.getcwd(), "static", "data", "tif", file_name)
        print(file_path)

        # For debugging, print the path to check
        print(f"Looking for file: {file_path}")

        if not os.path.exists(file_path):
            abort(404, description=f"No NDVI data found for {date_str}")

        # 2. Load your Zimbabwe boundaries GeoJSON
        geojson_path = os.path.join(os.getcwd(), "static", "data", "zim_admin1.geojson")
        with open(geojson_path, "r") as f:
            geojson_data = json.load(f)

        # Extract the polygon geometry
        shapes = [feature["geometry"] for feature in geojson_data["features"]]

        # 3. Open the GeoTIFF, clip it, and create an image
        with rasterio.open(file_path) as src:
            # Perform the clip
            out_image, out_transform = mask(src, shapes, crop=True, nodata=src.nodata)

            # 4. Prepare the clipped data for visualization
            ndvi_band = out_image[0].astype(float)

            # Handle no-data values
            if src.nodata is not None:
                ndvi_band[ndvi_band == src.nodata] = np.nan

            # 5. Create a matplotlib figure
            fig, ax = plt.subplots(figsize=(10, 10))
            im = ax.imshow(ndvi_band, cmap="RdYlGn", vmin=-1.0, vmax=1.0)
            ax.axis("off")

            # Save to buffer
            img_buffer = BytesIO()
            plt.savefig(
                img_buffer, format="png", bbox_inches="tight", pad_inches=0, dpi=100
            )
            plt.close(fig)
            img_buffer.seek(0)

        # 6. Send the image
        return send_file(img_buffer, mimetype="image/png")

    except Exception as e:
        # Log the error
        print(f"Error processing {date_str}: {str(e)}")
        abort(500, description=f"Server error: {str(e)}")


import glob


@app.route("/api/available_dates")
def get_available_dates():
    tif_folder = os.path.join(os.path.dirname(__file__), "static", "data", "tif")
    print(tif_folder)
    files = glob.glob(os.path.join(tif_folder, "gsod_*.tif"))
    dates = []
    for f in files:
        try:
            # Extract date from filename like 'gsod_20021021.tif'
            date_str = os.path.basename(f)[5:-4]  # get '20021021'
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            dates.append(date_obj.strftime("%Y-%m-%d"))
        except:
            continue
    return jsonify(sorted(dates))


if __name__ == "__main__":
    app.run(debug=True)

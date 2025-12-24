from flask import Flask, render_template, send_file, abort, jsonify
import rasterio
from rasterio.mask import mask
import json
import os
import glob
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
import numpy as np

# Initialize Flask application
app = Flask(__name__)


# ============================================================================
# MAIN ENDPOINT - Renders the HTML page
# ============================================================================
@app.route("/")
def index():
    """
    Main endpoint that renders the index.html template.
    This is the entry point of your web application.
    """
    return render_template("index.html")


# ============================================================================
# API ENDPOINT 1 - Get clipped NDVI image for a specific date
# ============================================================================
@app.route("/api/ndvi_image/<date_str>")
def get_clipped_ndvi(date_str):
    """
    Returns a PNG image of NDVI, clipped to Zimbabwe, for the given date.
    Format: /api/ndvi_image/2023-10-01
    """
    try:
        # 1. Convert date and find the correct file
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        file_name = f"gsod_{date_obj.strftime('%Y%m%d')}.tif"

        # Path to your TIFF files - adjust if needed
        file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "static",
            "data",
            "tif",
            file_name,
        )

        # Debug print
        print(f"Looking for TIFF file: {file_path}")

        if not os.path.exists(file_path):
            abort(404, description=f"No NDVI data found for {date_str}")

        # 2. Load Zimbabwe boundaries GeoJSON
        geojson_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "static",
            "data",
            "zim_admin1.geojson",
        )

        with open(geojson_path, "r") as f:
            geojson_data = json.load(f)

        # Extract polygon geometries
        shapes = [feature["geometry"] for feature in geojson_data["features"]]

        # 3. Open GeoTIFF, clip it, and create image
        with rasterio.open(file_path) as src:
            # Perform the clip operation
            out_image, out_transform = mask(src, shapes, crop=True, nodata=src.nodata)

            # Prepare clipped data for visualization
            ndvi_band = out_image[0].astype(float)

            # Handle no-data values
            if src.nodata is not None:
                ndvi_band[ndvi_band == src.nodata] = np.nan

            # 4. Create matplotlib visualization
            fig, ax = plt.subplots(figsize=(10, 10))
            im = ax.imshow(ndvi_band, cmap="RdYlGn", vmin=-1.0, vmax=1.0)
            ax.axis("off")

            # Save to in-memory buffer
            img_buffer = BytesIO()
            plt.savefig(
                img_buffer, format="png", bbox_inches="tight", pad_inches=0, dpi=100
            )
            plt.close(fig)
            img_buffer.seek(0)

        # 5. Send the image as PNG response
        return send_file(img_buffer, mimetype="image/png")

    except ValueError as e:
        abort(400, description=f"Invalid date format. Use YYYY-MM-DD: {str(e)}")
    except Exception as e:
        print(f"Error processing {date_str}: {str(e)}")
        abort(500, description=f"Server error: {str(e)}")


# ============================================================================
# API ENDPOINT 2 - Get list of available dates
# ============================================================================
@app.route("/api/available_dates")
def get_available_dates():
    """
    Returns a JSON list of dates for which NDVI TIFF files are available.
    This endpoint is called by the frontend to populate the date picker.
    """
    try:
        # Path to your TIFF folder
        tif_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "static", "data", "tif"
        )

        # Get all matching TIFF files
        files = glob.glob(os.path.join(tif_folder, "gsod_*.tif"))

        # Extract dates from filenames
        dates = []
        for f in files:
            try:
                # Extract date from filename like 'gsod_20021021.tif'
                base_name = os.path.basename(f)
                date_str = base_name[5:-4]  # Remove 'gsod_' and '.tif'

                # Parse and format date
                date_obj = datetime.strptime(date_str, "%Y%m%d")
                formatted_date = date_obj.strftime("%Y-%m-%d")
                dates.append(formatted_date)

            except ValueError:
                print(f"Warning: Skipping file with bad name format '{base_name}'")
                continue

        # Return sorted dates (chronological order)
        return jsonify(sorted(dates))

    except Exception as e:
        print(f"Error in get_available_dates: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Application Entry Point
# ============================================================================
if __name__ == "__main__":
    # Run the Flask application in debug mode
    app.run(debug=True, host="0.0.0.0", port=5000)

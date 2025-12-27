from flask import Flask, send_file, abort, render_template
import os
from datetime import datetime
import rasterio
import json
from flask import jsonify

app = Flask(__name__)


@app.route("/api/ndvi_png/<date_str>")
def get_png(date_str):
    """Serve pre-converted PNG file - fastest possible"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        file_name = f"gsod_{date_obj.strftime('%Y%m%d')}.png"
        file_path = os.path.join(os.getcwd(), "static", "data", "png", file_name)

        if not os.path.exists(file_path):
            abort(404)

        return send_file(file_path, mimetype="image/png")

    except:
        abort(500)


# NDVI DATA ENDPOINT - Returns image URL and geographic bounds
@app.route("/api/ndvi_data/<date_str>")
def get_ndvi_data(date_str):
    """Return image URL and its geographic bounds."""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        file_name = f"gsod_{date_obj.strftime('%Y%m%d')}.png"
        file_path = os.path.join("static", "data", "png", file_name)
        print(f"Looking for file at: {file_path}")

        if not os.path.exists(file_path):
            abort(404)

        # Read bounds from the georeferenced PNG
        with rasterio.open(file_path) as src:
            bounds = src.bounds  # (left, bottom, right, top)

        return jsonify(
            {
                "image_url": f"/api/ndvi_png/{date_str}",
                "bounds": {
                    "south": bounds.bottom,
                    "west": bounds.left,
                    "north": bounds.top,
                    "east": bounds.right,
                },
            }
        )
    except Exception as e:
        print(f"Error: {e}")
        abort(500)


# Hardcoded bounds as a Python list for Leaflet
IMAGE_BOUNDS = [
    [-35.00446428571232, 10.995535714285715],  # [south, west]
    [-7.995535714285042, 41.00446428571284],
]  # [north, east]


@app.route("/")
def index():
    """The ONE AND ONLY route - renders HTML with embedded bounds"""
    return render_template("index.html", bounds=IMAGE_BOUNDS)


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
# Additional API Endpoint - Colored NDVI Image
# ============================================================================
from PIL import Image
import numpy as np
import io


def ndvi_to_color(ndvi_value):
    """Convert NDVI value to RGB color"""
    if ndvi_value < -1:
        return (215, 48, 39)  # Red - Water/Snow
    elif ndvi_value < 0.2:
        return (252, 141, 89)  # Orange - Bare soil
    elif ndvi_value < 0.4:
        return (254, 224, 139)  # Light yellow - Sparse vegetation
    elif ndvi_value < 0.6:
        return (217, 239, 139)  # Light green - Moderate vegetation
    elif ndvi_value < 0.7:
        return (145, 207, 96)  # Green - Dense vegetation
    else:
        return (26, 152, 80)  # Dark green - Very dense vegetation


@app.route("/api/colored_ndvi/<date_str>")
def get_colored_ndvi(date_str):
    """Return NDVI image colored server-side"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        file_name = f"gsod_{date_obj.strftime('%Y%m%d')}.png"
        file_path = os.path.join(os.getcwd(), "static", "data", "png", file_name)

        if not os.path.exists(file_path):
            abort(404)

        # Open and process image
        img = Image.open(file_path).convert("L")  # Convert to grayscale
        img_array = np.array(img)

        # Convert to NDVI values (assuming 0-255 represents -1 to 1)
        ndvi_array = (img_array / 255.0) * 2 - 1

        # Create colored image
        colored = np.zeros((img_array.shape[0], img_array.shape[1], 3), dtype=np.uint8)

        for i in range(img_array.shape[0]):
            for j in range(img_array.shape[1]):
                colored[i, j] = ndvi_to_color(ndvi_array[i, j])

        # Convert back to image
        colored_img = Image.fromarray(colored, "RGB")

        # Save to bytes
        img_io = io.BytesIO()
        colored_img.save(img_io, "PNG")
        img_io.seek(0)

        return send_file(img_io, mimetype="image/png")

    except Exception as e:
        print(f"Error: {e}")
        abort(500)


if __name__ == "__main__":
    # Run the Flask application in debug mode
    app.run(debug=True, host="0.0.0.0", port=5000)

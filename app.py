from flask import Flask, send_file, abort, render_template, request
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
# Image classification API  endpoint- PNG based
# ============================================================================
from PIL import Image
import numpy as np
import io


@app.route("/api/classified_rainfall/<date_str>")
def classified_rainfall(date_str):
    """
    Rainfall classes (mm):
    0–25   Very Low
    25–75  Low
    75–150 Moderate
    150–250 High
    """
    try:
        # Expect date_str = YYYY-MM-DD
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        file_name = f"gsod_{date_obj.strftime('%Y%m%d')}.png"
        file_path = os.path.join("static", "data", "rain", "png", file_name)

        if not os.path.exists(file_path):
            abort(404)

        img = np.array(Image.open(file_path).convert("L"))
        rainfall = (img / 255.0) * 250  # mm

        out = np.zeros((*img.shape, 3), dtype=np.uint8)

        # Classified colors (vectorized)
        out[(rainfall <= 25)] = (222, 235, 247)  # Very Low
        out[(rainfall > 25) & (rainfall <= 75)] = (158, 202, 225)  # Low
        out[(rainfall > 75) & (rainfall <= 150)] = (49, 130, 189)  # Moderate
        out[(rainfall > 150)] = (8, 48, 107)  # High

        buf = io.BytesIO()
        Image.fromarray(out).save(buf, "PNG")
        buf.seek(0)

        return send_file(buf, mimetype="image/png")

    except Exception as e:
        print(e)
        abort(500)


# ============================================================================
# Image classification API  endpoint- GEOTIFF based
# ============================================================================
from PIL import Image
import numpy as np
import io


@app.route("/api/classified_rainfall_tif/<date_str>")
def classified_rainfall_tif(date_str):
    """
    Rainfall classes (mm):
    0–25   Very Low
    25–75  Low
    75–150 Moderate
    150–250 High
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        file_name = f"gsod_{date_obj.strftime('%Y%m%d')}.tif"
        file_path = os.path.join("static", "data", "tif", file_name)

        if not os.path.exists(file_path):
            abort(404)

        with rasterio.open(file_path) as src:
            data = src.read(1).astype("float32")
            nodata = src.nodata
            if nodata is not None:
                data[data == nodata] = np.nan

        out = np.zeros((*data.shape, 3), dtype=np.uint8)
        print("Data min/max:", np.nanmin(data), np.nanmax(data))
        # Classified colors (mm-based)
        out[(data <= 25)] = (222, 235, 247)  # Very Low
        out[(data > 25) & (data <= 75)] = (158, 202, 225)  # Low
        out[(data > 75) & (data <= 150)] = (49, 130, 189)  # Moderate
        out[(data > 150)] = (8, 48, 107)  # High

        buf = io.BytesIO()
        Image.fromarray(out).save(buf, "PNG")
        buf.seek(0)

        return send_file(buf, mimetype="image/png")

    except Exception as e:
        print(e)
        abort(500)


# ============================================================================
# Rainfall Metadata  API  endpoint-
# ============================================================================
#
@app.route("/api/rainfall_metadata/<date_str>")
def get_rainfall_metadata(date_str):
    """Just return the metadata for a rainfall file"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        file_name = f"gsod_{date_obj.strftime('%Y%m%d')}.png"
        file_path = os.path.join(
            os.getcwd(), "static", "data", "rain", "png", file_name
        )
        print(f"Looking for rainfall file at: {file_path}")
        if not os.path.exists(file_path):
            abort(404)

        img = Image.open(file_path)
        print(f"Image info: {img.info}")
        metadata = img.info

        # Return as JSON
        return jsonify(
            {
                "date": date_str,
                "filename": file_name,
                "actual_min": float(metadata.get("actual_min", 0)),
                "actual_max": float(metadata.get("actual_max", 250)),
                "units": metadata.get("units", "mm"),
                "original_file": metadata.get("original_file", ""),
                "crs": metadata.get("crs", ""),
            }
        )

    except Exception as e:
        print(f"Error getting rainfall metadata: {e}")
        abort(500)


###################------------ ANALYTICS API------------##################
###################------------ ANALYTICS API------------##################


# ============================================================================
# Get rainfal value at pixel level  API  endpoint-
# ============================================================================
#
@app.route("/api/rainfall_value")
def rainfall_value():
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))
    date = request.args.get("date")

    file = f"static/data/tif/gsod_{date.replace('-', '')}.tif"
    print(f"Looking for rainfall file at: {file}")
    with rasterio.open(file) as src:
        row, col = src.index(lon, lat)
        value = src.read(1)[row, col]

    return {"rainfall_mm": float(value)}


if __name__ == "__main__":
    # Run the Flask application in debug mode
    app.run(debug=True, host="0.0.0.0", port=5000)

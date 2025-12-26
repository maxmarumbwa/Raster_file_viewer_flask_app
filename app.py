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


@app.route("/")
def index():
    """Serve the main map page."""
    return render_template("index.html")


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

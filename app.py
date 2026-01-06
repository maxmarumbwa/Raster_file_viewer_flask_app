from flask import Flask, send_file, abort, render_template, request
import os
from datetime import datetime
import rasterio
import json
from flask import jsonify
import glob
import geopandas as gpd
import numpy as np
from rasterio.mask import mask


app = Flask(__name__)


@app.route("/api/ndvi_png/<date_str>")
def get_png(date_str):
    """Serve pre-converted PNG file - fastest possible"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        file_name = f"gsod_{date_obj.strftime('%Y%m%d')}.png"
        file_path = os.path.join(
            os.getcwd(), "static", "data", "rain", "png", file_name
        )
        if not os.path.exists(file_path):
            abort(404)

        return send_file(file_path, mimetype="image/png")

    except:
        abort(500)


@app.route("/api/img_bounds/<date_str>")
def get_img_bounds(date_str):
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
                "image_url": f"/api/data/rain/png/{date_str}.png",
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
from flask import jsonify, abort
from datetime import datetime
import os
import rasterio


@app.route("/api/rainfall_metadata/<date_str>")
def get_rainfall_metadata(date_str):
    """Return metadata from original GeoTIFF (no scaling)"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        file_name = f"gsod_{date_obj.strftime('%Y%m%d')}.tif"
        file_path = os.path.join(os.getcwd(), "static", "data", "tif", file_name)
        if not os.path.exists(file_path):
            abort(404)

        with rasterio.open(file_path) as src:
            band = src.read(1)

            # Mask nodata
            if src.nodata is not None:
                band = band[band != src.nodata]

            metadata = {
                "date": date_str,
                "filename": file_name,
                "actual_min": float(band.min()),
                "actual_max": float(band.max()),
                "units": "mm",
                "nodata": src.nodata,
                "dtype": str(band.dtype),
                "crs": str(src.crs),
                "transform": src.transform.to_gdal(),
                "width": src.width,
                "height": src.height,
                "bounds": list(src.bounds),
            }

        return jsonify(metadata)

    except Exception as e:
        print(f"Error getting rainfall metadata: {e}")
        abort(500)


###################------------ ANALYTICS API------------##################
###################------------ ANALYTICS API------------##################


# ============================================================================
# Get rainfal value at pixel level  API  endpoint-
# ============================================================================
# http://localhost:5000/api/rainfall_value_single?lat=-12&lon=27&date=2005-03-21
@app.route("/api/rainfall_value_single")
def rainfall_value_single():
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))
    date = request.args.get("date")

    file = f"static/data/tif/gsod_{date.replace('-', '')}.tif"
    print(f"Looking for rainfall file at: {file}")
    with rasterio.open(file) as src:
        row, col = src.index(lon, lat)
        value = src.read(1)[row, col]

    return {"rainfall_mm": float(value)}


# ============API to get val by start and end data =====================
# http://localhost:5000/api/rainfall_value_multiple?lat=-12&lon=27&start_date=2002-03-21&end_date=2003-06-01
@app.route("/api/rainfall_value_multiple")
def rainfall_value_multiple():
    import rasterio
    from datetime import datetime, timedelta
    import os

    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))
    start_date = request.args.get("start_date")  # e.g., "2001-12-01"
    end_date = request.args.get("end_date") or start_date  # default to start_date

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    values = []

    current = start_dt
    while current <= end_dt:
        date_str = current.strftime("%Y%m%d")
        file_path = os.path.join("static", "data", "cog", f"gsod_{date_str}_cog.tif")
        if os.path.exists(file_path):
            with rasterio.open(file_path) as src:
                row, col = src.index(lon, lat)
                value = src.read(1)[row, col]
                values.append(
                    {"date": current.strftime("%Y-%m-%d"), "rainfall_mm": float(value)}
                )
        # Increment to next dekad
        day = current.day
        if day == 1:
            current = current.replace(day=11)
        elif day == 11:
            current = current.replace(day=21)
        else:  # day == 21
            # move to first dekad of next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1, day=1)
            else:
                current = current.replace(month=current.month + 1, day=1)

    return values


# ============================================================================
# ============ Convert single raster to COG if not exists ============
# ============================================================================


def ensure_cog(file_name, input_dir="static/data/tif", output_dir="static/data/cog"):
    os.makedirs(output_dir, exist_ok=True)

    src_path = os.path.join(input_dir, file_name)
    cog_name = file_name.replace(".tif", "_cog.tif")
    cog_path = os.path.join(output_dir, cog_name)

    if not os.path.exists(cog_path):
        with rasterio.open(src_path) as src:
            profile = src.profile.copy()
            profile.update(
                driver="GTiff",
                tiled=True,
                blockxsize=512,
                blockysize=512,
                compress="deflate",
                interleave="band",
            )
            rio_copy(src, cog_path, **profile, copy_src_overviews=True)
            print(f"COG created: {cog_path}")

    return cog_path


# ============ API to serve COG ============
@app.route("/api/rainfall_cog/<date_str>")
def rainfall_cog(date_str):
    # Expect date format YYYY-MM-DD
    file_name = f"gsod_{date_str.replace('-', '')}.tif"
    cog_path = ensure_cog(file_name)

    if not os.path.exists(cog_path):
        abort(404)

    return send_file(cog_path, mimetype="image/tiff", as_attachment=False)


# ============================================================================
# Rainfall polygon statistics API endpoint
# ============================================================================
# http://localhost:5000/api/rainfall_polygon?date=2002-03-21&adm1_name=Harare
@app.route("/api/rainfall_polygon")
def rainfall_polygon():
    try:
        date_str = request.args.get("date")
        adm1_name = request.args.get("adm1_name")

        if not date_str or not adm1_name:
            abort(400)

        # Build raster path
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        raster_path = os.path.join(
            "static", "data", "cog", f"gsod_{date_obj.strftime('%Y%m%d')}_cog.tif"
        )

        if not os.path.exists(raster_path):
            abort(404)

        # Load admin boundaries
        gdf = gpd.read_file("static/data/zim_admin1.geojson")

        # Filter polygon
        poly = gdf[gdf["ADM1_EN"] == adm1_name]

        if poly.empty:
            abort(404)

        with rasterio.open(raster_path) as src:
            # Reproject polygon if needed
            if poly.crs != src.crs:
                poly = poly.to_crs(src.crs)

            geom = [poly.geometry.iloc[0]]

            # Mask raster by polygon
            data, _ = mask(src, geom, crop=True)
            band = data[0]

            # Remove nodata
            if src.nodata is not None:
                band = band[band != src.nodata]

            band = band[~np.isnan(band)]

            if band.size == 0:
                abort(404)

            stats = {
                "date": date_str,
                "adm1_name": adm1_name,
                "mean_mm": float(band.mean()),
                "min_mm": float(band.min()),
                "max_mm": float(band.max()),
                "std_mm": float(band.std()),
                "pixel_count": int(band.size),
            }

        return jsonify(stats)

    except Exception as e:
        print("Polygon stats error:", e)
        abort(500)


# ============================================================================
# Rainfall polygon statistics API endpoint start and end date
# ============================================================================
# http://localhost:5000/api/rainfall_polygon_range?start_date=2002-03-01&end_date=2002-03-21&adm1_name=Matabeleland North
from datetime import datetime, timedelta


@app.route("/api/rainfall_polygon_range")
def rainfall_polygon_range():
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        adm1_name = request.args.get("adm1_name")

        if not start_date or not end_date or not adm1_name:
            abort(400, "start_date, end_date and adm1_name are required")

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        if start_dt > end_dt:
            abort(400, "start_date must be before end_date")

        # Load admin boundaries
        gdf = gpd.read_file("static/data/zim_admin1.geojson")
        poly = gdf[gdf["ADM1_EN"] == adm1_name]

        if poly.empty:
            abort(404, "Admin area not found")

        daily_stats = []
        all_values = []

        current_dt = start_dt
        while current_dt <= end_dt:
            raster_path = os.path.join(
                "static", "data", "cog", f"gsod_{current_dt.strftime('%Y%m%d')}_cog.tif"
            )

            if not os.path.exists(raster_path):
                current_dt += timedelta(days=1)
                continue

            with rasterio.open(raster_path) as src:
                if poly.crs != src.crs:
                    poly_proj = poly.to_crs(src.crs)
                else:
                    poly_proj = poly

                geom = [poly_proj.geometry.iloc[0]]

                data, _ = mask(src, geom, crop=True)
                band = data[0]

                if src.nodata is not None:
                    band = band[band != src.nodata]

                band = band[~np.isnan(band)]

                if band.size > 0:
                    daily_stats.append(
                        {
                            "date": current_dt.strftime("%Y-%m-%d"),
                            "mean_mm": float(band.mean()),
                            "min_mm": float(band.min()),
                            "max_mm": float(band.max()),
                            "std_mm": float(band.std()),
                            "pixel_count": int(band.size),
                        }
                    )

                    all_values.append(band)

            current_dt += timedelta(days=1)

        if not all_values:
            abort(404, "No valid raster data found for date range")

        all_values = np.concatenate(all_values)

        summary_stats = {
            "mean_mm": float(all_values.mean()),
            "min_mm": float(all_values.min()),
            "max_mm": float(all_values.max()),
            "std_mm": float(all_values.std()),
            "pixel_count": int(all_values.size),
        }

        return jsonify(
            {
                "adm1_name": adm1_name,
                "start_date": start_date,
                "end_date": end_date,
                "summary": summary_stats,
                "daily": daily_stats,
            }
        )

    except Exception as e:
        print("Polygon stats error:", e)
        abort(500)


# ======================================================================
# Simple rainfall total between start and end date
# ======================================================================
# /api/rainfall_total?start_date=2001-01-01&end_date=2001-12-31
@app.route("/api/rainfall_total")
def rainfall_total():
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        if not start_date or not end_date:
            abort(400, "start_date and end_date are required")

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        if start_dt > end_dt:
            abort(400, "start_date must be before end_date")

        all_values = []

        current = start_dt
        while current <= end_dt:
            raster_path = os.path.join(
                "static", "data", "cog", f"gsod_{current.strftime('%Y%m%d')}_cog.tif"
            )

            if not os.path.exists(raster_path):
                current += timedelta(days=1)
                continue

            with rasterio.open(raster_path) as src:
                band = src.read(1).astype("float32")

                if src.nodata is not None:
                    band[band == src.nodata] = np.nan

                band = band[~np.isnan(band)]

                if band.size > 0:
                    all_values.append(band)

            current += timedelta(days=1)

        if not all_values:
            abort(404, "No rainfall data found in given period")

        values = np.concatenate(all_values)

        return jsonify(
            {
                "start_date": start_date,
                "end_date": end_date,
                "mean_rainfall_mm": float(values.sum()),
            }
        )

    except Exception as e:
        print("Rainfall total error:", e)
        abort(500)


# ======================================================================
# Areal rainfall total per province (mean → sum)
# ======================================================================
# /api/rainfall_areal_total_by_province?start_date=2001-01-01&end_date=2001-12-31


@app.route("/api/rainfall_areal_total_by_province")
def rainfall_areal_total_by_province():
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        if not start_date or not end_date:
            abort(400, "start_date and end_date are required")

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        if start_dt > end_dt:
            abort(400, "start_date must be before end_date")

        # Load provinces
        gdf = gpd.read_file("static/data/zim_admin1.geojson")

        results = []

        for _, row in gdf.iterrows():
            province = row["ADM1_EN"]
            geom = [row.geometry]

            daily_means = []

            current = start_dt
            while current <= end_dt:
                raster_path = os.path.join(
                    "static",
                    "data",
                    "cog",
                    f"gsod_{current.strftime('%Y%m%d')}_cog.tif",
                )

                if not os.path.exists(raster_path):
                    current += timedelta(days=1)
                    continue

                with rasterio.open(raster_path) as src:
                    # Reproject geometry if needed
                    geom_proj = geom
                    if gdf.crs != src.crs:
                        geom_proj = [
                            gpd.GeoSeries(geom, crs=gdf.crs).to_crs(src.crs).iloc[0]
                        ]

                    data, _ = mask(src, geom_proj, crop=True)
                    band = data[0].astype("float32")

                    if src.nodata is not None:
                        band[band == src.nodata] = np.nan

                    band = band[~np.isnan(band)]

                    if band.size > 0:
                        daily_means.append(float(band.mean()))

                current += timedelta(days=1)

            if daily_means:
                results.append(
                    {
                        "province": province,
                        "areal_rainfall_mm": float(np.sum(daily_means)),
                        "days_used": len(daily_means),
                        "mean_daily_mm": float(np.mean(daily_means)),
                    }
                )

        return jsonify(
            {
                "start_date": start_date,
                "end_date": end_date,
                "method": "sum of daily polygon means",
                "unit": "mm",
                "results": results,
            }
        )

    except Exception as e:
        print("Areal rainfall error:", e)
        abort(500)


# ========================================================================
# API get event/ current rainfall data and lta
# ========================================================================
# http://localhost:5000/api/event_vs_lta_range?start_date=2002-05-01&end_date=2002-06-01&adm1_name=Matabeleland%20North&


@app.route("/api/event_vs_lta_range")
def event_vs_lta_range():
    from rasterio.mask import mask
    import numpy as np

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    adm1_name = request.args.get("adm1_name")

    if not start_date or not end_date or not adm1_name:
        abort(400)

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    gdf = gpd.read_file("static/data/zim_admin1.geojson")
    poly = gdf[gdf["ADM1_EN"] == adm1_name]

    if poly.empty:
        abort(404)

    results = []

    # 🔹 START AT FIRST MONTH
    current = start_dt.replace(day=1)

    while current <= end_dt:

        for day in (1, 11, 21):
            try:
                dekad_date = current.replace(day=day)
            except ValueError:
                continue

            if not (start_dt <= dekad_date <= end_dt):
                continue

            mmdd = dekad_date.strftime("%m%d")

            event_raster = (
                f"static/data/cog/gsod_{dekad_date.strftime('%Y%m%d')}_cog.tif"
            )
            lta_raster = f"static/data/derived/lta/gsod_{mmdd}_lta.tif"

            if not os.path.exists(event_raster) or not os.path.exists(lta_raster):
                continue

            # --- Event rainfall ---
            with rasterio.open(event_raster) as src:
                poly_p = poly.to_crs(src.crs)
                data, _ = mask(src, poly_p.geometry, crop=True)
                band = data[0]
                band = band[~np.isnan(band)]

                if band.size == 0:
                    continue

                event_mean = float(band.mean())

            # --- Baseline (LTA) ---
            with rasterio.open(lta_raster) as src:
                poly_p = poly.to_crs(src.crs)
                data, _ = mask(src, poly_p.geometry, crop=True)
                band = data[0]
                band = band[~np.isnan(band)]

                if band.size == 0:
                    continue

                lta_mean = float(band.mean())

            results.append(
                {
                    "date": dekad_date.strftime("%Y-%m-%d"),
                    "dekad": mmdd,
                    "event_mm": round(event_mean, 2),
                    "baseline_mm": round(lta_mean, 2),
                }
            )

        # 🔹 MOVE TO NEXT MONTH
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    return jsonify(
        {
            "adm1_name": adm1_name,
            "start_date": start_date,
            "end_date": end_date,
            "data": results,
        }
    )


if __name__ == "__main__":
    # Run the Flask application in debug mode
    app.run(debug=True, host="0.0.0.0", port=5000)

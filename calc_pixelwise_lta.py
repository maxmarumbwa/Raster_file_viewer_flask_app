import os
import rasterio
import numpy as np
from rasterio.enums import Resampling

# ---------------- CONFIG ----------------
EVENT_DIR = "static/data/cog"
LTA_DIR = "static/data/derived/lta"
OUT_DIR = "static/data/derived/anom"

os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------
# LOOP THROUGH ALL EVENT RASTERS
# ---------------------------------------
for fname in sorted(os.listdir(EVENT_DIR)):

    # Expecting: gsod_YYYYMMDD_cog.tif
    if not fname.startswith("gsod_") or not fname.endswith("_cog.tif"):
        continue

    date_str = fname.replace("gsod_", "").replace("_cog.tif", "")
    year = date_str[:4]
    month = date_str[4:6]
    dekad = date_str[6:8]  # 01, 11, or 21

    event_path = os.path.join(EVENT_DIR, fname)
    lta_path = os.path.join(LTA_DIR, f"gsod_{month}{dekad}_lta.tif")
    out_path = os.path.join(OUT_DIR, f"gsod_{date_str}_anom.tif")

    if not os.path.exists(lta_path):
        print(f"⚠ Missing LTA for {month}{dekad}, skipping")
        continue

    print(f"Processing {date_str}")

    # -----------------------------------
    # READ RASTERS
    # -----------------------------------
    with rasterio.open(event_path) as ev_src, rasterio.open(lta_path) as lta_src:

        event = ev_src.read(1).astype("float32")

        lta = lta_src.read(
            1, out_shape=event.shape, resampling=Resampling.nearest
        ).astype("float32")

        nodata = ev_src.nodata
        if nodata is None:
            nodata = -9999

        # -----------------------------------
        # MASKING
        # -----------------------------------
        mask = (~np.isnan(event)) & (~np.isnan(lta)) & (lta > 0)

        anomaly_pct = np.full(event.shape, nodata, dtype="float32")

        anomaly_pct[mask] = ((event[mask] - lta[mask]) / lta[mask]) * 100

        # -----------------------------------
        # WRITE OUTPUT
        # -----------------------------------
        profile = ev_src.profile
        profile.update(dtype="float32", nodata=nodata, compress="deflate")

        with rasterio.open(out_path, "w", **profile) as dst:
            dst.write(anomaly_pct, 1)

print("✅ All dekadal percentage anomalies computed")

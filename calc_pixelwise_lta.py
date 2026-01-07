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
# INPUTS (dekad is EXPLICIT)
# ---------------------------------------
year = "2001"
month = "01"  # 01–12
dekad = "01"  # 01, 11, or 21

# ---------------------------------------
# FILE PATHS (MATCH YOUR NAMING)
# ---------------------------------------
event_path = os.path.join(EVENT_DIR, f"gsod_{year}{month}{dekad}_cog.tif")

lta_path = os.path.join(LTA_DIR, f"gsod_{month}{dekad}_lta.tif")

out_path = os.path.join(OUT_DIR, f"gsod_{year}{month}{dekad}_anom.tif")

print("Event:", event_path)
print("LTA:", lta_path)
print("Output:", out_path)

# ---------------------------------------
# CHECK FILES
# ---------------------------------------
if not os.path.exists(event_path):
    raise FileNotFoundError(f"Missing event raster: {event_path}")

if not os.path.exists(lta_path):
    raise FileNotFoundError(f"Missing LTA raster: {lta_path}")

# ---------------------------------------
# READ + COMPUTE ANOMALY
# ---------------------------------------
with rasterio.open(event_path) as ev_src, rasterio.open(lta_path) as lta_src:

    event = ev_src.read(1).astype("float32")
    lta = lta_src.read(1, out_shape=event.shape, resampling=Resampling.nearest).astype(
        "float32"
    )

    nodata = ev_src.nodata

    # Mask nodata
    mask = np.ones(event.shape, dtype=bool)
    if nodata is not None:
        mask &= event != nodata
        mask &= lta != nodata

    anomaly = np.full(event.shape, nodata, dtype="float32")
    anomaly[mask] = event[mask] - lta[mask]  # ✅ ABSOLUTE ANOMALY

    profile = ev_src.profile
    profile.update(dtype="float32", nodata=nodata, compress="deflate")

# ---------------------------------------
# WRITE OUTPUT
# ---------------------------------------
with rasterio.open(out_path, "w", **profile) as dst:
    dst.write(anomaly, 1)

print("✅ Dekadal anomaly written:", out_path)

import os
import rasterio
import numpy as np
from collections import defaultdict

# ---------------- CONFIG ----------------
DATA_DIR = "static/data/cog"
OUT_DIR = "static/data/lta"
START_YEAR = 2001
END_YEAR = 2005

os.makedirs(OUT_DIR, exist_ok=True)

DEKAD_DAYS = [1, 11, 21]

# ---------------------------------------
# Group rasters by MMDD (0301, 0311, 0321)
# ---------------------------------------
groups = defaultdict(list)

for year in range(START_YEAR, END_YEAR + 1):
    for month in range(1, 13):
        for day in DEKAD_DAYS:
            mmdd = f"{month:02d}{day:02d}"
            fname = f"gsod_{year}{mmdd}_cog.tif"
            path = os.path.join(DATA_DIR, fname)
            if os.path.exists(path):
                groups[mmdd].append(path)

print(f"Found {len(groups)} dekadal groups")

# ---------------------------------------
# Compute LTA per MMDD
# ---------------------------------------
for mmdd, files in groups.items():
    print(f"Computing LTA for {mmdd} ({len(files)} years)")

    stack = []

    with rasterio.open(files[0]) as ref:
        meta = ref.meta.copy()
        nodata = ref.nodata

    for f in files:
        with rasterio.open(f) as src:
            arr = src.read(1).astype("float32")
            if nodata is not None:
                arr[arr == nodata] = np.nan
            stack.append(arr)

    lta = np.nanmean(np.stack(stack), axis=0)

    # ---------------- Save LTA raster ----------------
    meta.update(dtype="float32", nodata=np.nan)

    out_raster = os.path.join(OUT_DIR, f"gsod_{mmdd}_lta.tif")

    with rasterio.open(out_raster, "w", **meta) as dst:
        dst.write(lta, 1)

print("✅ Dekadal LTA computed for 01, 11 and 21")

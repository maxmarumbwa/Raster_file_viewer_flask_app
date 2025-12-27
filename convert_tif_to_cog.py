import os
import rasterio
from rasterio.enums import Resampling
from rasterio.shutil import copy as rio_copy


def convert_to_cog(
    input_dir="static/data/tif", output_dir="static/data/cog", compress="deflate"
):
    os.makedirs(output_dir, exist_ok=True)

    for fname in os.listdir(input_dir):
        if not fname.endswith(".tif"):
            continue

        src_path = os.path.join(input_dir, fname)
        cog_path = os.path.join(output_dir, fname.replace(".tif", "_cog.tif"))

        with rasterio.open(src_path) as src:
            profile = src.profile.copy()

            profile.update(
                driver="GTiff",
                tiled=True,
                blockxsize=512,
                blockysize=512,
                compress=compress,
                interleave="band",
            )

            rio_copy(src, cog_path, **profile, copy_src_overviews=True)

        print(f"COG created: {cog_path}")


if __name__ == "__main__":
    convert_to_cog()

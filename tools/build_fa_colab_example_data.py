"""Build the small real-data bundle used by the Colab FA90 example.

The source volumes live in /data/garbage and are intentionally not part of the
repository. This script extracts one representative slice and stores the image
geometry needed to reproduce the production physical-space B-spline resampling.
"""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import SimpleITK as sitk

from pyable_eros_montin import imaginable as ima


SOURCE_ROOT = Path("/data/garbage/FA-test")
SNR_PATH = SOURCE_ROOT / "output_product_coil_b1/data/SNR.nii.gz"
FA_PATH = SOURCE_ROOT / "fa_maps/fa_product_coil.nii.gz"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data/fa90_example_slice.pkl"
SLICE_INDEX = 8


def geometry_for_slice(path: Path, slice_index: int) -> dict:
    image = sitk.ReadImage(str(path))
    origin = image.TransformIndexToPhysicalPoint((0, 0, slice_index))
    return {
        "origin": tuple(float(value) for value in origin),
        "spacing": tuple(float(value) for value in image.GetSpacing()),
        "direction": tuple(float(value) for value in image.GetDirection()),
    }


def main() -> None:
    for path in (SNR_PATH, FA_PATH):
        if not path.is_file():
            raise FileNotFoundError(f"Required validation volume is missing: {path}")

    snr_volume = np.asarray(ima.Imaginable(str(SNR_PATH)).getImageAsNumpy())
    fa_volume = np.asarray(ima.Imaginable(str(FA_PATH)).getImageAsNumpy())
    if SLICE_INDEX >= snr_volume.shape[2] or SLICE_INDEX >= fa_volume.shape[2]:
        raise IndexError(f"Slice {SLICE_INDEX} is outside one of the source volumes")

    bundle = {
        "format_version": 1,
        "description": (
            "Product-coil validation slice for the mroptimum B-spline FA90 example"
        ),
        "source_dataset": "FA-test product coil",
        "slice_index": SLICE_INDEX,
        "snr": snr_volume[:, :, SLICE_INDEX : SLICE_INDEX + 1].astype(
            np.complex64, copy=False
        ),
        "snr_geometry": geometry_for_slice(SNR_PATH, SLICE_INDEX),
        "fa_degrees": fa_volume[:, :, SLICE_INDEX : SLICE_INDEX + 1].astype(
            np.float32, copy=False
        ),
        "fa_geometry": geometry_for_slice(FA_PATH, SLICE_INDEX),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("wb") as stream:
        pickle.dump(bundle, stream, protocol=pickle.HIGHEST_PROTOCOL)
    print(
        f"Wrote {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size} bytes): "
        f"SNR {bundle['snr'].shape}, FA {bundle['fa_degrees'].shape}"
    )


if __name__ == "__main__":
    main()

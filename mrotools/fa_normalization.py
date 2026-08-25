"""
FA (Flip Angle) Normalization for MR Optimum SNR Maps.

Formula:
    SNR_normalized = SNR / sin(FA)

where FA is provided in degrees by the user.

Design decisions:
- FA map is resampled onto the SNR grid with cubic B-spline interpolation,
  then clamped to [0, 180] to suppress ringing overshoot.
- Near-zero sin(FA) voxels (BSpline fringe artefacts at the FA map boundary)
  are healed via a 3x3(x3) median filter: each masked voxel is replaced by the
  median of its immediate neighbours.  Voxels that are still near-zero after
  inpainting (deep background, no valid neighbours) are set to NaN and
  subsequently zeroed by snr.py's existing cleanup step.
- Resampling uses pyable's resampleOnTargetImage; geometry compatibility is
  checked first with isImaginableInTheSameSpace.
- No Siemens-specific scaling, no T1 correction, no TR correction.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional

from pyable_eros_montin import imaginable as ima


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EPSILON = 0.02          # |sin(FA)| below this is considered near-zero (FA < ~1.1°)
FILL_WINDOW = 3         # median-filter window size (voxels) for inpainting near-zero voxels
FA_CORRECTION_METHOD = "snr_over_sin_fa"


# ---------------------------------------------------------------------------
# Data class for the normalization result
# ---------------------------------------------------------------------------
@dataclass
class FANormalizationResult:
    """Holds the corrected SNR array and provenance metadata."""

    snr_fa_corrected: np.ndarray
    provenance: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_fa_map(path: str) -> ima.Imaginable:
    """Load a FA map from disk into an Imaginable object.

    Args:
        path: Path to a NIfTI, MHA, or any SimpleITK-supported image.

    Returns:
        An Imaginable wrapping the FA map.

    Raises:
        FileNotFoundError: if the file does not exist.
        RuntimeError: if the file cannot be read.
    """
    import os
    if not os.path.exists(path):
        raise FileNotFoundError(f"FA map not found: {path}")
    try:
        fa_img = ima.Imaginable(path)
    except Exception as e:
        raise RuntimeError(f"Cannot read FA map '{path}': {e}") from e
    return fa_img


def validate_and_resample_fa(
    fa_img: ima.Imaginable,
    snr_img: ima.Imaginable,
) -> ima.Imaginable:
    """Check that FA map geometry is compatible with the SNR map.

    If the geometries match, returns fa_img unchanged.
    If they differ but resampling is safe, resamples FA map onto SNR geometry.
    If geometries are irrecoverably incompatible (e.g. very different orientations),
    raises a ValueError with an actionable message.

    Args:
        fa_img:  Imaginable holding the FA map.
        snr_img: Imaginable holding the reconstructed SNR map (reference geometry).

    Returns:
        FA Imaginable in SNR geometry (resampled if necessary).

    Raises:
        ValueError: if the images cannot be safely brought into the same space.
    """
    try:
        same_space = snr_img.isImaginableInTheSameSpace(fa_img)
    except Exception:
        same_space = False

    if same_space:
        return fa_img

    # Attempt resampling with cubic B-spline interpolation.
    # B-spline gives smoother FA values at the SNR grid resolution than
    # linear interpolation, reducing artefacts at the FA map boundary.
    # Clamp to [0, 180] after resampling to suppress BSpline ringing overshoot.
    try:
        import SimpleITK as sitk
        import numpy as np
        fa_resampled = fa_img.resampleOnTargetImage(
            snr_img,
            interpolator=sitk.sitkBSplineResampler,  # cubic B-spline (order 3)
            default_value=0,
        )
        arr = fa_resampled.getImageAsNumpy()
        arr = np.clip(arr, 0.0, 180.0)
        fa_resampled.setImageFromNumpy(arr)
        return fa_resampled
    except Exception as e:
        fa_size = fa_img.getImageSize()
        snr_size = snr_img.getImageSize()
        fa_sp = fa_img.getImageSpacing()
        snr_sp = snr_img.getImageSpacing()
        raise ValueError(
            f"FA map geometry is incompatible with SNR map and could not be "
            f"resampled automatically.\n"
            f"  FA  size={fa_size}, spacing={fa_sp}\n"
            f"  SNR size={snr_size}, spacing={snr_sp}\n"
            f"Please provide a FA map that is already registered and aligned "
            f"to the reconstructed image. Original error: {e}"
        ) from e


def apply_fa_normalization(
    snr_array: np.ndarray,
    fa_array: np.ndarray,
) -> FANormalizationResult:
    """Apply FA normalization: SNR_corrected = SNR / sin(FA_degrees).

    Args:
        snr_array: SNR map as a numpy array (any shape / dtype).
        fa_array:  FA map in **degrees** as a numpy array (same shape as snr_array
                   after resampling, or broadcastable to it).

    Returns:
        FANormalizationResult with corrected map and provenance metadata.
    """
    from scipy.ndimage import median_filter

    fa_array = fa_array.astype(np.float64)
    fa_rad = np.deg2rad(fa_array)
    sin_fa = np.sin(fa_rad)

    # --- Inpaint near-zero sin(FA) voxels via median filter ---
    # BSpline resampling creates fringe voxels at the FA map boundary with
    # FA ≈ 0–1°.  Instead of masking them to NaN immediately, we replace each
    # such voxel with the median of its FILL_WINDOW neighbourhood.  Voxels
    # adjacent to real tissue are healed; isolated deep-background voxels
    # whose neighbourhood median is also near-zero are then set to NaN and
    # subsequently zeroed by snr.py's cleanup step.
    near_zero_mask = np.abs(sin_fa) < EPSILON
    n_near_zero = int(np.sum(near_zero_mask))

    if n_near_zero > 0:
        sin_fa_filled = median_filter(sin_fa, size=FILL_WINDOW, mode='nearest')
        sin_fa[near_zero_mask] = sin_fa_filled[near_zero_mask]
        # Second pass: voxels still near-zero after inpainting → NaN
        still_zero = near_zero_mask & (np.abs(sin_fa) < EPSILON)
        n_still_zero = int(np.sum(still_zero))
        sin_fa[still_zero] = np.nan
    else:
        n_still_zero = 0

    # Preserve complex dtype if input is complex, otherwise use float64
    if np.iscomplexobj(snr_array):
        snr_corrected = snr_array.astype(np.complex128) / sin_fa
    else:
        snr_corrected = snr_array.astype(np.float64) / sin_fa

    provenance = {
        "faCorrectionApplied": True,
        "faUnits": "degrees",
        "faCorrectionMethod": FA_CORRECTION_METHOD,
        "epsilonThreshold": EPSILON,
        "fillWindow": FILL_WINDOW,
        "nNearZeroVoxelsDetected": n_near_zero,
        "nNearZeroVoxelsInpainted": n_near_zero - n_still_zero,
        "nNearZeroVoxelsMasked": n_still_zero,
        "faMin": float(np.nanmin(fa_array)),
        "faMax": float(np.nanmax(fa_array)),
    }

    out_dtype = np.complex64 if np.iscomplexobj(snr_corrected) else np.float32
    return FANormalizationResult(
        snr_fa_corrected=snr_corrected.astype(out_dtype),
        provenance=provenance,
    )


def normalize_snr_with_fa(
    snr_array: np.ndarray,
    snr_img: ima.Imaginable,
    fa_path: str,
) -> FANormalizationResult:
    """End-to-end convenience function: load, validate, resample, and apply FA normalization.

    Args:
        snr_array: SNR map as numpy array (H, W[, D, ...]).
        snr_img:   Imaginable wrapping the SNR map (for geometry reference).
        fa_path:   Path to the FA map file (degrees, user-supplied).

    Returns:
        FANormalizationResult with corrected map and provenance.

    Raises:
        FileNotFoundError: FA map file missing.
        RuntimeError:      FA map unreadable.
        ValueError:        Geometry incompatible and cannot be resampled.
    """
    fa_img = load_fa_map(fa_path)
    fa_img = validate_and_resample_fa(fa_img, snr_img)
    fa_array = fa_img.getImageAsNumpy()
    return apply_fa_normalization(snr_array, fa_array)

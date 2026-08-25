"""
Unit tests for FA normalization — mrotools.fa_normalization.

Run with:
    conda run -n mro python -m pytest tests/test_fa_normalization.py -v
"""

import math
import os
import tempfile

import numpy as np
import pytest

try:
    from mrotools.fa_normalization import (
        apply_fa_normalization,
        load_fa_map,
        validate_and_resample_fa,
        normalize_snr_with_fa,
        EPSILON,
    )
    from pyable_eros_montin import imaginable as ima
except ImportError:
    # Allow running from repo root without install
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from mrotools.fa_normalization import (
        apply_fa_normalization,
        load_fa_map,
        validate_and_resample_fa,
        normalize_snr_with_fa,
        EPSILON,
    )
    from pyable_eros_montin import imaginable as ima


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_nifti(array: np.ndarray, path: str, spacing=(2.0, 2.0, 2.0)):
    """Save a numpy array as a NIfTI file via pyable."""
    img = ima.numpyToImaginable(array.astype(np.float32))
    img.setImageSpacing(list(spacing))
    img.writeImageAs(path)


# ---------------------------------------------------------------------------
# Test 1 — FA = 90° : SNR unchanged
# ---------------------------------------------------------------------------
class TestFA90:
    def test_snr_unchanged(self):
        snr = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32)
        fa = np.full_like(snr, 90.0)
        result = apply_fa_normalization(snr, fa)
        # sin(90°) = 1 → corrected == original
        np.testing.assert_allclose(result.snr_fa_corrected, snr, rtol=1e-5)

    def test_complex_snr_preserved(self):
        # SNR may be complex; normalization preserves the complex value (abs used only for display)
        snr = np.array([3.0 + 0j, 4.0 + 0j], dtype=np.complex64)
        fa = np.array([90.0, 90.0], dtype=np.float32)
        result = apply_fa_normalization(snr, fa)
        # sin(90°)=1 → corrected == original complex values
        np.testing.assert_allclose(np.abs(result.snr_fa_corrected), [3.0, 4.0], rtol=1e-5)

    def test_provenance_keys(self):
        snr = np.ones((4, 4), dtype=np.float32)
        fa = np.full_like(snr, 90.0)
        result = apply_fa_normalization(snr, fa)
        assert result.provenance["faCorrectionApplied"] is True
        assert result.provenance["faUnits"] == "degrees"
        assert result.provenance["faCorrectionMethod"] == "snr_over_sin_fa"


# ---------------------------------------------------------------------------
# Test 2 — FA = 30° : SNR_corrected = SNR / 0.5 = 2 * SNR
# ---------------------------------------------------------------------------
class TestFA30:
    def test_snr_doubled(self):
        snr = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32)
        fa = np.full_like(snr, 30.0)
        result = apply_fa_normalization(snr, fa)
        expected = snr / math.sin(math.radians(30))  # sin(30°) = 0.5 → ×2
        np.testing.assert_allclose(result.snr_fa_corrected, expected, rtol=1e-5)


# ---------------------------------------------------------------------------
# Test 3 — Near-zero FA : safe NaN handling
# ---------------------------------------------------------------------------
class TestNearZeroFA:
    def test_near_zero_returns_nan(self):
        snr = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        fa = np.array([0.0, 0.0, 90.0], dtype=np.float32)  # first two near-zero
        result = apply_fa_normalization(snr, fa)
        # Near-zero sin → NaN in output
        assert np.isnan(result.snr_fa_corrected[0])
        assert np.isnan(result.snr_fa_corrected[1])
        # 90° → valid
        assert not np.isnan(result.snr_fa_corrected[2])

    def test_near_zero_count_in_provenance(self):
        snr = np.ones(5, dtype=np.float32)
        fa = np.zeros(5, dtype=np.float32)
        result = apply_fa_normalization(snr, fa)
        assert result.provenance["nNearZeroVoxelsMasked"] == 5

    def test_very_small_fa_treated_as_near_zero(self):
        snr = np.array([1.0], dtype=np.float32)
        small_deg = math.degrees(EPSILON / 2)  # sin below threshold
        fa = np.array([small_deg], dtype=np.float32)
        result = apply_fa_normalization(snr, fa)
        assert np.isnan(result.snr_fa_corrected[0])


# ---------------------------------------------------------------------------
# Test 4 — Geometry mismatch: validation / resampling
# ---------------------------------------------------------------------------
class TestGeometryValidation:
    def test_compatible_geometry_no_resample(self, tmp_path):
        """Same geometry → FA returned unchanged (no resampling)."""
        arr = np.ones((10, 10, 5), dtype=np.float32) * 60.0
        fa_path = str(tmp_path / "fa.nii.gz")
        _make_nifti(arr, fa_path, spacing=(2.0, 2.0, 4.0))

        fa_img = load_fa_map(fa_path)

        # Build matching reference SNR Imaginable
        snr_arr = np.ones((10, 10, 5), dtype=np.float32)
        snr_img = ima.numpyToImaginable(snr_arr)
        snr_img.setImageSpacing([2.0, 2.0, 4.0])

        result_img = validate_and_resample_fa(fa_img, snr_img)
        # Should return an Imaginable; values should still be ~60
        out = result_img.getImageAsNumpy()
        np.testing.assert_allclose(out, arr, rtol=1e-3)

    def test_different_spacing_triggers_resample(self, tmp_path):
        """Different spacing → resampled onto SNR geometry."""
        arr_fa = np.ones((20, 20, 5), dtype=np.float32) * 45.0
        fa_path = str(tmp_path / "fa_coarse.nii.gz")
        _make_nifti(arr_fa, fa_path, spacing=(4.0, 4.0, 4.0))

        fa_img = load_fa_map(fa_path)

        snr_arr = np.ones((10, 10, 5), dtype=np.float32)
        snr_img = ima.numpyToImaginable(snr_arr)
        snr_img.setImageSpacing([2.0, 2.0, 4.0])

        # Should not raise — resampling should succeed
        result_img = validate_and_resample_fa(fa_img, snr_img)
        assert result_img is not None

    def test_missing_fa_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_fa_map("/nonexistent/path/fa.nii.gz")


# ---------------------------------------------------------------------------
# Test 5 — End-to-end normalize_snr_with_fa convenience function
# ---------------------------------------------------------------------------
class TestEndToEnd:
    def test_full_pipeline_fa90(self, tmp_path):
        """End-to-end: SNR / sin(90°) == SNR."""
        snr_data = np.random.rand(8, 8, 3).astype(np.float32) * 100
        fa_data = np.full((8, 8, 3), 90.0, dtype=np.float32)

        fa_path = str(tmp_path / "fa90.nii.gz")
        _make_nifti(fa_data, fa_path, spacing=(2.0, 2.0, 4.0))

        snr_img = ima.numpyToImaginable(snr_data)
        snr_img.setImageSpacing([2.0, 2.0, 4.0])

        result = normalize_snr_with_fa(snr_data, snr_img, fa_path)
        np.testing.assert_allclose(result.snr_fa_corrected, snr_data, rtol=1e-4)
        assert result.provenance["faCorrectionApplied"] is True

    def test_full_pipeline_fa30(self, tmp_path):
        """End-to-end: SNR / sin(30°) == SNR * 2."""
        snr_data = np.ones((4, 4, 2), dtype=np.float32) * 50.0
        fa_data = np.full((4, 4, 2), 30.0, dtype=np.float32)

        fa_path = str(tmp_path / "fa30.nii.gz")
        _make_nifti(fa_data, fa_path, spacing=(2.0, 2.0, 4.0))

        snr_img = ima.numpyToImaginable(snr_data)
        snr_img.setImageSpacing([2.0, 2.0, 4.0])

        result = normalize_snr_with_fa(snr_data, snr_img, fa_path)
        expected = snr_data / math.sin(math.radians(30))
        np.testing.assert_allclose(result.snr_fa_corrected, expected, rtol=1e-4)

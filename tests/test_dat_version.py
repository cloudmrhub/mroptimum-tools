"""
Tests for Siemens .dat file version detection and metadata extraction.

Test structure:
    1. Unit tests for classify_platform() — pure logic, no files needed
    2. Unit tests for orientation/acceleration extraction with mocked headers
    3. Integration test (CLI) that can be pointed at real .dat files

Run unit tests:
    conda run -n mro python -m pytest tests/test_dat_version.py -v

Run integration test against a real file:
    conda run -n mro python tests/test_dat_version.py /path/to/file.dat
"""

import sys
import os
import json
import numpy as np
import pytest
from typing import Dict
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mrotools.dat_version import (
    classify_platform,
    detect_version_from_file,
    DatFileInfo,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. classify_platform() unit tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestClassifyPlatform:
    """Test platform classification from syngo version strings."""

    # VB versions
    @pytest.mark.parametrize("version", ["B13", "B15", "B17", "B19", "B20"])
    def test_vb_versions(self, version):
        assert classify_platform(version) == "VB"

    # VD versions
    @pytest.mark.parametrize("version", ["D11", "D13", "D13D"])
    def test_vd_versions(self, version):
        assert classify_platform(version) == "VD"

    # VE versions
    @pytest.mark.parametrize("version", ["E11", "E11C", "E12U"])
    def test_ve_versions(self, version):
        assert classify_platform(version) == "VE"

    # XA versions
    @pytest.mark.parametrize("version", [
        "XA10", "XA11", "XA20", "XA30", "XA31", "XA50", "XA51", "XA60", "XA61"
    ])
    def test_xa_versions(self, version):
        assert classify_platform(version) == "XA"

    # Full syngo strings
    def test_full_syngo_string_vb(self):
        assert classify_platform("syngo MR B17") == "VB"

    def test_full_syngo_string_vd(self):
        assert classify_platform("syngo MR D13") == "VD"

    def test_full_syngo_string_xa(self):
        assert classify_platform("syngo MR XA30") == "XA"

    def test_full_syngo_string_xa_with_extra(self):
        assert classify_platform("syngo MR XA50A") == "XA"

    # Edge cases
    def test_lowercase(self):
        assert classify_platform("b17") == "VB"

    def test_whitespace(self):
        assert classify_platform("  XA30  ") == "XA"

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            classify_platform("Z99")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            classify_platform("")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Mock header tests for orientation/acceleration extraction
# ═══════════════════════════════════════════════════════════════════════════════


def _make_mock_header(platform="VD", n_slices=3, base_res=256, phase_lines=256,
                      readout_fov=256.0, phase_fov=256.0, thickness=5.0,
                      origin=(10.0, -20.0, 30.0), normal_axis="tra",
                      accel_pe=1, ref_lines_pe=24,
                      patient_position="HFS"):
    """
    Build a mock twix header dict that mimics what twixtools produces.
    Adjusts key paths based on platform to simulate real differences.
    """
    # Build slice array
    slices = []
    for i in range(n_slices):
        sl = {
            "dReadoutFOV": readout_fov,
            "dPhaseFOV": phase_fov,
            "dThickness": thickness,
            "sPosition": {
                "dSag": origin[0] + i * 0.1,
                "dCor": origin[1] + i * 0.1,
                "dTra": origin[2] + i * thickness,
            },
            "sNormal": {},
        }
        if normal_axis == "tra":
            sl["sNormal"]["dTra"] = 1.0
        elif normal_axis == "sag":
            sl["sNormal"]["dSag"] = 1.0
        elif normal_axis == "cor":
            sl["sNormal"]["dCor"] = 1.0
        elif normal_axis == "oblique":
            sl["sNormal"]["dTra"] = 0.7071
            sl["sNormal"]["dSag"] = 0.7071
        slices.append(sl)

    slice_array = {"lSize": n_slices, "asSlice": slices}

    hdr = {
        "Config": {
            "BaseResolution": str(base_res),
            "PhaseEncodingLines": str(phase_lines),
        },
        "Phoenix": {
            "sSliceArray": slice_array,
        },
        "MeasYaps": {
            "sSliceArray": slice_array,
            "sPat": {
                "lAccelFactPE": accel_pe,
                "lRefLinesPE": ref_lines_pe,
            },
            "sKSpace": {
                "lBaseResolution": base_res,
                "lPhaseEncodingLines": phase_lines,
                "ucDimension": 2,
            },
        },
        "Dicom": {
            "SoftwareVersions": {
                "VB": "syngo MR B17",
                "VD": "syngo MR D13",
                "VE": "syngo MR E11",
                "XA": "syngo MR XA30",
            }[platform],
        },
        "Meas": {},
    }

    # Platform-specific patient position paths
    if platform in ("VB", "VD", "VE"):
        hdr["Meas"]["tPatientPosition"] = patient_position
    else:  # XA
        hdr["Meas"]["sPatPosition"] = patient_position

    # Slice ordering (simulate different keys)
    if platform == "VB":
        hdr["Config"]["relSliceNumber"] = " ".join(
            str(i) for i in range(n_slices)
        ) + " -1"
    else:
        hdr["Config"]["chronSliceIndices"] = " ".join(
            str(i) for i in range(n_slices)
        )

    return hdr


def _make_mock_twix_data(platform="VD", **kwargs):
    """
    Build a mock twix data list that DatFileInfo expects.
    For VB: single raid. For VD/VE/XA: two raids (noise + signal).
    """
    signal_hdr = _make_mock_header(platform=platform, **kwargs)

    if platform == "VB":
        # Single raid
        return [
            {"hdr": signal_hdr, "image": MagicMock(), "noise": MagicMock()},
        ]
    else:
        # Multi-raid: raid 0 = noise, raid 1 = signal
        noise_hdr = _make_mock_header(platform=platform, **kwargs)
        return [
            {"hdr": noise_hdr, "noise": MagicMock()},
            {"hdr": signal_hdr, "image": MagicMock(), "refscan": MagicMock()},
        ]


class TestDatFileInfoMocked:
    """
    Test DatFileInfo with mocked twixtools to verify version-aware extraction
    without requiring real .dat files.
    """

    def _create_info(self, platform, **kwargs):
        """Create a DatFileInfo instance with mocked file and twix data."""
        is_multiraid = platform != "VB"
        n_scans = 2 if is_multiraid else 1
        mock_twix = _make_mock_twix_data(platform=platform, **kwargs)

        with patch("mrotools.dat_version.detect_version_from_file",
                   return_value=(is_multiraid, n_scans)):
            with patch("mrotools.dat_version.os.path.isfile", return_value=True):
                with patch("mrotools.dat_version.os.path.expanduser", side_effect=lambda x: x):
                    with patch("mrotools.dat_version.os.path.realpath", side_effect=lambda x: x):
                        info = DatFileInfo.__new__(DatFileInfo)
                        info.filepath = "/mock/test.dat"
                        info._twix_data = mock_twix
                        info._is_ve_format = is_multiraid
                        info._n_scans = n_scans
                        info._syngo_version = None
                        info._platform = None
        return info

    # --- Platform detection tests ---

    @pytest.mark.parametrize("platform", ["VB", "VD", "VE", "XA"])
    def test_platform_detection(self, platform):
        info = self._create_info(platform)
        assert info.platform == platform

    @pytest.mark.parametrize("platform", ["VB", "VD", "VE", "XA"])
    def test_syngo_version(self, platform):
        info = self._create_info(platform)
        expected = {"VB": "B17", "VD": "D13", "VE": "E11", "XA": "XA30"}
        assert info.syngo_version == expected[platform]

    # --- Multiraid tests ---

    def test_vb_not_multiraid(self):
        info = self._create_info("VB")
        assert info.is_multiraid is False
        assert info.n_raids == 1
        assert info.signal_raid == 0
        assert info.noise_raid is None

    @pytest.mark.parametrize("platform", ["VD", "VE", "XA"])
    def test_multiraid_structure(self, platform):
        info = self._create_info(platform)
        assert info.is_multiraid is True
        assert info.n_raids == 2
        assert info.signal_raid == 1
        assert info.noise_raid == 0

    # --- Orientation extraction tests ---

    @pytest.mark.parametrize("platform", ["VB", "VD", "VE", "XA"])
    def test_orientation_spacing(self, platform):
        info = self._create_info(platform, base_res=128, phase_lines=128,
                                 readout_fov=256.0, phase_fov=256.0)
        orient = info.orientation(0)
        assert orient["spacing"] == [2.0, 2.0, 5.0]

    @pytest.mark.parametrize("platform", ["VB", "VD", "VE", "XA"])
    def test_orientation_origin(self, platform):
        info = self._create_info(platform, origin=(10.0, -20.0, 30.0))
        orient = info.orientation(0)
        np.testing.assert_allclose(orient["origin"], [10.0, -20.0, 30.0], atol=0.2)

    @pytest.mark.parametrize("platform", ["VB", "VD", "VE", "XA"])
    def test_orientation_fov(self, platform):
        info = self._create_info(platform, readout_fov=320.0, phase_fov=240.0,
                                 thickness=3.0, n_slices=5)
        orient = info.orientation(0)
        assert orient["fov"] == [320.0, 240.0, 15.0]

    def test_orientation_axial_direction(self):
        """Axial slice: normal along Tra."""
        info = self._create_info("VD", normal_axis="tra")
        orient = info.orientation(0)
        direction = orient["direction"]
        # For pure axial: direction[2,2] should be -1.0 (from -normal["dTra"])
        assert direction[2, 2] == pytest.approx(-1.0)
        # Other diagonals should be -1 (from -eye initialization)
        assert direction[0, 0] == pytest.approx(-1.0)
        assert direction[1, 1] == pytest.approx(-1.0)

    def test_orientation_sagittal_direction(self):
        """Sagittal slice: normal along Sag."""
        info = self._create_info("VD", normal_axis="sag")
        orient = info.orientation(0)
        direction = orient["direction"]
        assert direction[0, 0] == pytest.approx(1.0)
        assert direction[1, 1] == pytest.approx(-1.0)
        assert direction[2, 2] == pytest.approx(-1.0)

    def test_orientation_coronal_direction(self):
        """Coronal slice: normal along Cor."""
        info = self._create_info("VD", normal_axis="cor")
        orient = info.orientation(0)
        direction = orient["direction"]
        assert direction[0, 0] == pytest.approx(-1.0)
        assert direction[1, 1] == pytest.approx(1.0)
        assert direction[2, 2] == pytest.approx(-1.0)

    def test_orientation_oblique_direction(self):
        """Oblique slice: mixed normal components."""
        info = self._create_info("VD", normal_axis="oblique")
        orient = info.orientation(0)
        direction = orient["direction"]
        # Oblique: dTra=0.7071, dSag=0.7071
        assert direction[0, 0] == pytest.approx(0.7071, abs=1e-3)
        assert direction[2, 2] == pytest.approx(-0.7071, abs=1e-3)

    # --- Patient position (version-specific paths) ---

    def test_patient_position_vb(self):
        info = self._create_info("VB", patient_position="HFS")
        orient = info.orientation(0)
        assert orient["patient_position"] == "HFS"

    def test_patient_position_xa(self):
        """XA uses a different header path for patient position."""
        info = self._create_info("XA", patient_position="FFS")
        orient = info.orientation(0)
        assert orient["patient_position"] == "FFS"

    # --- Acceleration extraction ---

    @pytest.mark.parametrize("platform", ["VB", "VD", "VE", "XA"])
    def test_acceleration_no_accel(self, platform):
        info = self._create_info(platform, accel_pe=1, ref_lines_pe=24)
        accel, acl = info.acceleration()
        assert accel == [1, 1]
        assert acl[1] == 24

    @pytest.mark.parametrize("platform", ["VD", "VE", "XA"])
    def test_acceleration_with_accel(self, platform):
        info = self._create_info(platform, accel_pe=2, ref_lines_pe=32)
        accel, acl = info.acceleration()
        assert accel == [1, 2]
        assert acl[1] == 32

    # --- Multi-slice ---

    @pytest.mark.parametrize("platform", ["VB", "VD", "VE", "XA"])
    def test_all_orientations(self, platform):
        info = self._create_info(platform, n_slices=5)
        orientations = info.all_orientations()
        assert len(orientations) == 5
        # Each slice should have different origin (offset by thickness)
        for i in range(1, 5):
            assert orientations[i]["origin"][2] != orientations[0]["origin"][2]

    # --- Summary ---

    @pytest.mark.parametrize("platform", ["VB", "VD", "VE", "XA"])
    def test_summary_keys(self, platform):
        info = self._create_info(platform)
        s = info.summary()
        required_keys = [
            "filepath", "platform", "syngo_version", "is_multiraid",
            "n_raids", "signal_raid", "noise_raid", "scan_types",
            "n_slices", "matrix_size", "spacing", "origin", "fov",
            "patient_position", "acceleration", "acl",
        ]
        for key in required_keys:
            assert key in s, f"Missing key '{key}' in summary"

    # --- Scan types ---

    def test_scan_types_vb(self):
        info = self._create_info("VB")
        st = info.scan_types
        assert 0 in st
        assert "image" in st[0]

    def test_scan_types_multiraid(self):
        info = self._create_info("VD")
        st = info.scan_types
        assert 0 in st
        assert 1 in st
        assert "noise" in st[0]
        assert "image" in st[1]


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Integration test (real file) — run as script
# ═══════════════════════════════════════════════════════════════════════════════


def run_integration_test(dat_path: str) -> Dict:
    """
    Run full integration test against a real .dat file.
    Prints a comprehensive report and returns the summary dict.
    """
    print("=" * 70)
    print(f"DAT FILE VERSION TEST")
    print(f"File: {dat_path}")
    print("=" * 70)

    info = DatFileInfo(dat_path)
    summary = info.summary()

    print(f"\n--- Version Detection ---")
    print(f"  Platform:       {info.platform}")
    print(f"  Syngo Version:  {info.syngo_version}")
    print(f"  Is Multiraid:   {info.is_multiraid}")
    print(f"  N Raids:        {info.n_raids}")
    print(f"  Signal Raid:    {info.signal_raid}")
    print(f"  Noise Raid:     {info.noise_raid}")

    print(f"\n--- Scan Types ---")
    for raid_idx, types in info.scan_types.items():
        print(f"  Raid {raid_idx}: {types}")

    print(f"\n--- Orientation (slice 0) ---")
    orient = info.orientation(0)
    print(f"  Spacing:          {orient['spacing']}")
    print(f"  Origin:           {orient['origin']}")
    print(f"  FOV:              {orient['fov']}")
    print(f"  Size:             {orient['size']}")
    print(f"  Patient Position: {orient['patient_position']}")
    print(f"  N Slices:         {orient['n_slices']}")
    print(f"  Direction:\n{orient['direction']}")

    print(f"\n--- Acceleration ---")
    accel, acl = info.acceleration()
    print(f"  Acceleration: {accel}")
    print(f"  ACL:          {acl}")

    # Validate consistency
    print(f"\n--- Consistency Checks ---")
    errors = []

    # Check spacing is positive
    if any(s <= 0 for s in orient["spacing"]):
        errors.append(f"Non-positive spacing: {orient['spacing']}")
    else:
        print(f"  [OK] Spacing is positive")

    # Check FOV is positive
    if any(f <= 0 for f in orient["fov"]):
        errors.append(f"Non-positive FOV: {orient['fov']}")
    else:
        print(f"  [OK] FOV is positive")

    # Check direction is a valid rotation-like matrix
    det = np.linalg.det(orient["direction"])
    if abs(abs(det) - 1.0) > 0.5:
        errors.append(f"Direction matrix determinant = {det:.3f} (expected +/-1)")
    else:
        print(f"  [OK] Direction matrix determinant = {det:.3f}")

    # Check acceleration makes sense
    if accel[1] < 1:
        errors.append(f"Invalid phase acceleration: {accel[1]}")
    else:
        print(f"  [OK] Acceleration factor >= 1")

    # Check multiraid consistency
    if info.is_multiraid and info.n_raids < 2:
        errors.append("Multiraid flagged but only 1 raid found")
    else:
        print(f"  [OK] Multiraid consistency")

    # Check platform vs file format consistency
    if info.platform == "VB" and info.is_multiraid:
        errors.append("VB platform should not be multiraid")
    elif info.platform in ("VD", "VE", "XA") and not info.is_multiraid:
        # This can happen with single-scan VD files, not necessarily an error
        print(f"  [WARN] {info.platform} platform but not multiraid (single-scan file?)")
    else:
        print(f"  [OK] Platform/format consistency")

    # Multi-slice orientation check
    if orient["n_slices"] > 1:
        all_orient = info.all_orientations()
        origins = [o["origin"] for o in all_orient]
        # Check that slices have distinct origins
        unique_origins = len(set(tuple(o) for o in origins))
        if unique_origins < orient["n_slices"]:
            print(f"  [WARN] Only {unique_origins}/{orient['n_slices']} unique origins")
        else:
            print(f"  [OK] All {orient['n_slices']} slices have distinct origins")

    if errors:
        print(f"\n  ERRORS:")
        for e in errors:
            print(f"    [FAIL] {e}")
    else:
        print(f"\n  ALL CHECKS PASSED")

    print("=" * 70)
    return summary


# ═══════════════════════════════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Integration test mode: pass one or more .dat files
        results = []
        for fpath in sys.argv[1:]:
            if os.path.isfile(fpath):
                result = run_integration_test(fpath)
                results.append(result)
            elif os.path.isdir(fpath):
                # Process all .dat files in directory
                for fname in sorted(os.listdir(fpath)):
                    if fname.lower().endswith(".dat"):
                        result = run_integration_test(os.path.join(fpath, fname))
                        results.append(result)
            else:
                print(f"[SKIP] Not found: {fpath}")

        if results:
            print(f"\n\n{'=' * 70}")
            print(f"SUMMARY: Tested {len(results)} file(s)")
            print(f"{'=' * 70}")
            for r in results:
                print(f"  {os.path.basename(r['filepath']):40s} "
                      f"platform={r['platform']:3s}  "
                      f"version={r['syngo_version']:6s}  "
                      f"raids={r['n_raids']}  "
                      f"slices={r['n_slices']}")
    else:
        # Run pytest unit tests
        print("No .dat file provided — running unit tests with pytest.")
        print("Usage: python tests/test_dat_version.py /path/to/file.dat")
        print("       python -m pytest tests/test_dat_version.py -v")
        sys.exit(pytest.main([__file__, "-v"]))

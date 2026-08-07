"""
Siemens .dat file version detection and metadata extraction.

Identifies the scanner software platform (VB, VD, VE, XA) from a .dat file
and provides version-aware extraction of orientation, acceleration, and
geometric metadata.

Platform differences handled:
    VB  : Single-raid file, signal at raid 0, different slice ordering keys
    VD  : Multi-raid, noise at raid 0, signal at raid 1+
    VE  : Same structure as VD with minor header key changes
    XA  : Multi-raid, some header paths moved (e.g. patient position)

Usage:
    from mrotools.dat_version import DatFileInfo

    info = DatFileInfo("/path/to/file.dat")
    print(info.platform)          # 'VB', 'VD', 'VE', or 'XA'
    print(info.syngo_version)     # e.g. 'B17', 'XA30'
    print(info.is_multiraid)      # True for VD/VE/XA
    print(info.n_raids)           # number of raids/measurements
    print(info.signal_raid)       # raid index where signal data lives
    print(info.orientation(0))    # orientation dict for first slice
    print(info.acceleration())    # (acceleration, acl) tuple
"""

import os
import re
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

import twixtools
import twixtools.helpers as tw_helpers


# ---------------------------------------------------------------------------
# Platform classification
# ---------------------------------------------------------------------------

# Maps the first letter(s) of the syngo version string to a platform name
_VERSION_PREFIX_MAP = {
    "B": "VB",
    "C": "VB",   # very old syngo C versions mapped to VB
    "D": "VD",
    "E": "VE",
    "X": "XA",   # XA10, XA20, XA30, XA50, XA60...
}


def classify_platform(syngo_version: str) -> str:
    """
    Classify the Siemens platform from a syngo version string.

    Args:
        syngo_version: Version string like 'B17', 'D13', 'E11', 'XA30'.
                       Can also be a longer string like 'syngo MR XA30'
                       or raw format like '4VB13A'.

    Returns:
        Platform string: 'VB', 'VD', 'VE', or 'XA'.

    Raises:
        ValueError: If the version string cannot be classified.
    """
    # Strip common prefixes
    v = syngo_version.strip()
    # Handle full strings like "syngo MR XA30" or "syngo MR B17"
    if " " in v:
        v = v.split()[-1]

    if not v:
        raise ValueError(f"Empty version string: '{syngo_version}'")

    # Try XA first (two-char prefix)
    if v.upper().startswith("XA") or "XA" in v.upper():
        return "XA"

    # Handle raw format like "4VB13A", "4VD11C" — strip leading digits
    v_stripped = v.lstrip("0123456789")
    if v_stripped:
        v = v_stripped

    # Check for VB/VD/VE embedded in the string
    v_upper = v.upper()
    if "VB" in v_upper:
        return "VB"
    if "VD" in v_upper:
        return "VD"
    if "VE" in v_upper:
        return "VE"

    prefix = v[0].upper()
    if prefix in _VERSION_PREFIX_MAP:
        return _VERSION_PREFIX_MAP[prefix]

    raise ValueError(
        f"Cannot classify platform from version '{syngo_version}'. "
        f"Expected prefix in {list(_VERSION_PREFIX_MAP.keys())} or 'XA'."
    )


def detect_version_from_file(filepath: str) -> Tuple[bool, int]:
    """
    Detect file-level version (VB vs VD/VE/XA) from binary header.

    Args:
        filepath: Path to .dat file.

    Returns:
        (is_vd_or_later, n_scans): Whether the file uses VD+ multi-raid
        format, and how many scans/raids it contains.
    """
    filepath = os.path.expanduser(filepath)
    with open(filepath, "rb") as fid:
        return tw_helpers.idea_version_check(fid)


# ---------------------------------------------------------------------------
# DatFileInfo: main class
# ---------------------------------------------------------------------------

@dataclass
class DatFileInfo:
    """
    Comprehensive metadata about a Siemens .dat file.

    Provides version detection and version-aware extraction of orientation,
    acceleration, and geometric metadata needed by mroptimum.
    """

    filepath: str
    _twix_data: Any = field(default=None, repr=False)
    _is_ve_format: Optional[bool] = field(default=None, repr=False)
    _n_scans: Optional[int] = field(default=None, repr=False)
    _syngo_version: Optional[str] = field(default=None, repr=False)
    _platform: Optional[str] = field(default=None, repr=False)

    def __post_init__(self):
        self.filepath = os.path.expanduser(os.path.realpath(self.filepath))
        if not os.path.isfile(self.filepath):
            raise FileNotFoundError(f"DAT file not found: {self.filepath}")
        # Detect binary format version
        self._is_ve_format, self._n_scans = detect_version_from_file(self.filepath)

    # ----- Lazy loading ----------------------------------------------------

    @property
    def twix_data(self):
        """Parsed twix data (list of raids). Loaded lazily."""
        if self._twix_data is None:
            # Try map_twix first (provides twix_array objects).
            # If it fails (e.g. missing 'Meas' key in XA files), fall back
            # to read_twix which just gives us headers + mdb lists.
            try:
                raw = twixtools.read_twix(self.filepath, verbose=False, parse_geometry=False)
                self._twix_data = twixtools.map_twix(raw, verbose=False)
            except (KeyError, TypeError, ValueError):
                # Fallback: use raw read_twix output (list of dicts with 'hdr' + 'mdb')
                self._twix_data = twixtools.read_twix(
                    self.filepath, verbose=False,
                    parse_geometry=False, parse_data=False,
                )
        return self._twix_data

    # ----- Version properties ----------------------------------------------

    @property
    def is_multiraid(self) -> bool:
        """True if the file uses VD/VE/XA multi-raid format."""
        return self._is_ve_format

    @property
    def n_raids(self) -> int:
        """Number of raids (measurements) in the file."""
        if self._is_ve_format:
            return self._n_scans
        return 1

    @property
    def signal_raid(self) -> int:
        """Raid index where the signal (image) data is located."""
        if self.is_multiraid:
            return len(self.twix_data) - 1
        return 0

    @property
    def noise_raid(self) -> Optional[int]:
        """
        Raid index for noise data, or None if no dedicated noise raid.
        For multi-raid files (VD/VE/XA), noise is typically in raid 0.
        """
        if self.is_multiraid and len(self.twix_data) > 1:
            return 0
        return None

    @property
    def syngo_version(self) -> str:
        """
        Syngo software version string (e.g. 'B17', 'XA30').
        Extracted from the Dicom header of the signal raid.
        """
        if self._syngo_version is None:
            raid_idx = self.signal_raid
            hdr = self.twix_data[raid_idx]["hdr"]
            try:
                self._syngo_version = tw_helpers.get_syngo_version(hdr)
            except (KeyError, TypeError, AttributeError, IndexError):
                # Fallback: try to find version info elsewhere
                self._syngo_version = self._fallback_version_detection(hdr)
        return self._syngo_version

    @property
    def platform(self) -> str:
        """
        Platform classification: 'VB', 'VD', 'VE', or 'XA'.
        """
        if self._platform is None:
            try:
                self._platform = classify_platform(self.syngo_version)
            except (ValueError, TypeError):
                # Fall back to binary-level detection
                self._platform = "VD" if self._is_ve_format else "VB"
        return self._platform

    @property
    def is_vb(self) -> bool:
        return self.platform == "VB"

    @property
    def is_vd(self) -> bool:
        return self.platform == "VD"

    @property
    def is_ve(self) -> bool:
        return self.platform == "VE"

    @property
    def is_xa(self) -> bool:
        return self.platform == "XA"

    # ----- Header access ---------------------------------------------------

    @property
    def signal_header(self) -> Dict:
        """Header dict for the signal raid."""
        return self.twix_data[self.signal_raid]["hdr"]

    @property
    def scan_types(self) -> Dict[int, List[str]]:
        """
        Available scan types per raid.
        Returns dict mapping raid_idx -> list of scan type keys.
        """
        result = {}
        for idx, raid in enumerate(self.twix_data):
            keys = [k for k in raid.keys() if k not in ("hdr", "hdr_str", "raidfile_hdr")]
            result[idx] = keys
        return result

    # ----- Orientation extraction ------------------------------------------

    def orientation(self, slice_idx: int = 0) -> Dict:
        """
        Extract orientation metadata for a given slice.

        Uses version-aware header paths to extract spacing, origin,
        direction, and FOV. Falls back gracefully when keys are missing.

        Args:
            slice_idx: Slice index (0-based).

        Returns:
            Dict with keys: spacing, origin, direction (3x3 ndarray),
            fov, size, patient_position.
        """
        hdr = self.signal_header
        raid_idx = self.signal_raid

        # --- Resolution ---
        base_res, phase_lines = self._get_matrix_size(hdr)

        # --- Slice array (version-aware paths) ---
        slice_array = self._get_slice_array(hdr)
        n_slices = self._safe_int(slice_array.get("lSize", 1), 1)

        # Clamp slice_idx
        slice_idx = min(slice_idx, n_slices - 1)

        # Slice ordering
        slice_order = self._get_slice_order(hdr, n_slices)
        if slice_order and slice_idx < len(slice_order):
            # Map from chronological to physical slice index
            physical_idx = slice_order.index(slice_idx) if slice_idx in slice_order else slice_idx
        else:
            physical_idx = slice_idx

        sl = slice_array["asSlice"][physical_idx]

        # --- Position/Origin ---
        origin = self._extract_position(sl)

        # --- Spacing & FOV ---
        readout_fov = self._safe_float(sl.get("dReadoutFOV", 256.0), 256.0)
        phase_fov = self._safe_float(sl.get("dPhaseFOV", 256.0), 256.0)
        thickness = self._safe_float(sl.get("dThickness", 5.0), 5.0)

        spacing = [
            readout_fov / base_res if base_res > 0 else 1.0,
            phase_fov / phase_lines if phase_lines > 0 else 1.0,
            thickness,
        ]
        fov = [readout_fov, phase_fov, thickness * n_slices]

        # --- Direction (normal vector) ---
        direction = self._extract_direction(sl)

        # --- Patient position ---
        patient_position = self._get_patient_position(hdr)

        return {
            "spacing": spacing,
            "origin": origin,
            "direction": direction,
            "fov": fov,
            "size": [base_res, phase_lines, 1],
            "patient_position": patient_position,
            "n_slices": n_slices,
        }

    def all_orientations(self) -> List[Dict]:
        """Extract orientation for all slices."""
        hdr = self.signal_header
        slice_array = self._get_slice_array(hdr)
        n_slices = int(slice_array.get("lSize", 1))
        return [self.orientation(i) for i in range(n_slices)]

    # ----- Acceleration extraction -----------------------------------------

    def acceleration(self) -> Tuple[List, List]:
        """
        Extract acceleration and autocalibration line info.

        Returns:
            (acceleration, acl) where:
                acceleration = [freq_accel, phase_accel]
                acl = [freq_acl, phase_acl]
        """
        hdr = self.signal_header
        try:
            iPat = hdr["MeasYaps"]["sPat"]
            raw_pe = iPat.get("lAccelFactPE", 1)
            raw_3d = iPat.get("lAccelFact3D", 1)

            # Handle NaN / None / float gracefully
            try:
                phase_accel = int(raw_pe) if raw_pe is not None and not (isinstance(raw_pe, float) and np.isnan(raw_pe)) else 1
            except (ValueError, TypeError):
                phase_accel = 1

            try:
                freq_accel = int(raw_3d) if raw_3d is not None and not (isinstance(raw_3d, float) and np.isnan(raw_3d)) else 1
            except (ValueError, TypeError):
                freq_accel = 1

            if freq_accel <= 0:
                freq_accel = 1
            if phase_accel <= 0:
                phase_accel = 1

            raw_ref = iPat.get("lRefLinesPE", None)
            try:
                ref_lines_pe = int(raw_ref) if raw_ref is not None and not (isinstance(raw_ref, float) and np.isnan(raw_ref)) else np.nan
            except (ValueError, TypeError):
                ref_lines_pe = np.nan
        except (KeyError, TypeError):
            phase_accel = 1
            freq_accel = 1
            ref_lines_pe = np.nan

        return [freq_accel, phase_accel], [np.nan, ref_lines_pe]

    # ----- Summary / report ------------------------------------------------

    def summary(self) -> Dict:
        """
        Return a comprehensive summary of the .dat file metadata.
        Useful for inventorying and debugging.
        """
        orient = self.orientation(0)
        accel, acl = self.acceleration()

        return {
            "filepath": self.filepath,
            "platform": self.platform,
            "syngo_version": self.syngo_version,
            "is_multiraid": self.is_multiraid,
            "n_raids": self.n_raids,
            "signal_raid": self.signal_raid,
            "noise_raid": self.noise_raid,
            "scan_types": self.scan_types,
            "n_slices": orient["n_slices"],
            "matrix_size": orient["size"],
            "spacing": orient["spacing"],
            "origin": orient["origin"],
            "fov": orient["fov"],
            "patient_position": orient["patient_position"],
            "acceleration": accel,
            "acl": acl,
        }

    # ----- Private helpers -------------------------------------------------

    @staticmethod
    def _safe_int(val, default: int = 0) -> int:
        """Safely convert a value to int, handling NaN/None/float."""
        if val is None:
            return default
        try:
            f = float(val)
            if np.isnan(f) or np.isinf(f):
                return default
            return int(f)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_float(val, default: float = 0.0) -> float:
        """Safely convert a value to float, handling NaN/None."""
        if val is None:
            return default
        try:
            f = float(val)
            if np.isnan(f) or np.isinf(f):
                return default
            return f
        except (ValueError, TypeError):
            return default

    def _fallback_version_detection(self, hdr: Dict) -> str:
        """Try alternative header paths to find version info."""
        # Try Dicom directly
        try:
            sv = hdr["Dicom"]["SoftwareVersions"]
            if sv:
                return sv.split()[-1] if " " in sv else sv
        except (KeyError, TypeError, AttributeError):
            pass
        # Try MeasYaps path
        try:
            return hdr["MeasYaps"]["tMeasUID"]
        except (KeyError, TypeError):
            pass
        # Try Meas path
        try:
            sw = hdr.get("Meas", {}).get("tSoftwareVersion", "")
            if sw:
                return sw.split()[-1]
        except (KeyError, TypeError, AttributeError):
            pass
        # Try Config tSoftwareVersion
        try:
            sw = hdr.get("Config", {}).get("SoftwareVersions", "")
            if sw:
                return sw.split()[-1]
        except (KeyError, TypeError, AttributeError):
            pass
        # Last resort: infer from file format
        return "VD" if self._is_ve_format else "VB"

    def _get_matrix_size(self, hdr: Dict) -> Tuple[int, int]:
        """
        Get base resolution and phase encoding lines.
        Tries Config first (available in all versions), falls back to MeasYaps.
        """
        # Primary path: Config (populated by twixtools for all versions)
        try:
            raw_base = hdr["Config"]["BaseResolution"]
            raw_phase = hdr["Config"]["PhaseEncodingLines"]
            base_res = int(float(raw_base)) if raw_base is not None else 256
            phase_lines = int(float(raw_phase)) if raw_phase is not None else 256
            if base_res > 0 and phase_lines > 0:
                return base_res, phase_lines
        except (KeyError, TypeError, ValueError):
            pass

        # Fallback: MeasYaps
        try:
            kspace = hdr["MeasYaps"]["sKSpace"]
            raw_base = kspace["lBaseResolution"]
            raw_phase = kspace["lPhaseEncodingLines"]
            base_res = int(float(raw_base)) if raw_base is not None else 256
            phase_lines = int(float(raw_phase)) if raw_phase is not None else 256
            if base_res > 0 and phase_lines > 0:
                return base_res, phase_lines
        except (KeyError, TypeError, ValueError):
            pass

        # Last resort defaults
        return 256, 256

    def _get_slice_array(self, hdr: Dict) -> Dict:
        """
        Get the slice array from the header.
        Tries Phoenix first, then MeasYaps.
        """
        # Phoenix (Config protocol) - most reliable across versions
        try:
            sa = hdr["Phoenix"]["sSliceArray"]
            if "asSlice" in sa:
                return sa
        except (KeyError, TypeError):
            pass

        # MeasYaps (Measurement protocol)
        try:
            sa = hdr["MeasYaps"]["sSliceArray"]
            if "asSlice" in sa:
                return sa
        except (KeyError, TypeError):
            pass

        raise KeyError("Cannot find sSliceArray in header (tried Phoenix and MeasYaps)")

    def _get_slice_order(self, hdr: Dict, n_slices: int) -> Optional[List[int]]:
        """
        Get slice ordering. Different keys across versions.

        Priority:
        1. Config['chronSliceIndices'] (twixtools geometry module uses this)
        2. Config['relSliceNumber'] (older approach, used in current mro.py)
        3. None (sequential ordering)
        """
        # chronSliceIndices (robust across versions when present)
        try:
            chron_str = hdr["Config"]["chronSliceIndices"]
            if chron_str and chron_str[0] != "-":
                order = [int(s) for s in chron_str.split() if s.isdigit()]
                if len(order) >= n_slices:
                    return order[:n_slices]
        except (KeyError, TypeError, ValueError):
            pass

        # relSliceNumber (VB/VD legacy)
        try:
            rel_str = hdr["Config"]["relSliceNumber"]
            if rel_str:
                order = [int(a) for a in rel_str.replace("-1", "").replace(" ", "")]
                if len(order) >= n_slices:
                    return order[:n_slices]
        except (KeyError, TypeError, ValueError):
            pass

        return None

    def _extract_position(self, sl: Dict) -> List[float]:
        """Extract slice position (origin) from a slice dict."""
        pos = sl.get("sPosition", {})
        return [
            self._safe_float(pos.get("dSag", 0.0), 0.0),
            self._safe_float(pos.get("dCor", 0.0), 0.0),
            self._safe_float(pos.get("dTra", 0.0), 0.0),
        ]

    def _extract_direction(self, sl: Dict) -> np.ndarray:
        """
        Extract direction matrix from slice normal vector.

        This is a simplified version using the diagonal approach from
        the existing mro.py code. For production use with oblique slices,
        consider using twixtools.geometry.Geometry which uses MDB quaternions.
        """
        direction = -np.eye(3)

        normal = sl.get("sNormal", {})
        if "dTra" in normal:
            val = self._safe_float(normal["dTra"], 0.0)
            if val != 0.0:
                direction[2, 2] = -val
        if "dSag" in normal:
            val = self._safe_float(normal["dSag"], 0.0)
            if val != 0.0:
                direction[0, 0] = val
        if "dCor" in normal:
            val = self._safe_float(normal["dCor"], 0.0)
            if val != 0.0:
                direction[1, 1] = val

        return direction

    def _get_patient_position(self, hdr: Dict) -> Optional[str]:
        """
        Get patient position string.
        Path differs between VB/VD and XA.
        """
        # VB/VD path
        try:
            return hdr["Meas"]["tPatientPosition"]
        except (KeyError, TypeError):
            pass

        # XA path
        try:
            return hdr["Meas"]["sPatPosition"]
        except (KeyError, TypeError):
            pass

        # MeasYaps fallback
        try:
            return hdr["MeasYaps"]["sProtConsistencyInfo"]["tBaselineString"]
        except (KeyError, TypeError):
            pass

        return None

    def __repr__(self):
        try:
            return (
                f"DatFileInfo('{os.path.basename(self.filepath)}', "
                f"platform='{self.platform}', "
                f"syngo='{self.syngo_version}', "
                f"multiraid={self.is_multiraid}, "
                f"raids={self.n_raids})"
            )
        except Exception:
            return f"DatFileInfo('{self.filepath}')"

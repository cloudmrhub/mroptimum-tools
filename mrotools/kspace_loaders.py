"""
K-Space data loaders for different file formats.

Each loader reads signal/noise k-space data and returns a standardized format
so the SNR pipeline is agnostic to the input vendor/file type.

Supported vendors:
    - siemens : Siemens .dat (twixtools)
    - numpy   : .npy / .npz files with orientation metadata in JSON
    - matlab  : .mat files (v5/v7.3) with orientation metadata

Standardized slice dict format (returned by get_signal_kspace):
    {
        "KSpace":    np.ndarray  (freq, phase, coils) or (freq, phase, coils, replicas),
        "spacing":   [dx, dy, dz],
        "origin":    [ox, oy, oz],
        "direction": np.ndarray  3x3,
        "size":      [freq, phase, 1],
        "fov":       [fov_freq, fov_phase, fov_slice],
    }
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
import numpy as np
import os


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------
class KSpaceLoader(ABC):
    """Base class for k-space data loaders."""

    @abstractmethod
    def get_signal_kspace(
        self,
        signal_options: Dict,
        signal: bool = True,
        MR: bool = False,
    ) -> List[Dict]:
        """
        Load signal k-space and return a list of per-slice dicts.

        Args:
            signal_options: The ``signal`` or ``noise`` block from the JSON config.
            signal: True for signal data, False for noise.
            MR: True for multiple-replicas acquisition.

        Returns:
            List of dicts, one per slice. Each dict contains at minimum:
                KSpace, spacing, origin, direction, size, fov.
        """
        ...

    @abstractmethod
    def get_noise_kspace(
        self,
        noise_options: Dict,
        slice_sel: Union[int, str] = "all",
    ) -> Union[List[np.ndarray], np.ndarray]:
        """
        Load noise k-space.

        Args:
            noise_options: The ``noise`` block from the JSON config.
            slice_sel: Slice index or ``'all'``.

        Returns:
            List of numpy arrays (freq, phase, coils) – one per slice –
            or a single array when *slice_sel* is an int.
        """
        ...

    @abstractmethod
    def get_reference_kspace(
        self,
        signal_options: Dict,
        signal_acceleration_realsize: int,
        slice_sel: Union[int, str] = "all",
    ) -> Union[List[np.ndarray], np.ndarray, None]:
        """
        Load reference / autocalibration k-space (e.g. for GRAPPA / SENSE).

        Returns None when not applicable.
        """
        ...

    @abstractmethod
    def get_acceleration_info(
        self,
        signal_options: Dict,
    ) -> tuple:
        """
        Return (acceleration, autocalibration_lines) for SENSE / GRAPPA.

        Returns:
            acceleration: list, e.g. [1, 2]
            acl:           list, e.g. [nan, 24]
        """
        ...


# ---------------------------------------------------------------------------
# Siemens loader  (wraps the existing twixtools-based functions)
# ---------------------------------------------------------------------------
class SiemensLoader(KSpaceLoader):
    """
    Loads k-space from Siemens .dat files via twixtools.

    Uses DatFileInfo for version-aware orientation/acceleration extraction
    (handles VB, VD, VE, XA correctly), and the existing getSiemensKSpace2D
    for raw k-space data extraction.
    """

    def __init__(self):
        # Lazy imports so we don't break at import time if twixtools is absent
        import twixtools  # noqa: F401
        from pynico_eros_montin import pynico as pn
        import cmtools.cmaws as cmaws
        self._twixtools = twixtools
        self._pn = pn
        self._cmaws = cmaws
        self._dat_info_cache = {}  # cache DatFileInfo per filepath

    # -- helpers ------------------------------------------------------------

    def _get_file(self, s, s3=None):
        return self._cmaws.getCMRFile(s, s3)

    def _resolve_filepath(self, signal_options):
        """Resolve the local filepath from signal options."""
        return self._pn.Pathable(self._get_file(signal_options)).getPosition()

    def _get_dat_info(self, filepath):
        """Get or create a cached DatFileInfo for a filepath."""
        if filepath not in self._dat_info_cache:
            from mrotools.dat_version import DatFileInfo
            self._dat_info_cache[filepath] = DatFileInfo(filepath)
        return self._dat_info_cache[filepath]

    def _safe_map_twix(self, filepath):
        """
        Map twix data safely, avoiding geometry and regrid crashes on
        files with missing 'Meas' header key (some XA/older exports).
        Returns the mapped twix data list.

        Reuses raw twix from DatFileInfo if already loaded.
        """
        # Try to reuse raw data from DatFileInfo cache
        dat_info = self._get_dat_info(filepath)
        if dat_info._raw_twix:
            raw = dat_info._raw_twix
        else:
            raw = self._twixtools.read_twix(filepath, verbose=False, parse_geometry=False)

        try:
            return self._twixtools.map_twix(raw, verbose=False)
        except (KeyError, TypeError, ValueError):
            # map_twix crashed (e.g. missing 'Meas' key for regrid calc).
            # Inject a minimal 'Meas' dict so map_twix's regrid calc won't crash
            for meas in raw:
                if isinstance(meas, dict) and 'hdr' in meas:
                    if 'Meas' not in meas['hdr']:
                        meas['hdr']['Meas'] = {}
            return self._twixtools.map_twix(raw, verbose=False)

    def _extract_kspace(self, filepath, raid=0, noise=False, MR=False,
                        aveRepetition=True, slice_sel='all'):
        """
        Extract k-space from a .dat file without triggering twixtools geometry
        crashes.

        Args:
            filepath: Path to .dat file
            raid: Raid index
            noise: If True, extract noise data (keep oversampling)
            MR: If True, extract multiple replicas
            aveRepetition: Average repetitions (ignored if MR=True)
            slice_sel: 'all' or int

        Returns:
            List of arrays (one per slice), or a single array, or error string.
        """
        twix = self._safe_map_twix(filepath)

        try:
            im_array = twix[raid]['image']
        except (KeyError, IndexError):
            if noise:
                try:
                    im_array = twix[raid]['noise']
                except (KeyError, IndexError):
                    raise Exception("Cannot find image or noise data in this file")
            else:
                raise Exception("Cannot find image data in this file")

        im_array.flags['remove_os'] = not noise

        _MR_DIM = 7
        if noise:
            im_array.flags['average']['Rep'] = False
            im_array.flags['average']['Ave'] = False
        else:
            if not MR:
                im_array.flags['average']['Rep'] = aveRepetition
                im_array.flags['average']['Ave'] = True
            else:
                if not im_array.shape[_MR_DIM] > 1:
                    return "No Multiple Replicas Data"
                im_array.flags['average']['Rep'] = False
                im_array.flags['average']['Ave'] = True

        SL_DIM = 11
        if isinstance(slice_sel, str) and slice_sel.lower() == 'all':
            K = []
            for sl in range(im_array.shape[SL_DIM]):
                if MR:
                    K.append(np.transpose(
                        im_array[0, 0, 0, 0, 0, 0, 0, :, 0, 0, 0, sl, 0, :, :, :],
                        [3, 1, 2, 0]))
                else:
                    K.append(np.transpose(
                        im_array[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, sl, 0, :, :, :],
                        [2, 0, 1]))
            return K
        else:
            sl = int(slice_sel)
            if MR:
                return np.transpose(
                    im_array[0, 0, 0, 0, 0, 0, 0, :, 0, 0, 0, sl, 0, :, :, :],
                    [3, 1, 2, 0])
            else:
                return np.transpose(
                    im_array[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, sl, 0, :, :, :],
                    [2, 0, 1])

    # -- public interface ---------------------------------------------------

    def get_signal_kspace(self, signal_options, signal=True, MR=False):
        """
        Load signal k-space with version-aware orientation extraction.

        Strategy:
        - Uses DatFileInfo for orientation metadata (spacing, origin,
          direction, fov) — handles VB/VD/VE/XA header differences.
        - Uses a safe k-space extraction that avoids twixtools geometry
          crashes on XA files.
        """
        filepath = self._resolve_filepath(signal_options)
        dat_info = self._get_dat_info(filepath)

        # Determine signal raid index
        raid = dat_info.signal_raid

        # Extract raw k-space data (safe method that skips parse_geometry)
        K = self._extract_kspace(filepath, raid=raid, noise=False, MR=MR)

        # If MR mode returned an error string, propagate it
        if isinstance(K, str):
            return K

        # Extract orientation from DatFileInfo (version-aware)
        n_kspace_slices = len(K)
        orientations = []
        for i in range(n_kspace_slices):
            try:
                orient = dat_info.orientation(i)
            except (KeyError, IndexError, TypeError):
                # Fallback: use first slice orientation for all
                orient = dat_info.orientation(0)
            orientations.append(orient)

        # Compute actual center-to-center inter-slice distance from header
        # positions.  DatFileInfo returns dThickness which is slice thickness
        # only; any slice gap (distance factor) must be inferred from the
        # actual sPosition values of adjacent slices.
        # Slices may be in interleaved acquisition order — sort by physical
        # position along the slice normal before computing the step.
        slice_normal = np.asarray(orientations[0]["direction"])[:, 2]
        centers = [np.array(o["origin"], dtype=float) for o in orientations]
        if len(centers) > 1:
            projs = sorted([np.dot(c, slice_normal) for c in centers])
            dists = [abs(projs[j+1] - projs[j]) for j in range(len(projs) - 1)]
            actual_slice_spacing = float(np.median(dists))
        else:
            actual_slice_spacing = float(orientations[0]["spacing"][2])

        # Build output: list of per-slice dicts
        slices = []
        for i, kspace in enumerate(K):
            o = orientations[i] if i < len(orientations) else orientations[0]

            # DatFileInfo.orientation() returns sPosition, which is the SLICE
            # CENTER in Siemens PCS.  NIfTI/SimpleITK/DICOM all expect the
            # first-voxel CORNER as origin.  Convert:
            #   corner = center
            #            - (N_readout/2)*sp_readout * readout_dir
            #            - (N_phase/2)  *sp_phase   * phase_dir
            direction = np.asarray(o["direction"])         # 3x3
            readout_dir = direction[:, 0]                  # image x-axis
            phase_dir   = direction[:, 1]                  # image y-axis
            n_readout   = kspace.shape[0]
            n_phase     = kspace.shape[1]
            sp_readout  = o["spacing"][0]
            sp_phase    = o["spacing"][1]
            center      = np.array(o["origin"], dtype=float)
            corner      = (center
                           - (n_readout / 2) * sp_readout * readout_dir
                           - (n_phase   / 2) * sp_phase   * phase_dir)

            spacing = [o["spacing"][0], o["spacing"][1], actual_slice_spacing]
            slices.append({
                "KSpace": kspace,
                "spacing": spacing,
                "origin": corner.tolist(),
                "direction": o["direction"],
                "size": o["size"],
                "fov": o["fov"],
            })

        return slices

    def get_noise_kspace(self, noise_options, slice_sel="all"):
        """
        Load noise k-space.

        For multiraid files (VD/VE/XA), noise is typically in raid 0.
        For VB files or separate noise files, reads from the image data
        with oversampling kept.
        """
        from raider_eros_montin import raider

        filepath = self._resolve_filepath(noise_options)
        opts = noise_options.get("options", noise_options)
        multiraid = opts.get("multiraid", False)

        if multiraid:
            # Multiraid: noise is in raid 0
            return raider.readMultiRaidNoise(filepath, slice=slice_sel, raid=0)
        else:
            # Separate noise file or embedded noise — use safe extraction
            return self._extract_kspace(filepath, raid=0, noise=True, slice_sel=slice_sel)

    def get_reference_kspace(self, signal_options, signal_acceleration_realsize, slice_sel="all"):
        """
        Load reference / ACS k-space for accelerated acquisitions.
        Uses DatFileInfo to determine the correct raid index.
        """
        from mrotools.mro import fixReferenceSiemens

        filepath = self._resolve_filepath(signal_options)
        dat_info = self._get_dat_info(filepath)
        raid = dat_info.signal_raid

        twix = self._safe_map_twix(filepath)

        try:
            r_array = twix[raid]['refscan']
        except (KeyError, IndexError):
            return None

        r_array.flags['remove_os'] = True
        r_array.flags['average']['Rep'] = True
        r_array.flags['average']['Ave'] = True

        SL_DIM = 11
        if isinstance(slice_sel, str) and slice_sel.lower() == 'all':
            slices = []
            for sl in range(r_array.shape[SL_DIM]):
                ref = fixReferenceSiemens(
                    np.transpose(r_array[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, sl, 0, :, :, :], [2, 0, 1]),
                    signal_acceleration_realsize,
                )
                slices.append(ref)
            return slices
        else:
            sl = int(slice_sel)
            return fixReferenceSiemens(
                np.transpose(r_array[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, sl, 0, :, :, :], [2, 0, 1]),
                signal_acceleration_realsize,
            )

    def get_acceleration_info(self, signal_options):
        """
        Get acceleration info using DatFileInfo (version-aware).
        Handles NaN values and different header paths across VB/VD/VE/XA.
        """
        filepath = self._resolve_filepath(signal_options)
        dat_info = self._get_dat_info(filepath)
        return dat_info.acceleration()


# ---------------------------------------------------------------------------
# Numpy loader
# ---------------------------------------------------------------------------
class NumpyLoader(KSpaceLoader):
    """
    Loads k-space from .npy or .npz files.

    Orientation metadata is resolved with the following priority:
        1. Explicit values in the JSON ``"orientation"`` block  (highest)
        2. Arrays embedded inside the ``.npz`` file
        3. Defaults: spacing=[1,1,1], origin=[0,0,0], direction=eye(3)  (lowest)

    This means a bare ``.npy`` file with just the k-space data works fine –
    the output will use 1 mm isotropic spacing, origin at 0, identity direction.

    Supported JSON config block::

        "signal": {
            "type": "file",
            "options": {
                "vendor": "numpy",
                "filename": "/path/to/signal.npy",      # or .npz
                "npz_key": "kspace",                     # key inside .npz (optional, default 'kspace')
                "orientation": {                          # optional – overrides file-embedded values
                    "spacing":   [1.0, 1.0, 5.0],
                    "origin":    [0.0, 0.0, 0.0],
                    "direction": [1,0,0, 0,1,0, 0,0,1],  # row-major 3x3 (9 elements)
                    "fov":       [256.0, 256.0, 50.0]
                }
            }
        }

    .npz files may contain the following optional keys alongside ``kspace``::

        spacing      : 1-D array of length 3  (dx, dy, dz)
        origin       : 1-D array of length 3  (ox, oy, oz)
        direction    : 1-D array of length 9  (row-major 3x3)
        fov          : 1-D array of length 3  (fov_freq, fov_phase, fov_slice)
        acceleration : 1-D array of length 2  (freq_accel, phase_accel)
        acl          : 1-D array of length 2  (freq_acl, phase_acl)
        reference    : complex array  (freq, phase, coils[, slices]) — embedded ACS data

    The numpy k-space array must be shaped as:
        Single-slice:                (freq, phase, coils)
        Multi-slice:                 (freq, phase, coils, slices)
        Multiple-replicas (MR):      (freq, phase, coils, slices, replicas)
                              or     (freq, phase, coils, replicas)  for single-slice MR

    For noise files the same shapes apply (replicas dim is ignored).
    """

    # ----- helpers ---------------------------------------------------------
    @staticmethod
    def _load_array(filepath: str, npz_key: str = "kspace") -> tuple:
        """
        Load a numpy array from .npy or .npz.

        Returns:
            (kspace_array, file_orientation)
            where *file_orientation* is a dict with any orientation arrays
            found inside a .npz file, or an empty dict for .npy files.
        """
        filepath = os.path.expanduser(filepath)
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"Numpy file not found: {filepath}")

        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".npy":
            return np.load(filepath), {}
        elif ext == ".npz":
            data = np.load(filepath)
            # Extract k-space array
            if npz_key in data:
                kspace = data[npz_key]
            else:
                keys = list(data.keys())
                if len(keys) == 0:
                    raise ValueError(f"Empty .npz file: {filepath}")
                kspace = data[keys[0]]

            # Extract orientation + metadata arrays if present
            file_orient = {}
            for key in ("spacing", "origin", "direction", "fov",
                        "acceleration", "acl"):
                if key in data:
                    file_orient[key] = data[key].tolist()

            return kspace, file_orient
        else:
            raise ValueError(f"Unsupported numpy file extension: {ext}")

    @staticmethod
    def _parse_orientation(opts: Dict, file_orient: Optional[Dict] = None) -> Dict:
        """
        Resolve orientation with priority: JSON > file-embedded > defaults.

        Args:
            opts: The ``options`` dict from the JSON config.
            file_orient: Orientation dict extracted from the .npz file
                         (as returned by ``_load_array``).

        Returns:
            Dict with ``spacing``, ``origin``, ``direction`` (3x3 ndarray),
            and ``fov`` (list or None).
        """
        if file_orient is None:
            file_orient = {}

        # Defaults:  1 mm iso, origin at 0, identity direction
        DEFAULTS = {
            "spacing":   [1.0, 1.0, 1.0],
            "origin":    [0.0, 0.0, 0.0],
            "direction": [1, 0, 0, 0, 1, 0, 0, 0, 1],
            "fov":       None,
        }

        json_orient = opts.get("orientation", {})

        def _resolve(key):
            """Pick the first non-None source."""
            if key in json_orient:
                return json_orient[key]
            if key in file_orient:
                return file_orient[key]
            return DEFAULTS[key]

        spacing = _resolve("spacing")
        origin = _resolve("origin")
        fov = _resolve("fov")

        direction_flat = _resolve("direction")
        direction = np.array(direction_flat, dtype=float).reshape(3, 3)

        return {
            "spacing": spacing,
            "origin": origin,
            "direction": direction,
            "fov": fov,
        }

    # ----- public interface ------------------------------------------------
    def get_signal_kspace(self, signal_options, signal=True, MR=False):
        opts = signal_options["options"]
        filepath = opts["filename"]
        npz_key = opts.get("npz_key", "kspace")

        arr, file_orient = self._load_array(filepath, npz_key)
        orient = self._parse_orientation(opts, file_orient)

        # Determine shape convention
        # 3-D: (freq, phase, coils)            -> single slice
        # 4-D: (freq, phase, coils, slices)    -> multi-slice  (or single-slice MR)
        # 5-D: (freq, phase, coils, slices, replicas) -> multi-slice MR
        if arr.ndim == 3:
            # single slice: (freq, phase, coils)
            slices_data = [arr]
        elif arr.ndim == 4:
            if MR:
                # single-slice MR: (freq, phase, coils, replicas)
                slices_data = [arr]
            else:
                # multi-slice: (freq, phase, coils, slices)
                slices_data = [arr[:, :, :, s] for s in range(arr.shape[3])]
        elif arr.ndim == 5:
            # multi-slice MR: (freq, phase, coils, slices, replicas)
            slices_data = [arr[:, :, :, s, :] for s in range(arr.shape[3])]
        else:
            raise ValueError(
                f"Unexpected numpy array ndim={arr.ndim}. "
                "Expected 3 (freq,phase,coils), 4 (…,slices), or 5 (…,slices,replicas)."
            )

        n_slices = len(slices_data)
        freq, phase = slices_data[0].shape[0], slices_data[0].shape[1]

        # Build per-slice fov
        spacing = orient["spacing"]
        fov = orient["fov"]
        if fov is None:
            fov = [freq * spacing[0], phase * spacing[1], n_slices * spacing[2]]

        result = []
        for s_idx, ksp in enumerate(slices_data):
            # Per-slice origin offset along slice direction (3rd col of direction)
            slice_offset = np.array(orient["direction"][:, 2]) * spacing[2] * s_idx
            slice_origin = [
                orient["origin"][0] + slice_offset[0],
                orient["origin"][1] + slice_offset[1],
                orient["origin"][2] + slice_offset[2],
            ]

            result.append({
                "KSpace": ksp,
                "spacing": spacing,
                "origin": slice_origin,
                "direction": orient["direction"],
                "size": [freq, phase, 1],
                "fov": fov,
            })

        return result

    def get_noise_kspace(self, noise_options, slice_sel="all"):
        opts = noise_options["options"]
        filepath = opts["filename"]
        npz_key = opts.get("npz_key", "kspace")

        arr, _ = self._load_array(filepath, npz_key)

        # Noise is always (freq, phase, coils) or (freq, phase, coils, slices)
        if arr.ndim == 3:
            slices = [arr]
        elif arr.ndim >= 4:
            slices = [arr[:, :, :, s] for s in range(arr.shape[3])]
        else:
            raise ValueError(f"Noise array ndim={arr.ndim}, expected >= 3.")

        if isinstance(slice_sel, str) and slice_sel.lower() == "all":
            return slices
        else:
            return slices[int(slice_sel)]

    def get_acceleration_info(self, signal_options):
        """
        Resolve acceleration info with priority: JSON > file-embedded > defaults.

        JSON keys::

            "accelerations": [1, 2],
            "acl": [null, 24]

        .npz keys: ``acceleration``, ``acl`` (1-D arrays of length 2).

        Returns defaults of [1,1] / [nan,nan] when not supplied.
        """
        opts = signal_options.get("options", signal_options)

        # Load file-embedded metadata if available
        file_meta = {}
        filepath = opts.get("filename")
        if filepath and os.path.isfile(os.path.expanduser(filepath)):
            ext = os.path.splitext(filepath)[1].lower()
            if ext == ".npz":
                data = np.load(os.path.expanduser(filepath))
                if "acceleration" in data:
                    file_meta["acceleration"] = data["acceleration"].tolist()
                if "acl" in data:
                    file_meta["acl"] = data["acl"].tolist()

        # Priority: JSON > file > defaults
        acceleration = opts.get("accelerations",
                                file_meta.get("acceleration", [1, 1]))
        acl = opts.get("acl",
                       file_meta.get("acl", [np.nan, np.nan]))
        acl = [np.nan if v is None or v == 0 else v for v in acl]
        return acceleration, acl

    def get_reference_kspace(self, signal_options, signal_acceleration_realsize, slice_sel="all"):
        """
        Load reference / ACS data.

        Supports:
        1. Separate file via ``reference_filename`` in JSON
        2. Embedded ``reference`` key inside the signal ``.npz`` file
        """
        opts = signal_options["options"]

        # 1. Separate file
        ref_path = opts.get("reference_filename", None)
        if ref_path is not None:
            npz_key = opts.get("npz_key", "kspace")
            arr, _ = self._load_array(ref_path, npz_key)
        else:
            # 2. Embedded in signal file
            filepath = opts.get("filename")
            if filepath is None:
                return None
            ext = os.path.splitext(filepath)[1].lower()
            if ext != ".npz":
                return None
            data = np.load(os.path.expanduser(filepath))
            if "reference" not in data:
                return None
            arr = data["reference"]

        if arr.ndim == 3:
            slices = [arr]
        elif arr.ndim >= 4:
            slices = [arr[:, :, :, s] for s in range(arr.shape[3])]
        else:
            raise ValueError(f"Reference array ndim={arr.ndim}, expected >= 3.")

        if isinstance(slice_sel, str) and slice_sel.lower() == "all":
            return slices
        return slices[int(slice_sel)]


# ---------------------------------------------------------------------------
# MATLAB loader
# ---------------------------------------------------------------------------
class MatlabLoader(KSpaceLoader):
    """
    Loads k-space from MATLAB ``.mat`` files (v5 via scipy, v7.3/HDF5 via h5py).

    Orientation metadata is resolved with the following priority:
        1. Explicit values in the JSON ``"orientation"`` block  (highest)
        2. Variables embedded inside the ``.mat`` file
        3. Defaults: spacing=[1,1,1], origin=[0,0,0], direction=eye(3)  (lowest)

    Required ``.mat`` variable:
        kspace    : complex array shaped (freq, phase, coils[, slices[, replicas]])

    Optional ``.mat`` variables for orientation:
        spacing   : 1-D array of length 3  (dx, dy, dz)
        origin    : 1-D array of length 3  (ox, oy, oz)
        direction : 1-D array of length 9  (row-major 3x3)
        fov       : 1-D array of length 3  (fov_freq, fov_phase, fov_slice)

    Supported JSON config block::

        "signal": {
            "type": "file",
            "options": {
                "vendor": "matlab",
                "filename": "/path/to/signal.mat",
                "mat_key": "kspace",
                "orientation": { ... }
            }
        }
    """

    # ----- helpers ---------------------------------------------------------
    @staticmethod
    def _load_mat(filepath: str, mat_key: str = "kspace") -> tuple:
        """
        Load a k-space array and orientation from a .mat file.

        Supports both MATLAB v5 (scipy.io.loadmat) and v7.3/HDF5 (h5py).

        Returns:
            (kspace_array, file_orientation_dict)
        """
        filepath = os.path.expanduser(filepath)
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"MATLAB file not found: {filepath}")

        kspace = None
        file_orient = {}

        # Try scipy first (v5 / v7)
        try:
            import scipy.io as sio
            mat = sio.loadmat(filepath)
            # scipy adds meta keys like __header__, filter them
            user_keys = [k for k in mat.keys() if not k.startswith("__")]
            if mat_key in mat:
                kspace = np.asarray(mat[mat_key])
            elif user_keys:
                kspace = np.asarray(mat[user_keys[0]])
            else:
                raise KeyError("no user variables found")

            # Orientation + metadata
            for okey in ("spacing", "origin", "direction", "fov",
                         "acceleration", "acl"):
                if okey in mat:
                    file_orient[okey] = np.asarray(mat[okey]).flatten().tolist()

        except NotImplementedError:
            # v7.3 HDF5 – fall through to h5py
            import h5py
            with h5py.File(filepath, "r") as f:
                keys = list(f.keys())
                if mat_key in f:
                    ds = f[mat_key]
                elif keys:
                    ds = f[keys[0]]
                else:
                    raise ValueError(f"Empty .mat (HDF5) file: {filepath}")

                # h5py stores MATLAB arrays transposed (column-major)
                kspace = np.asarray(ds).T
                if np.issubdtype(kspace.dtype, np.floating):
                    # Check for paired real/imag stored as last dim
                    pass  # keep as-is; user must supply complex
                # If h5py reads real + imag as a compound type, recombine
                if kspace.dtype.names and "real" in kspace.dtype.names:
                    kspace = kspace["real"] + 1j * kspace["imag"]

                for okey in ("spacing", "origin", "direction", "fov",
                             "acceleration", "acl"):
                    if okey in f:
                        file_orient[okey] = np.asarray(f[okey]).flatten().tolist()

        return kspace, file_orient

    # Reuse the same orientation resolver as NumpyLoader
    _parse_orientation = NumpyLoader.__dict__["_parse_orientation"]

    # ----- public interface ------------------------------------------------
    def get_signal_kspace(self, signal_options, signal=True, MR=False):
        opts = signal_options["options"]
        filepath = opts["filename"]
        mat_key = opts.get("mat_key", "kspace")

        arr, file_orient = self._load_mat(filepath, mat_key)
        orient = self._parse_orientation(opts, file_orient)

        # Shape conventions identical to NumpyLoader
        if arr.ndim == 3:
            slices_data = [arr]
        elif arr.ndim == 4:
            if MR:
                slices_data = [arr]
            else:
                slices_data = [arr[:, :, :, s] for s in range(arr.shape[3])]
        elif arr.ndim == 5:
            slices_data = [arr[:, :, :, s, :] for s in range(arr.shape[3])]
        else:
            raise ValueError(
                f"Unexpected MATLAB array ndim={arr.ndim}. "
                "Expected 3 (freq,phase,coils), 4 (…,slices), or 5 (…,slices,replicas)."
            )

        n_slices = len(slices_data)
        freq, phase = slices_data[0].shape[0], slices_data[0].shape[1]

        spacing = orient["spacing"]
        fov = orient["fov"]
        if fov is None:
            fov = [freq * spacing[0], phase * spacing[1], n_slices * spacing[2]]

        result = []
        for s_idx, ksp in enumerate(slices_data):
            slice_offset = np.array(orient["direction"][:, 2]) * spacing[2] * s_idx
            slice_origin = [
                orient["origin"][0] + slice_offset[0],
                orient["origin"][1] + slice_offset[1],
                orient["origin"][2] + slice_offset[2],
            ]
            result.append({
                "KSpace": ksp,
                "spacing": spacing,
                "origin": slice_origin,
                "direction": orient["direction"],
                "size": [freq, phase, 1],
                "fov": fov,
            })
        return result

    def get_noise_kspace(self, noise_options, slice_sel="all"):
        opts = noise_options["options"]
        filepath = opts["filename"]
        mat_key = opts.get("mat_key", "kspace")

        arr, _ = self._load_mat(filepath, mat_key)

        if arr.ndim == 3:
            slices = [arr]
        elif arr.ndim >= 4:
            slices = [arr[:, :, :, s] for s in range(arr.shape[3])]
        else:
            raise ValueError(f"Noise array ndim={arr.ndim}, expected >= 3.")

        if isinstance(slice_sel, str) and slice_sel.lower() == "all":
            return slices
        return slices[int(slice_sel)]

    def get_reference_kspace(self, signal_options, signal_acceleration_realsize, slice_sel="all"):
        """Load reference / ACS data from a separate file or embedded 'reference' variable."""
        opts = signal_options["options"]

        # 1. Separate file
        ref_path = opts.get("reference_filename", None)
        if ref_path is not None:
            mat_key = opts.get("mat_key", "kspace")
            arr, _ = self._load_mat(ref_path, mat_key)
        else:
            # 2. Embedded 'reference' variable in signal file
            filepath = opts.get("filename")
            if filepath is None:
                return None
            try:
                import scipy.io as sio
                mat = sio.loadmat(os.path.expanduser(filepath))
                if "reference" not in mat:
                    return None
                arr = np.asarray(mat["reference"])
            except (NotImplementedError, Exception):
                try:
                    import h5py
                    with h5py.File(os.path.expanduser(filepath), "r") as f:
                        if "reference" not in f:
                            return None
                        arr = np.asarray(f["reference"]).T
                except Exception:
                    return None

        if arr.ndim == 3:
            slices = [arr]
        elif arr.ndim >= 4:
            slices = [arr[:, :, :, s] for s in range(arr.shape[3])]
        else:
            raise ValueError(f"Reference array ndim={arr.ndim}, expected >= 3.")

        if isinstance(slice_sel, str) and slice_sel.lower() == "all":
            return slices
        return slices[int(slice_sel)]

    def get_acceleration_info(self, signal_options):
        """Resolve acceleration info with priority: JSON > file-embedded > defaults."""
        opts = signal_options.get("options", signal_options)

        # Load file-embedded metadata
        file_meta = {}
        filepath = opts.get("filename")
        if filepath and os.path.isfile(os.path.expanduser(filepath)):
            try:
                import scipy.io as sio
                mat = sio.loadmat(os.path.expanduser(filepath))
                for key in ("acceleration", "acl"):
                    if key in mat:
                        file_meta[key] = np.asarray(mat[key]).flatten().tolist()
            except (NotImplementedError, Exception):
                try:
                    import h5py
                    with h5py.File(os.path.expanduser(filepath), "r") as f:
                        for key in ("acceleration", "acl"):
                            if key in f:
                                file_meta[key] = np.asarray(f[key]).flatten().tolist()
                except Exception:
                    pass

        # Priority: JSON > file > defaults
        acceleration = opts.get("accelerations",
                                file_meta.get("acceleration", [1, 1]))
        acl = opts.get("acl",
                       file_meta.get("acl", [np.nan, np.nan]))
        acl = [np.nan if v is None or v == 0 else v for v in acl]
        return acceleration, acl


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
_LOADERS = {
    "siemens": SiemensLoader,
    "numpy": NumpyLoader,
    "matlab": MatlabLoader,
}


def get_kspace_loader(vendor: str) -> KSpaceLoader:
    """
    Return the appropriate KSpaceLoader for the given vendor string.

    Args:
        vendor: One of 'siemens', 'numpy' (case-insensitive).

    Raises:
        ValueError: If the vendor is not supported.
    """
    key = vendor.strip().lower()
    if key not in _LOADERS:
        supported = ", ".join(sorted(_LOADERS.keys()))
        raise ValueError(
            f"Unsupported vendor '{vendor}'. Supported: {supported}"
        )
    return _LOADERS[key]()

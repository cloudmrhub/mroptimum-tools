"""
ISMRMRD (.h5) → NumPy (.npz) converter.

Reads an ISMRMRD raw data file and exports all the information needed by
the MR Optimum numpy loader into self-contained .npz files.

The ISMRMRD format is a vendor-neutral standard for MR raw data:
    https://ismrmrd.github.io

Output files (one set per conversion):
    signal.npz   — signal k-space + orientation + acceleration metadata
    noise.npz    — noise k-space  (if noise acquisitions are present)
    reference.npz— reference / ACS k-space (only for accelerated acquisitions)

Each .npz contains:
    kspace      : complex array (freq, phase, coils[, slices])
    spacing     : [dx, dy, dz]
    origin      : [ox, oy, oz]         (physical center of first slice)
    direction   : 9 elements, row-major 3x3
    fov         : [fov_freq, fov_phase, fov_slice]
    acceleration: [accel_freq, accel_phase]
    acl         : [acl_freq, acl_phase]   (autocalibration lines)

Install dependency:
    conda run -n mro pip install ismrmrd

Usage:
    conda run -n mro python tools/ismrmrd2numpy.py \\
        -i /path/to/data.h5 \\
        -o /path/to/output_dir/
"""

import argparse
import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# ISMRMRD XML header helpers
# ---------------------------------------------------------------------------

def _parse_xml_header(dataset):
    """
    Parse ISMRMRD XML header into a plain dict-like object.

    Returns:
        header: ismrmrd header object
    """
    import ismrmrd.xsd
    return ismrmrd.xsd.CreateFromDocument(dataset.read_xml_header())


def extract_encoding_info(header):
    """
    Extract encoding limits, trajectory, FOV and matrix size from header.

    Returns dict with:
        encoded_size : (RO, E1, E2)
        recon_size   : (RO, E1, E2)
        fov_mm       : [fov_RO, fov_E1, fov_E2]
        e1_center    : centre PE line
        e2_center    : centre partition (or 0 for 2-D)
        n_slices     : number of slices
        trajectory   : string (e.g. 'cartesian')
    """
    enc = header.encoding[0]

    encoded_size = (
        int(enc.encodedSpace.matrixSize.x),
        int(enc.encodedSpace.matrixSize.y),
        int(enc.encodedSpace.matrixSize.z),
    )
    recon_size = (
        int(enc.reconSpace.matrixSize.x),
        int(enc.reconSpace.matrixSize.y),
        int(enc.reconSpace.matrixSize.z),
    )
    fov_mm = [
        float(enc.encodedSpace.fieldOfView_mm.x),
        float(enc.encodedSpace.fieldOfView_mm.y),
        float(enc.encodedSpace.fieldOfView_mm.z),
    ]

    lim = enc.encodingLimits
    e1_min  = int(lim.kspace_encoding_step_1.minimum)
    e1_max  = int(lim.kspace_encoding_step_1.maximum)
    e1_ctr  = int(lim.kspace_encoding_step_1.center)

    e2_min  = int(lim.kspace_encoding_step_2.minimum) if lim.kspace_encoding_step_2 else 0
    e2_max  = int(lim.kspace_encoding_step_2.maximum) if lim.kspace_encoding_step_2 else 0
    e2_ctr  = int(lim.kspace_encoding_step_2.center)  if lim.kspace_encoding_step_2 else 0

    n_slices = 1
    if lim.slice:
        n_slices = int(lim.slice.maximum) - int(lim.slice.minimum) + 1

    trajectory = str(enc.trajectory) if enc.trajectory else "cartesian"

    return {
        "encoded_size": encoded_size,
        "recon_size": recon_size,
        "fov_mm": fov_mm,
        "e1_range": (e1_min, e1_max, e1_ctr),
        "e2_range": (e2_min, e2_max, e2_ctr),
        "n_slices": n_slices,
        "trajectory": trajectory,
    }


def extract_acceleration_info(header):
    """
    Extract parallel imaging acceleration and calibration mode from header.

    Returns:
        acceleration : [accel_E1, accel_E2]
        acl          : [acl_E1, acl_E2]  (NaN if not applicable)
        calibration  : str ('embedded', 'separate', 'external', 'other')
    """
    enc = header.encoding[0]

    acceleration = [1, 1]
    acl = [np.nan, np.nan]
    calibration = "none"

    if enc.parallelImaging:
        pi = enc.parallelImaging
        af = pi.accelerationFactor
        if af:
            acceleration = [
                int(af.kspace_encoding_step_1),
                int(af.kspace_encoding_step_2),
            ]
        if pi.calibrationMode:
            calibration = str(pi.calibrationMode)

    return acceleration, acl, calibration


# ---------------------------------------------------------------------------
# Orientation helpers
# ---------------------------------------------------------------------------

def extract_orientation_from_acquisition(acq):
    """
    Extract position and direction cosines from a single acquisition.

    ISMRMRD stores per-readout:
        acq.position  : [x, y, z]  physical centre of the readout line
        acq.read_dir  : [x, y, z]  frequency-encode direction cosine
        acq.phase_dir : [x, y, z]  phase-encode direction cosine
        acq.slice_dir : [x, y, z]  slice direction cosine

    Returns:
        origin    : [x, y, z]
        direction : 3x3 ndarray  [read_dir; phase_dir; slice_dir]
    """
    origin = list(acq.position)
    direction = np.array([
        list(acq.read_dir),
        list(acq.phase_dir),
        list(acq.slice_dir),
    ], dtype=float)
    return origin, direction


# ---------------------------------------------------------------------------
# K-space extraction
# ---------------------------------------------------------------------------

def _make_kspace_buffer(encoded_size, n_coils, n_slices, dtype=np.complex64):
    """Allocate a (RO, E1, coils, slices) buffer filled with zeros."""
    RO, E1, _ = encoded_size
    return np.zeros((RO, E1, n_coils, n_slices), dtype=dtype)


def extract_kspace(dataset, enc_info, calibration):
    """
    Separate acquisitions into signal, noise, and reference k-space.

    Args:
        dataset   : open ismrmrd.Dataset
        enc_info  : dict returned by extract_encoding_info
        calibration: calibration mode string ('embedded', 'separate', …)

    Returns:
        signal_kspace    : np.ndarray (RO, E1, coils[, slices])
        noise_kspace     : np.ndarray or None
        reference_kspace : np.ndarray or None
        acl              : number of calibration lines found (int)
        first_acq        : first non-noise acquisition (for orientation)
    """
    import ismrmrd

    n_acq = dataset.number_of_acquisitions()
    encoded_size = enc_info["encoded_size"]
    e1_min, e1_max, e1_ctr = enc_info["e1_range"]
    n_slices = enc_info["n_slices"]
    n_e1 = e1_max - e1_min + 1

    # Will be determined from first acquisition
    n_coils = None

    # Accumulators — we don't know coil count until we see the first acq
    signal_lines   = {}   # (slice, e1) -> array
    noise_lines    = []
    ref_lines      = {}   # (slice, e1) -> array

    first_signal_acq = None

    print(f"  Scanning {n_acq} acquisitions...")
    for i in range(n_acq):
        acq = dataset.read_acquisition(i)

        # Determine acquisition type via flags
        is_noise = acq.is_flag_set(ismrmrd.ACQ_IS_NOISE_MEASUREMENT)
        is_ref   = acq.is_flag_set(ismrmrd.ACQ_IS_PARALLEL_CALIBRATION)
        is_last  = acq.is_flag_set(ismrmrd.ACQ_LAST_IN_MEASUREMENT)

        # Data shape: (channels, samples) → transpose to (samples, channels)
        data = acq.data.T  # (samples, channels)

        if n_coils is None:
            n_coils = data.shape[1]

        if is_noise:
            noise_lines.append(data)
            continue

        if first_signal_acq is None and not is_ref:
            first_signal_acq = acq

        e1  = acq.idx.kspace_encode_step_1
        sl  = acq.idx.slice if acq.idx.slice is not None else 0

        if is_ref:
            ref_lines[(sl, e1)] = data
        else:
            signal_lines[(sl, e1)] = data

    if n_coils is None:
        raise RuntimeError("No acquisitions found in file.")

    # ── Assemble signal k-space ───────────────────────────────────────────
    signal_kspace = np.zeros(
        (encoded_size[0], n_e1, n_coils, n_slices), dtype=np.complex64
    )
    for (sl, e1), data in signal_lines.items():
        e1_idx = e1 - e1_min
        if 0 <= e1_idx < n_e1 and 0 <= sl < n_slices:
            signal_kspace[:, e1_idx, :, sl] = data

    # ── Assemble noise ────────────────────────────────────────────────────
    # noise_lines entries: (samples, coils) each
    # Final shape: (total_samples, 1, coils) → (freq, phase=1, coils)
    noise_kspace = None
    if noise_lines:
        noise_kspace = np.concatenate(noise_lines, axis=0)  # (total_samples, coils)
        noise_kspace = noise_kspace[:, np.newaxis, :]        # (total_samples, 1, coils)

    # ── Assemble reference k-space ────────────────────────────────────────
    reference_kspace = None
    acl_lines = 0
    if ref_lines:
        reference_kspace = np.zeros(
            (encoded_size[0], n_e1, n_coils, n_slices), dtype=np.complex64
        )
        for (sl, e1), data in ref_lines.items():
            e1_idx = e1 - e1_min
            if 0 <= e1_idx < n_e1 and 0 <= sl < n_slices:
                reference_kspace[:, e1_idx, :, sl] = data
        acl_lines = len({e1 for (_, e1) in ref_lines.keys()})

    # ── Drop slice dim if single slice ────────────────────────────────────
    if n_slices == 1:
        signal_kspace = signal_kspace[:, :, :, 0]
        if reference_kspace is not None:
            reference_kspace = reference_kspace[:, :, :, 0]

    return signal_kspace, noise_kspace, reference_kspace, acl_lines, first_signal_acq


# ---------------------------------------------------------------------------
# Main conversion
# ---------------------------------------------------------------------------

def convert(input_path, output_dir, generate_json=True):
    """
    Convert an ISMRMRD .h5 file to .npz files.

    Args:
        input_path   : Path to the ISMRMRD .h5 file.
        output_dir   : Output directory for .npz files.
        generate_json: If True, write a ready-to-use MR Optimum JSON config.
    """
    try:
        import ismrmrd
    except ImportError:
        raise ImportError(
            "ismrmrd package not found. Install it with:\n"
            "  conda run -n mro pip install ismrmrd"
        )

    os.makedirs(output_dir, exist_ok=True)

    print(f"Reading: {input_path}")
    dataset = ismrmrd.Dataset(input_path, "dataset", create_if_needed=False)

    # ── 1. Parse XML header ───────────────────────────────────────────────
    header = _parse_xml_header(dataset)
    enc_info = extract_encoding_info(header)
    acceleration, acl, calibration = extract_acceleration_info(header)

    print(f"  encoded size : {enc_info['encoded_size']}")
    print(f"  slices       : {enc_info['n_slices']}")
    print(f"  trajectory   : {enc_info['trajectory']}")
    print(f"  acceleration : {acceleration}")
    print(f"  calibration  : {calibration}")

    # ── 2. Extract k-space ────────────────────────────────────────────────
    signal_kspace, noise_kspace, reference_kspace, acl_lines, first_acq = \
        extract_kspace(dataset, enc_info, calibration)

    print(f"  signal shape : {signal_kspace.shape}  dtype={signal_kspace.dtype}")

    # ── 3. Orientation from first acquisition ─────────────────────────────
    origin, direction = (None, None)
    if first_acq is not None:
        origin, direction = extract_orientation_from_acquisition(first_acq)

    fov = enc_info["fov_mm"]
    encoded_size = enc_info["encoded_size"]
    spacing = [
        fov[0] / encoded_size[0],
        fov[1] / encoded_size[1],
        fov[2] if encoded_size[2] <= 1 else fov[2] / encoded_size[2],
    ]

    # Update ACL from embedded calibration lines if not in header
    if acl_lines > 0:
        acl = [np.nan, acl_lines]

    print(f"  spacing      : {spacing}")
    print(f"  fov          : {fov}")
    print(f"  acl          : {acl}")

    # ── 4. Save signal ────────────────────────────────────────────────────
    sig_path = os.path.join(output_dir, "signal.npz")
    _save_npz(sig_path, signal_kspace, spacing, origin, direction, fov,
              acceleration, acl)

    # ── 5. Save noise ─────────────────────────────────────────────────────
    noi_path = None
    if noise_kspace is not None:
        noi_path = os.path.join(output_dir, "noise.npz")
        np.savez_compressed(noi_path, kspace=noise_kspace)
        print(f"  Saved noise : {noi_path}  shape={noise_kspace.shape}")

    # ── 6. Save reference ─────────────────────────────────────────────────
    ref_path = None
    if reference_kspace is not None:
        ref_path = os.path.join(output_dir, "reference.npz")
        np.savez_compressed(ref_path, kspace=reference_kspace)
        print(f"  Saved ref   : {ref_path}  shape={reference_kspace.shape}")

    dataset.close()

    # ── 7. Generate JSON config ───────────────────────────────────────────
    if generate_json:
        config = _build_json_config(
            sig_path=os.path.abspath(sig_path),
            noi_path=os.path.abspath(noi_path) if noi_path else None,
            ref_path=os.path.abspath(ref_path) if ref_path else None,
            acceleration=acceleration,
            acl=acl,
        )
        config_path = os.path.join(output_dir, "config_numpy.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"\nGenerated JSON config: {config_path}")

    print("\nDone!")


def _save_npz(filepath, kspace, spacing, origin, direction, fov,
              acceleration=None, acl=None):
    """Save k-space + metadata into a single .npz file."""
    data = {"kspace": kspace}

    if spacing is not None:
        data["spacing"] = np.array(spacing, dtype=np.float64)
    if origin is not None:
        data["origin"] = np.array(origin, dtype=np.float64)
    if direction is not None:
        data["direction"] = np.array(direction, dtype=np.float64).flatten()
    if fov is not None:
        data["fov"] = np.array(fov, dtype=np.float64)
    if acceleration is not None:
        data["acceleration"] = np.array(acceleration, dtype=np.float64)
    if acl is not None:
        data["acl"] = np.array(
            [0.0 if (v is None or (isinstance(v, float) and np.isnan(v))) else v
             for v in acl],
            dtype=np.float64,
        )

    np.savez_compressed(filepath, **data)
    print(f"  Saved signal: {filepath}  shape={kspace.shape}  dtype={kspace.dtype}")


def _build_json_config(sig_path, noi_path=None, ref_path=None,
                       acceleration=None, acl=None):
    """Build a ready-to-use MR Optimum JSON config."""
    signal_opts = {
        "type": "local",
        "vendor": "numpy",
        "filename": sig_path,
    }
    if ref_path:
        signal_opts["reference_filename"] = ref_path

    recon_opts = {
        "signal": {"type": "file", "options": signal_opts},
    }
    if noi_path:
        recon_opts["noise"] = {
            "type": "file",
            "options": {
                "type": "local",
                "vendor": "numpy",
                "filename": noi_path,
            },
        }

    has_accel = acceleration is not None and any(a > 1 for a in acceleration)
    if has_accel:
        recon_opts["accelerations"] = acceleration
        recon_opts["acl"] = [None if (v is None or np.isnan(v)) else int(v)
                             for v in acl]
        recon_opts["decimate"] = False
        recon_opts["sensitivityMap"] = {
            "type": "sensitivityMap",
            "id": 1,
            "name": "inner",
            "options": {"sensitivityMapMethod": "inner", "mask": "no"},
        }
        recon_name = "Sense"
    else:
        recon_name = "RSS"

    return {
        "version": "v0",
        "acquisition": 2,
        "type": "SNR",
        "id": 0,
        "name": "AC",
        "options": {
            "reconstructor": {
                "type": "recon",
                "name": recon_name,
                "options": recon_opts,
            }
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="ismrmrd2numpy",
        description="Convert ISMRMRD (.h5) raw data to NumPy .npz files for MR Optimum",
    )
    parser.add_argument(
        "-i", "--input", required=True, type=str,
        help="Path to the ISMRMRD .h5 file",
    )
    parser.add_argument(
        "-o", "--output", required=True, type=str,
        help="Output directory for .npz files",
    )
    parser.add_argument(
        "--no-json", action="store_true",
        help="Skip JSON config generation",
    )
    args = parser.parse_args()

    convert(
        input_path=args.input,
        output_dir=args.output,
        generate_json=not args.no_json,
    )

"""
Siemens .dat → NumPy (.npz) converter.

Reads a Siemens raw data file and exports all the information needed by
the MR Optimum numpy loader into self-contained .npz files.

Output files (one set per conversion):
    signal.npz   — signal k-space + orientation + acceleration metadata
    noise.npz    — noise k-space
    reference.npz— reference / ACS k-space (only for accelerated acquisitions)

Each .npz contains:
    kspace      : complex array (freq, phase, coils[, slices])
    spacing     : [dx, dy, dz]
    origin      : [ox, oy, oz]         (of the first slice)
    direction   : 9 elements, row-major 3x3
    fov         : [fov_freq, fov_phase, fov_slice]
    acceleration: [accel_freq, accel_phase]
    acl         : [acl_freq, acl_phase]   (autocalibration lines)

Usage:
    conda run -n mro python tools/dat2numpy.py \\
        -i /path/to/signal.dat \\
        -o /path/to/output_dir/ \\
        --multiraid           # if noise is embedded in the signal file

    conda run -n mro python tools/dat2numpy.py \\
        -i /path/to/signal.dat \\
        --noise /path/to/noise.dat \\
        -o /path/to/output_dir/
"""

import argparse
import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pynico_eros_montin import pynico as pn
import twixtools
from raider_eros_montin import raider


def extract_orientation(twix_data, raid):
    """
    Extract per-slice orientation from twix headers.

    Returns:
        list of dicts, one per slice, each with:
            spacing, origin, direction (3x3), fov, size
    """
    H = twix_data[raid]["hdr"]
    SA = H["Phoenix"]["sSliceArray"]
    C = H["Config"]
    KS = [int(C["BaseResolution"]), int(C["PhaseEncodingLines"])]
    SL = SA["asSlice"]

    try:
        SLORDER = [int(a) for a in C["relSliceNumber"].replace("-1", "").replace(" ", "")]
    except Exception:
        SLORDER = list(range(len(SL)))

    slices_info = []
    for j in range(len(SLORDER)):
        t = SLORDER.index(j) if j < len(SLORDER) else j
        sl = SL[t]
        slp = SL[t].get("sPosition", {})

        try:
            origin = [slp["dSag"], slp["dCor"], slp["dTra"]]
        except KeyError:
            origin = [0.0, 0.0, 0.0]

        spacing = [
            sl["dReadoutFOV"] / KS[0],
            sl["dPhaseFOV"] / KS[1],
            sl["dThickness"],
        ]
        fov = [sl["dReadoutFOV"], sl["dPhaseFOV"], sl["dThickness"] * SA["lSize"]]

        direction = -np.eye(3)
        if "dTra" in sl.get("sNormal", {}):
            direction[2, 2] = -sl["sNormal"]["dTra"]
        if "dSag" in sl.get("sNormal", {}):
            direction[0, 0] = sl["sNormal"]["dSag"]
        if "dCor" in sl.get("sNormal", {}):
            direction[1, 1] = sl["sNormal"]["dCor"]

        slices_info.append({
            "spacing": spacing,
            "origin": origin,
            "direction": direction,
            "fov": fov,
            "size": [*KS, 1],
        })

    return slices_info


def extract_acceleration(twix_data, raid):
    """
    Extract acceleration and autocalibration lines from twix headers.

    Returns:
        acceleration: [freq_accel, phase_accel]
        acl:          [freq_acl, phase_acl]
    """
    H = twix_data[raid]["hdr"]
    try:
        iPat = H["MeasYaps"]["sPat"]
        acceleration = [1, int(iPat["lAccelFactPE"])]
        acl = [np.nan, int(iPat["lRefLinesPE"])]
    except (KeyError, TypeError):
        acceleration = [1, 1]
        acl = [np.nan, np.nan]
    return acceleration, acl


def extract_signal_kspace(dat_path, raid, MR=False):
    """
    Extract signal k-space from a Siemens .dat file.

    Returns:
        list of arrays, one per slice. Each is (freq, phase, coils)
        or (freq, phase, coils, replicas) for MR.
    """
    twix = twixtools.map_twix(dat_path)
    im_array = twix[raid]["image"]
    im_array.flags["remove_os"] = True

    if not MR:
        im_array.flags["average"]["Rep"] = True
        im_array.flags["average"]["Ave"] = True
    else:
        if not im_array.shape[7] > 1:
            raise ValueError("No Multiple Replicas data found in this file.")
        im_array.flags["average"]["Rep"] = False
        im_array.flags["average"]["Ave"] = True

    SL_DIM = 11
    slices = []
    for sl in range(im_array.shape[SL_DIM]):
        if MR:
            k = np.transpose(
                im_array[0, 0, 0, 0, 0, 0, 0, :, 0, 0, 0, sl, 0, :, :, :],
                [3, 1, 2, 0],
            )
        else:
            k = np.transpose(
                im_array[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, sl, 0, :, :, :],
                [2, 0, 1],
            )
        slices.append(k)
    return slices


def extract_noise_kspace(dat_path, multiraid=False, raid=0):
    """
    Extract noise k-space.

    For multiraid files, noise is in raid 0.
    For separate noise files, it's the image data with OS kept.
    """
    if multiraid:
        noise = raider.readMultiRaidNoise(dat_path, slice="all", raid=0)
        return noise
    else:
        twix = twixtools.map_twix(dat_path)
        try:
            im_array = twix[raid]["noise"]
        except KeyError:
            im_array = twix[raid]["image"]
        im_array.flags["remove_os"] = False
        im_array.flags["average"]["Rep"] = False
        im_array.flags["average"]["Ave"] = False

        SL_DIM = 11
        slices = []
        for sl in range(im_array.shape[SL_DIM]):
            k = np.transpose(
                im_array[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, sl, 0, :, :, :],
                [2, 0, 1],
            )
            slices.append(k)
        return slices


def extract_reference_kspace(dat_path, signal_phase_size, raid=1):
    """
    Extract reference / ACS k-space for accelerated acquisitions.

    Returns:
        list of arrays (freq, phase, coils) per slice, or None if no refscan.
    """
    twix = twixtools.map_twix(dat_path)
    try:
        r_array = twix[raid]["refscan"]
    except KeyError:
        return None

    r_array.flags["remove_os"] = True
    r_array.flags["average"]["Rep"] = True
    r_array.flags["average"]["Ave"] = True

    SL_DIM = 11
    slices = []
    for sl in range(r_array.shape[SL_DIM]):
        ref = np.transpose(
            r_array[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, sl, 0, :, :, :],
            [2, 0, 1],
        )
        # Pad reference to match signal phase size
        if ref.shape[1] < signal_phase_size:
            padded = np.zeros(
                (ref.shape[0], signal_phase_size, ref.shape[2]),
                dtype=ref.dtype,
            )
            padded[:, : ref.shape[1], :] = ref
            ref = padded
        slices.append(ref)
    return slices


def save_npz(filepath, kspace_slices, orientation_info, acceleration=None, acl=None):
    """
    Save k-space slices + metadata into a single .npz file.

    If multiple slices, they are stacked along axis 3: (freq, phase, coils, slices).
    """
    # Stack slices
    if len(kspace_slices) == 1:
        kspace = kspace_slices[0]
    else:
        kspace = np.stack(kspace_slices, axis=3)

    data = {"kspace": kspace}

    # Orientation from first slice
    if orientation_info:
        info = orientation_info[0]
        data["spacing"] = np.array(info["spacing"], dtype=np.float64)
        data["origin"] = np.array(info["origin"], dtype=np.float64)
        data["direction"] = np.array(info["direction"].flatten(), dtype=np.float64)
        data["fov"] = np.array(info["fov"], dtype=np.float64)

    # Acceleration
    if acceleration is not None:
        data["acceleration"] = np.array(acceleration, dtype=np.float64)
    if acl is not None:
        data["acl"] = np.array(
            [0.0 if np.isnan(v) else v for v in acl], dtype=np.float64,
        )

    np.savez_compressed(filepath, **data)
    print(f"  Saved: {filepath}")
    print(f"    kspace shape : {kspace.shape}  dtype={kspace.dtype}")
    if acceleration is not None:
        print(f"    acceleration : {acceleration}")
    if acl is not None:
        print(f"    acl          : {acl}")


def convert(
    signal_path,
    output_dir,
    noise_path=None,
    multiraid=False,
    MR=False,
    generate_json=True,
):
    """
    Convert a Siemens .dat to .npz files.

    Args:
        signal_path: Path to the signal .dat file.
        output_dir:  Output directory for .npz files.
        noise_path:  Path to a separate noise .dat file (None if multiraid).
        multiraid:   If True, noise is embedded in the signal file (raid 0).
        MR:          If True, extract multiple replicas.
        generate_json: If True, generate a ready-to-use JSON config.
    """
    os.makedirs(output_dir, exist_ok=True)
    signal_raid = 1 if multiraid else (len(twixtools.map_twix(signal_path)) - 1)

    print(f"Reading: {signal_path}")
    print(f"  Signal raid index: {signal_raid}")

    # ── 1. Signal ──────────────────────────────────────────────────────────
    print("Extracting signal k-space...")
    signal_slices = extract_signal_kspace(signal_path, signal_raid, MR=MR)
    print(f"  {len(signal_slices)} slice(s), shape per slice: {signal_slices[0].shape}")

    # ── 2. Orientation ─────────────────────────────────────────────────────
    print("Extracting orientation...")
    twix_data = twixtools.map_twix(signal_path)
    orientation = extract_orientation(twix_data, signal_raid)
    print(f"  spacing: {orientation[0]['spacing']}")
    print(f"  origin : {orientation[0]['origin']}")
    print(f"  fov    : {orientation[0]['fov']}")

    # ── 3. Acceleration ───────────────────────────────────────────────────
    print("Extracting acceleration info...")
    acceleration, acl = extract_acceleration(twix_data, signal_raid)
    print(f"  acceleration: {acceleration}")
    print(f"  acl         : {acl}")

    # ── 4. Save signal ────────────────────────────────────────────────────
    sig_npz = os.path.join(output_dir, "signal.npz")
    save_npz(sig_npz, signal_slices, orientation, acceleration, acl)

    # ── 5. Noise ──────────────────────────────────────────────────────────
    noi_npz = os.path.join(output_dir, "noise.npz")
    if multiraid:
        print("Extracting noise from multiraid (raid 0)...")
        noise_slices = extract_noise_kspace(signal_path, multiraid=True)
    elif noise_path:
        print(f"Extracting noise from: {noise_path}")
        noise_slices = extract_noise_kspace(noise_path, multiraid=False)
    else:
        print("WARNING: No noise source specified. Skipping noise extraction.")
        noise_slices = None

    if noise_slices is not None:
        save_npz(noi_npz, noise_slices, None)

    # ── 6. Reference / ACS ────────────────────────────────────────────────
    ref_npz = os.path.join(output_dir, "reference.npz")
    has_accel = acceleration[1] > 1 if len(acceleration) > 1 else False
    if has_accel:
        print("Extracting reference / ACS k-space...")
        phase_size = signal_slices[0].shape[1]
        ref_slices = extract_reference_kspace(signal_path, phase_size, raid=signal_raid)
        if ref_slices is not None:
            save_npz(ref_npz, ref_slices, None)
        else:
            print("  No refscan found in file.")
            ref_npz = None
    else:
        print("No acceleration detected — skipping reference extraction.")
        ref_npz = None

    # ── 7. Generate JSON config ───────────────────────────────────────────
    if generate_json:
        config = _build_json_config(
            sig_path=os.path.abspath(sig_npz),
            noi_path=os.path.abspath(noi_npz) if noise_slices else None,
            ref_path=os.path.abspath(ref_npz) if ref_npz else None,
            acceleration=acceleration,
            acl=acl,
        )
        config_path = os.path.join(output_dir, "config_numpy.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"\nGenerated JSON config: {config_path}")

    print("\nDone!")
    return output_dir


def _build_json_config(sig_path, noi_path=None, ref_path=None,
                       acceleration=None, acl=None):
    """Build a ready-to-use MR Optimum JSON config for the converted numpy files."""

    signal_opts = {
        "type": "local",
        "vendor": "numpy",
        "filename": sig_path,
        "multiraid": False,
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
                "multiraid": False,
            },
        }

    # Determine if accelerated
    has_accel = acceleration is not None and len(acceleration) > 1 and acceleration[1] > 1
    if has_accel:
        recon_opts["accelerations"] = acceleration
        recon_opts["acl"] = [None if np.isnan(v) else int(v) for v in acl]
        recon_opts["decimate"] = False
        # Default to SENSE for accelerated
        recon_name = "Sense"
        recon_opts["sensitivityMap"] = {
            "type": "sensitivityMap",
            "id": 1,
            "name": "inner",
            "options": {"sensitivityMapMethod": "inner", "mask": "no"},
        }
    else:
        recon_name = "RSS"

    config = {
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
    return config


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="dat2numpy",
        description="Convert Siemens .dat raw data to NumPy .npz files for MR Optimum",
    )
    parser.add_argument(
        "-i", "--input", required=True, type=str,
        help="Path to the Siemens signal .dat file",
    )
    parser.add_argument(
        "-o", "--output", required=True, type=str,
        help="Output directory for .npz files",
    )
    parser.add_argument(
        "--noise", type=str, default=None,
        help="Path to a separate noise .dat file (if not multiraid)",
    )
    parser.add_argument(
        "--multiraid", action="store_true",
        help="Noise is embedded in the signal file as raid 0",
    )
    parser.add_argument(
        "--mr", action="store_true",
        help="Extract Multiple Replicas (MR) data",
    )
    parser.add_argument(
        "--no-json", action="store_true",
        help="Skip JSON config generation",
    )
    args = parser.parse_args()

    convert(
        signal_path=args.input,
        output_dir=args.output,
        noise_path=args.noise,
        multiraid=args.multiraid,
        MR=args.mr,
        generate_json=not args.no_json,
    )

"""
Siemens .dat full inventory → NumPy + preview images.

Scans every raid and every scan type in a .dat file, exports each dataset
as a self-contained .npz file and saves a quick RSS reconstruction PNG so
the upstream backend can present all available data to the user before the
actual SNR calculation.

Output structure::

    output_dir/
        inventory.json              # manifest of every dataset found
        raid0_noise.npz
        raid0_noise_recon.png
        raid1_noise.npz
        raid1_image.npz
        raid1_image_recon.png
        raid1_refscan.npz
        raid1_refscan_recon.png
        ...

.npz keys (all optional except kspace):
    kspace      : (freq, phase, coils[, slices[, reps]])  complex64
    spacing     : [dx, dy, dz]
    origin      : [ox, oy, oz]
    direction   : 9 floats, row-major 3×3
    fov         : [fov_f, fov_p, fov_s]
    acceleration: [accel_f, accel_p]
    acl         : [acl_f, acl_p]

Usage:
    conda run -n mro python tools/dat_inventory.py \\
        -i /path/to/signal.dat \\
        -o /path/to/output_dir/
"""

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import twixtools

# ---------------------------------------------------------------------------
# Twixtools dimension layout (16-D arrays)
#   0:Ide  1:Idd  2:Idc  3:Idb  4:Ida  5:Seg  6:Set  7:Rep
#   8:Phs  9:Eco  10:Par 11:Sli 12:Ave 13:Lin 14:Cha 15:Col
# ---------------------------------------------------------------------------
DIM_REP = 7
DIM_SLI = 11
DIM_LIN = 13
DIM_CHA = 14
DIM_COL = 15

# Scan types where OS removal is meaningful
IMAGE_LIKE = {"image", "refscan", "phasecor", "phasecor_pe"}


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def squeeze_to_kspace(arr, scan_type):
    """
    Extract (freq, phase, coils[, slices[, reps]]) from a 16-D twixtools array.

    Uses a single bulk read (``arr[:]``) to avoid the catastrophic per-element
    seek overhead that occurs when looping over replicas × slices on large
    datasets (e.g. 100-replica multi-slice files).

    16-D dim order (twixtools):
        0:Ide  1:Idd  2:Idc  3:Idb  4:Ida  5:Seg  6:Set  7:Rep
        8:Phs  9:Eco 10:Par 11:Sli 12:Ave 13:Lin 14:Cha 15:Col

    Returns:
        kspace : np.ndarray  (freq, phase, coils[, slices[, reps]])
        n_sli  : int
        n_rep  : int
    """
    arr.flags["remove_os"] = scan_type in IMAGE_LIKE
    arr.flags["average"]["Rep"] = False
    arr.flags["average"]["Ave"] = False

    shape = arr.shape  # 16-D
    n_sli = shape[DIM_SLI]   # dim 11
    n_rep = shape[DIM_REP]   # dim 7

    # ── Single bulk read ───────────────────────────────────────────────────
    # arr[:] returns the full 16-D array in one pass over the file.
    full = arr[:]   # shape: (1,1,1,1,1,1,1, Rep, 1,1,1, Sli, 1, Lin, Cha, Col)

    # Collapse singleton dims; keep Rep(7), Sli(11), Lin(13), Cha(14), Col(15)
    k = full[0, 0, 0, 0, 0, 0, 0, :, 0, 0, 0, :, 0, :, :, :]
    # k: (Rep, Sli, Lin, Cha, Col)

    # ── Single-slice, single-rep fast path ────────────────────────────────
    if n_sli == 1 and n_rep == 1:
        # (1, 1, Lin, Cha, Col) → (Col, Lin, Cha)
        kspace = np.transpose(k[0, 0], [2, 0, 1])
        return kspace, n_sli, n_rep

    # ── Single-rep multi-slice ────────────────────────────────────────────
    if n_rep == 1:
        # (1, Sli, Lin, Cha, Col) → (Col, Lin, Cha, Sli)
        kspace = np.transpose(k[0], [3, 1, 2, 0])
        return kspace, n_sli, n_rep

    # ── Single-slice multi-rep ────────────────────────────────────────────
    if n_sli == 1:
        # (Rep, 1, Lin, Cha, Col) → (Col, Lin, Cha, Rep)
        kspace = np.transpose(k[:, 0], [3, 1, 2, 0])
        return kspace, n_sli, n_rep

    # ── Multi-slice multi-rep: (Rep, Sli, Lin, Cha, Col) → (Col, Lin, Cha, Sli, Rep)
    kspace = np.transpose(k, [4, 2, 3, 1, 0])
    return kspace, n_sli, n_rep


# ---------------------------------------------------------------------------
# Orientation / acceleration helpers (reuse dat2numpy logic)
# ---------------------------------------------------------------------------

def _get_orientation(twix_data, raid_idx):
    """Extract first-slice orientation from twix headers. Returns dict or None."""
    try:
        H = twix_data[raid_idx]["hdr"]
        SA = H["Phoenix"]["sSliceArray"]
        C = H["Config"]
        KS = [int(C["BaseResolution"]), int(C["PhaseEncodingLines"])]
        SL = SA["asSlice"]
        sl = SL[0]
        slp = sl.get("sPosition", {})
        origin = [slp.get("dSag", 0.0), slp.get("dCor", 0.0), slp.get("dTra", 0.0)]
        spacing = [
            sl["dReadoutFOV"] / KS[0],
            sl["dPhaseFOV"] / KS[1],
            sl["dThickness"],
        ]
        fov = [sl["dReadoutFOV"], sl["dPhaseFOV"],
               sl["dThickness"] * SA["lSize"]]
        direction = -np.eye(3)
        if "dTra" in sl.get("sNormal", {}):
            direction[2, 2] = -sl["sNormal"]["dTra"]
        if "dSag" in sl.get("sNormal", {}):
            direction[0, 0] = sl["sNormal"]["dSag"]
        if "dCor" in sl.get("sNormal", {}):
            direction[1, 1] = sl["sNormal"]["dCor"]
        return {"spacing": spacing, "origin": origin,
                "direction": direction, "fov": fov}
    except Exception:
        return None


def _get_acceleration(twix_data, raid_idx):
    """Return (acceleration, acl) from twix headers."""
    try:
        iPat = twix_data[raid_idx]["hdr"]["MeasYaps"]["sPat"]
        return [1, int(iPat["lAccelFactPE"])], [np.nan, int(iPat["lRefLinesPE"])]
    except Exception:
        return [1, 1], [np.nan, np.nan]


# ---------------------------------------------------------------------------
# Quick RSS reconstruction
# ---------------------------------------------------------------------------

def quick_rss_recon(kspace):
    """
    Fast RSS reconstruction of the central slice from a (freq, phase, coils, ...)
    array.  Returns a (freq, phase) magnitude image.
    """
    # Pick central slice
    if kspace.ndim >= 4:
        sl = kspace.shape[3] // 2
        k2d = kspace[:, :, :, sl]
    else:
        k2d = kspace  # (freq, phase, coils)

    # If replicas present take first
    if k2d.ndim == 4:
        k2d = k2d[:, :, :, 0]

    # iFFT2 per coil then RSS
    imgs = np.fft.fftshift(
        np.fft.ifft2(np.fft.ifftshift(k2d, axes=(0, 1)), axes=(0, 1)),
        axes=(0, 1),
    )
    rss = np.sqrt(np.sum(np.abs(imgs) ** 2, axis=2))
    return rss


def save_recon_png(kspace, out_path, title=""):
    """Reconstruct central slice and save as PNG."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        rss = quick_rss_recon(kspace)

        fig, ax = plt.subplots(1, 1, figsize=(6, 6))
        ax.imshow(np.rot90(rss), cmap="gray", origin="lower")
        ax.set_title(title, fontsize=9)
        ax.axis("off")
        plt.tight_layout()
        plt.savefig(out_path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        return True
    except Exception as e:
        print(f"    [recon] warning: {e}")
        return False


# ---------------------------------------------------------------------------
# Save .npz
# ---------------------------------------------------------------------------

def save_npz(filepath, kspace, orient=None, acceleration=None, acl=None):
    """Save kspace + metadata to a compressed .npz file."""
    data = {"kspace": kspace.astype(np.complex64)}

    if orient:
        data["spacing"]   = np.array(orient["spacing"],              dtype=np.float64)
        data["origin"]    = np.array(orient["origin"],               dtype=np.float64)
        data["direction"] = np.array(orient["direction"].flatten(),  dtype=np.float64)
        data["fov"]       = np.array(orient["fov"],                  dtype=np.float64)

    if acceleration is not None:
        data["acceleration"] = np.array(acceleration, dtype=np.float64)
    if acl is not None:
        data["acl"] = np.array(
            [0.0 if (v is None or (isinstance(v, float) and np.isnan(v))) else v
             for v in acl],
            dtype=np.float64,
        )

    np.savez_compressed(filepath, **data)


# ---------------------------------------------------------------------------
# Main inventory
# ---------------------------------------------------------------------------

def inventory(dat_path, output_dir):
    """
    Scan every raid and scan type in *dat_path*, export to .npz + PNG previews.

    Returns a manifest dict (also written to inventory.json).
    """
    os.makedirs(output_dir, exist_ok=True)
    print(f"Scanning: {dat_path}")

    twix_data = twixtools.map_twix(dat_path)
    print(f"  Found {len(twix_data)} raid(s)")

    manifest = {
        "source": dat_path,
        "raids": {},
    }

    for raid_idx, raid in enumerate(twix_data):
        scan_keys = [k for k in raid.keys() if k not in ("hdr", "hdr_str")]
        if not scan_keys:
            continue

        orient     = _get_orientation(twix_data, raid_idx)
        accel, acl = _get_acceleration(twix_data, raid_idx)

        print(f"\n  raid {raid_idx}: {scan_keys}")
        manifest["raids"][raid_idx] = {}

        for scan_type in scan_keys:
            suffix   = f"raid{raid_idx}_{scan_type}"
            npz_path = os.path.join(output_dir, f"{suffix}.npz")
            png_path = os.path.join(output_dir, f"{suffix}_recon.png")

            print(f"    [{scan_type}] extracting...", end=" ", flush=True)
            try:
                kspace, n_sli, n_rep = squeeze_to_kspace(raid[scan_type], scan_type)
            except Exception as e:
                print(f"FAILED ({e})")
                continue

            print(f"shape={kspace.shape}  dtype={kspace.dtype}")

            # Save .npz — orientation and acceleration only for signal-like scans
            use_orient = orient if scan_type in IMAGE_LIKE else None
            use_accel  = accel  if scan_type in IMAGE_LIKE else None
            use_acl    = acl    if scan_type in IMAGE_LIKE else None
            save_npz(npz_path, kspace, use_orient, use_accel, use_acl)

            # Quick recon PNG (skip pure noise scans with very few lines)
            png_saved = False
            if scan_type in IMAGE_LIKE and kspace.shape[1] > 4:
                title = (f"raid{raid_idx}/{scan_type}  "
                         f"shape={kspace.shape}  slices={n_sli}  reps={n_rep}")
                png_saved = save_recon_png(kspace, png_path, title=title)

            entry = {
                "npz":         os.path.abspath(npz_path),
                "shape":       list(kspace.shape),
                "dtype":       str(kspace.dtype),
                "slices":      n_sli,
                "reps":        n_rep,
                "scan_type":   scan_type,
                "has_orient":  use_orient is not None,
                "acceleration": use_accel,
                "acl":          [None if (v is None or (isinstance(v, float) and np.isnan(v))) else v
                                 for v in use_acl] if use_acl else None,
                "recon_png":   os.path.abspath(png_path) if png_saved else None,
            }
            manifest["raids"][raid_idx][scan_type] = entry

    # Write manifest
    manifest_path = os.path.join(output_dir, "inventory.json")
    # Convert int keys to str for JSON serialisation
    manifest_out = dict(manifest)
    manifest_out["raids"] = {str(k): v for k, v in manifest["raids"].items()}
    with open(manifest_path, "w") as f:
        json.dump(manifest_out, f, indent=2)
    print(f"\nInventory written: {manifest_path}")
    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="dat_inventory",
        description="Full inventory of a Siemens .dat file → .npz + PNG previews",
    )
    parser.add_argument("-i", "--input",  required=True, help="Path to .dat file")
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    args = parser.parse_args()

    inventory(args.input, args.output)

"""
Multi-format file type inventory → NumPy + preview images.

Works like dat_inventory.py but handles multiple file types:
- ISMRMRD (.h5) files → k-space extraction via HDF5
- DAT (.dat) files → k-space extraction via twixtools
- MAT (.mat) files → k-space extraction from MATLAB structures

Scans every file in a folder, detects type, extracts k-space,
exports as .npz files and saves quick RSS reconstruction PNGs.

Output structure::

    output_dir/
        inventory.json              # manifest of every dataset found
        file1_dataset0.npz
        file1_dataset0_recon.png
        file1_dataset1.npz
        file1_dataset1_recon.png
        file2_raid0_image.npz
        file2_raid0_image_recon.png
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
    python tools/file_type_inventory.py \\
        -i /path/to/folder \\
        -o /path/to/output_dir/
"""

import argparse
import json
import os
import sys

import numpy as np
import h5py
import scipy.io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import twixtools
except ImportError:
    twixtools = None

# Scan types where OS removal/reconstruction is meaningful
IMAGE_LIKE = {"image", "refscan", "phasecor", "phasecor_pe"}


# ---------------------------------------------------------------------------
# File type detection
# ---------------------------------------------------------------------------

def detect_file_type(filepath):
    """Detect file type: ismrmrd (.h5), dat, or mat."""
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext == ".h5":
        try:
            with h5py.File(filepath, 'r') as f:
                if 'ismrmrd_header' in f:
                    return 'ismrmrd'
        except Exception:
            pass
        return 'h5'
    elif ext == ".dat":
        return 'dat'
    elif ext == ".mat":
        try:
            scipy.io.loadmat(filepath)
            return 'mat'
        except Exception:
            return 'mat_corrupted'
    else:
        return 'unknown'


# ---------------------------------------------------------------------------
# K-space extraction helpers
# ---------------------------------------------------------------------------

def quick_rss_recon(kspace):
    """
    Fast RSS reconstruction of the central slice from a (freq, phase, coils, ...)
    array.  Returns a (freq, phase) magnitude image.
    """
    if kspace.ndim >= 4:
        sl = kspace.shape[3] // 2
        k2d = kspace[:, :, :, sl]
    else:
        k2d = kspace

    if k2d.ndim == 4:
        k2d = k2d[:, :, :, 0]

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
        print(f"      [recon] warning: {e}")
        return False


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
# DAT file processing (via twixtools)
# ---------------------------------------------------------------------------

def process_dat_file(dat_path, output_dir, manifest):
    """Process a .dat file like dat_inventory does."""
    if twixtools is None:
        print(f"  [SKIP] twixtools not available")
        return
    
    print(f"  Processing .dat file...")
    
    try:
        twix_data = twixtools.map_twix(dat_path)
    except Exception as e:
        print(f"  [ERROR] Failed to map twix: {e}")
        return
    
    print(f"    Found {len(twix_data)} raid(s)")
    
    DIM_REP = 7
    DIM_SLI = 11
    DIM_LIN = 13
    DIM_CHA = 14
    DIM_COL = 15
    
    def squeeze_to_kspace(arr, scan_type):
        arr.flags["remove_os"] = scan_type in IMAGE_LIKE
        arr.flags["average"]["Rep"] = False
        arr.flags["average"]["Ave"] = False
        
        shape = arr.shape
        n_sli = shape[DIM_SLI]
        n_rep = shape[DIM_REP]
        
        full = arr[:]
        k = full[0, 0, 0, 0, 0, 0, 0, :, 0, 0, 0, :, 0, :, :, :]
        
        if n_sli == 1 and n_rep == 1:
            kspace = np.transpose(k[0, 0], [2, 0, 1])
            return kspace, n_sli, n_rep
        
        if n_rep == 1:
            kspace = np.transpose(k[0], [3, 1, 2, 0])
            return kspace, n_sli, n_rep
        
        if n_sli == 1:
            kspace = np.transpose(k[:, 0], [3, 1, 2, 0])
            return kspace, n_sli, n_rep
        
        kspace = np.transpose(k, [4, 2, 3, 1, 0])
        return kspace, n_sli, n_rep
    
    def get_orientation(twix_data, raid_idx):
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
            return {"spacing": spacing, "origin": origin, "direction": direction, "fov": fov}
        except Exception:
            return None
    
    def get_acceleration(twix_data, raid_idx):
        try:
            iPat = twix_data[raid_idx]["hdr"]["MeasYaps"]["sPat"]
            return [1, int(iPat["lAccelFactPE"])], [np.nan, int(iPat["lRefLinesPE"])]
        except Exception:
            return [1, 1], [np.nan, np.nan]
    
    for raid_idx, raid in enumerate(twix_data):
        scan_keys = [k for k in raid.keys() if k not in ("hdr", "hdr_str")]
        if not scan_keys:
            continue
        
        orient = get_orientation(twix_data, raid_idx)
        accel, acl = get_acceleration(twix_data, raid_idx)
        
        print(f"    raid {raid_idx}: {scan_keys}")
        
        for scan_type in scan_keys:
            suffix = f"raid{raid_idx}_{scan_type}"
            npz_path = os.path.join(output_dir, f"{suffix}.npz")
            png_path = os.path.join(output_dir, f"{suffix}_recon.png")
            
            print(f"      [{scan_type}] extracting...", end=" ", flush=True)
            try:
                kspace, n_sli, n_rep = squeeze_to_kspace(raid[scan_type], scan_type)
            except Exception as e:
                print(f"FAILED ({e})")
                continue
            
            print(f"shape={kspace.shape}  dtype={kspace.dtype}")
            
            use_orient = orient if scan_type in IMAGE_LIKE else None
            use_accel = accel if scan_type in IMAGE_LIKE else None
            use_acl = acl if scan_type in IMAGE_LIKE else None
            save_npz(npz_path, kspace, use_orient, use_accel, use_acl)
            
            png_saved = False
            if scan_type in IMAGE_LIKE and kspace.shape[1] > 4:
                title = (f"raid{raid_idx}/{scan_type}  "
                         f"shape={kspace.shape}  slices={n_sli}  reps={n_rep}")
                png_saved = save_recon_png(kspace, png_path, title=title)
            
            entry = {
                "npz": os.path.abspath(npz_path),
                "shape": list(kspace.shape),
                "dtype": str(kspace.dtype),
                "slices": n_sli,
                "reps": n_rep,
                "scan_type": scan_type,
                "has_orient": use_orient is not None,
                "acceleration": use_accel,
                "acl": [None if (v is None or (isinstance(v, float) and np.isnan(v))) else v
                        for v in use_acl] if use_acl else None,
                "recon_png": os.path.abspath(png_path) if png_saved else None,
            }
            manifest["datasets"][f"{suffix}"] = entry


# ---------------------------------------------------------------------------
# ISMRMRD file processing
# ---------------------------------------------------------------------------

def process_ismrmrd_file(h5_path, output_dir, manifest):
    """Process an ISMRMRD (.h5) file."""
    print(f"  Processing ISMRMRD file...")
    
    try:
        with h5py.File(h5_path, 'r') as f:
            if 'dataset' not in f:
                print(f"    [WARNING] No 'dataset' group found")
                return
            
            dataset_group = f['dataset']
            dataset_num = 0
            
            for ds_key in dataset_group.keys():
                ds = dataset_group[ds_key]
                
                if 'kspace' not in ds:
                    print(f"    [{ds_key}] No kspace data")
                    continue
                
                kspace_data = ds['kspace'][:]
                
                # ISMRMRD raw data shape: (X, Y, Z, Coils, ...)
                # Try to reshape to (freq, phase, coils[, slices])
                if kspace_data.ndim >= 3:
                    kspace = kspace_data
                    n_sli = kspace.shape[2] if kspace.ndim > 3 else 1
                    n_rep = 1
                else:
                    continue
                
                suffix = f"ismrmrd_{dataset_num}"
                npz_path = os.path.join(output_dir, f"{suffix}.npz")
                png_path = os.path.join(output_dir, f"{suffix}_recon.png")
                
                print(f"    [{ds_key}] shape={kspace.shape}  dtype={kspace.dtype}")
                
                save_npz(npz_path, kspace)
                
                png_saved = False
                if kspace.shape[1] > 4:
                    title = f"ismrmrd_{dataset_num}  shape={kspace.shape}"
                    png_saved = save_recon_png(kspace, png_path, title=title)
                
                entry = {
                    "npz": os.path.abspath(npz_path),
                    "shape": list(kspace.shape),
                    "dtype": str(kspace.dtype),
                    "slices": n_sli,
                    "reps": n_rep,
                    "dataset_key": ds_key,
                    "recon_png": os.path.abspath(png_path) if png_saved else None,
                }
                manifest["datasets"][f"{suffix}"] = entry
                dataset_num += 1
    
    except Exception as e:
        print(f"  [ERROR] {e}")


# ---------------------------------------------------------------------------
# MAT file processing
# ---------------------------------------------------------------------------

def process_mat_file(mat_path, output_dir, manifest):
    """Process a MATLAB .mat file."""
    print(f"  Processing MAT file...")
    
    try:
        mat_data = scipy.io.loadmat(mat_path)
        
        kspace_candidates = [k for k in mat_data.keys() 
                            if not k.startswith('__') and isinstance(mat_data[k], np.ndarray)]
        
        if not kspace_candidates:
            print(f"    [WARNING] No suitable arrays found")
            return
        
        for idx, key in enumerate(kspace_candidates[:5]):  # Process first 5 arrays
            arr = mat_data[key]
            
            if arr.ndim < 2 or arr.size == 0:
                continue
            
            # Try to use as complex k-space if it has complex values
            if np.iscomplexobj(arr):
                if arr.ndim == 2:
                    # (freq, phase) -> add coils and slice dims
                    kspace = np.expand_dims(np.expand_dims(arr, axis=2), axis=3)
                elif arr.ndim == 3:
                    # (freq, phase, coils) or similar
                    kspace = arr
                else:
                    kspace = arr
            else:
                continue  # Skip non-complex arrays
            
            suffix = f"mat_{idx}_{key}"
            npz_path = os.path.join(output_dir, f"{suffix}.npz")
            png_path = os.path.join(output_dir, f"{suffix}_recon.png")
            
            print(f"    [{key}] shape={kspace.shape}  dtype={kspace.dtype}")
            
            save_npz(npz_path, kspace)
            
            png_saved = False
            if kspace.ndim >= 2 and kspace.shape[1] > 4:
                title = f"mat_{idx}  shape={kspace.shape}"
                png_saved = save_recon_png(kspace, png_path, title=title)
            
            entry = {
                "npz": os.path.abspath(npz_path),
                "shape": list(kspace.shape),
                "dtype": str(kspace.dtype),
                "mat_variable": key,
                "recon_png": os.path.abspath(png_path) if png_saved else None,
            }
            manifest["datasets"][f"{suffix}"] = entry
    
    except Exception as e:
        print(f"  [ERROR] {e}")


# ---------------------------------------------------------------------------
# Main inventory
# ---------------------------------------------------------------------------

def _collect_files(input_path):
    """Return list of file paths from a file or directory input."""
    if os.path.isfile(input_path):
        return [input_path]
    files = []
    for root, _, fnames in os.walk(input_path):
        for fname in fnames:
            files.append(os.path.join(root, fname))
    return files


def inventory(input_path, output_dir):
    """
    Process a single file or every file in a folder: detect type, extract
    k-space, save .npz + PNG previews.

    Returns manifest dict (also written to inventory.json).
    """
    os.makedirs(output_dir, exist_ok=True)
    print(f"Input: {input_path}")

    manifest = {
        "source": input_path,
        "datasets": {},
        "summary": {
            "ismrmrd": 0,
            "dat": 0,
            "mat": 0,
            "unknown": 0,
            "processed": 0,
        }
    }

    for fpath in _collect_files(input_path):
        fname = os.path.basename(fpath)
        ftype = detect_file_type(fpath)

        if ftype == "unknown":
            print(f"[SKIP] {fname} (unknown type)")
            manifest["summary"]["unknown"] += 1
            continue

        print(f"\n[{ftype}] {fname}")
        manifest["summary"][ftype] += 1

        try:
            if ftype == "dat":
                process_dat_file(fpath, output_dir, manifest)
            elif ftype == "ismrmrd":
                process_ismrmrd_file(fpath, output_dir, manifest)
            elif ftype == "mat":
                process_mat_file(fpath, output_dir, manifest)
            manifest["summary"]["processed"] += 1
        except Exception as e:
            print(f"  [ERROR] Failed to process: {e}")
    
    # Write manifest
    manifest_path = os.path.join(output_dir, "inventory.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n✓ Inventory written: {manifest_path}")
    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="file_type_inventory",
        description="Multi-format file inventory → .npz + PNG previews (DAT/ISMRMRD/MAT)",
    )
    parser.add_argument("-i", "--input",  required=True, 
                        help="Path to a single file or a folder to scan")
    parser.add_argument("-o", "--output", required=True, 
                        help="Output directory for .npz/.png files")
    args = parser.parse_args()
    
    inv = inventory(args.input, args.output)
    print(f"\nSummary: {json.dumps(inv['summary'], indent=2)}")

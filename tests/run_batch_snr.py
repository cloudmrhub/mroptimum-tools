"""
Batch SNR calculation across all subdirectories in a Siemens raw data folder.

For each subdirectory:
1. Identifies signal and noise files by naming convention
2. Detects if GRAPPA/SENSE from filename or headers
3. Runs the appropriate SNR calculation (Kellman analytical)
4. Saves SNR NIfTI + info JSON in a mirrored output directory
5. Produces a summary CSV

Naming heuristics:
    NOISE files: contain 'noise', 'noi', 'no_rf', 'norf', '0v', '000v', '0volt'
                 (case-insensitive) in the filename
    GRAPPA files: contain 'grappa' in the filename
    SENSE/mSENSE files: contain 'sense' or 'msense' in the filename
    Everything else: RSS reconstruction

Usage:
    conda run -n mro python tests/run_batch_snr.py \
        -i /data/MYDATA/siemensrawdataexamples/ \
        -o /g/mro_test_snr
"""

import argparse
import csv
import json
import os
import re
import sys
import traceback
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mrotools.kspace_loaders import get_kspace_loader
from mrotools.dat_version import DatFileInfo
from mrotools.mro import (
    RECON, RECON_classes, KELLMAN_classes,
    calcKellmanSNR, calculteNoiseCovariance, saveImage,
)
from pyable_eros_montin import imaginable as ima


# ---------------------------------------------------------------------------
# File classification
# ---------------------------------------------------------------------------

# Patterns that identify a noise file
NOISE_PATTERNS = [
    r'(?i)[\W_]noise[\W_]',
    r'(?i)[\W_]noi[\W_]',
    r'(?i)[\W_]no[\W_]?rf[\W_]',
    r'(?i)[\W_]norf[\W_]',
    r'(?i)_0+v[\W_]',       # 0v, 000v, 0000v
    r'(?i)[\W_]0volt[\W_]',
    r'(?i)RF[\W_]?0+v',     # RF000v, RF_000v
]

GRAPPA_PATTERN = re.compile(r'(?i)grappa', re.IGNORECASE)
SENSE_PATTERN = re.compile(r'(?i)(m?sense)', re.IGNORECASE)


def is_noise_file(filename):
    """Check if a filename looks like a noise acquisition."""
    for pat in NOISE_PATTERNS:
        if re.search(pat, filename):
            return True
    # Also check for "no_RF" style (no signal, noise-only)
    if re.search(r'(?i)no[_\s]?RF', filename):
        return True
    return False


def detect_recon_type(filename):
    """
    Detect reconstruction type from filename.
    Returns: 'rss', 'grappa', or 'sense'
    """
    if GRAPPA_PATTERN.search(filename):
        return 'grappa'
    if SENSE_PATTERN.search(filename):
        return 'sense'
    return 'rss'


def detect_acceleration_from_filename(filename):
    """Try to extract acceleration factor from filename like 'GRAPPA_2' or 'mSENSE_3'."""
    m = re.search(r'(?i)(?:grappa|sense|msense)[_\s]?(\d)', filename)
    if m:
        return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Directory scanning
# ---------------------------------------------------------------------------

def scan_directory(dir_path):
    """
    Scan a directory and classify .dat files into signal/noise pairs.

    Returns list of dicts:
        {signal: path, noise: path_or_None, recon_type: str, accel: int_or_None}
    """
    dat_files = sorted([
        f for f in os.listdir(dir_path)
        if f.lower().endswith('.dat') and not f.startswith('.')
    ])

    if not dat_files:
        return []

    # Separate noise from signal
    noise_files = [f for f in dat_files if is_noise_file(f)]
    signal_files = [f for f in dat_files if not is_noise_file(f)]

    # If no explicit noise files but we have multiraid, noise is embedded
    # If no signal files at all, skip this directory
    if not signal_files:
        return []

    # Pick the best noise file (first one found)
    noise_path = os.path.join(dir_path, noise_files[0]) if noise_files else None

    # Build pairs
    pairs = []
    for sig_name in signal_files:
        sig_path = os.path.join(dir_path, sig_name)
        recon_type = detect_recon_type(sig_name)
        accel = detect_acceleration_from_filename(sig_name)
        pairs.append({
            'signal': sig_path,
            'noise': noise_path,
            'recon_type': recon_type,
            'accel_from_name': accel,
        })

    return pairs


# ---------------------------------------------------------------------------
# SNR calculation
# ---------------------------------------------------------------------------

def compute_snr(signal_path, noise_path, recon_type='rss', accel_from_name=None):
    """
    Compute SNR for a signal file.

    Args:
        signal_path: path to signal .dat
        noise_path: path to noise .dat (can be None for multiraid)
        recon_type: 'rss', 'grappa', or 'sense'
        accel_from_name: acceleration factor from filename (override)

    Returns:
        dict with results or error info
    """
    result = {
        'signal_file': os.path.basename(signal_path),
        'noise_file': os.path.basename(noise_path) if noise_path else 'multiraid/prescan',
        'recon_type': recon_type,
        'status': 'OK',
        'error': None,
    }

    try:
        # Get file info
        dat_info = DatFileInfo(signal_path)
        result['platform'] = dat_info.platform
        result['syngo_version'] = dat_info.syngo_version
        result['is_multiraid'] = dat_info.is_multiraid

        # Determine if multiraid noise
        multiraid = dat_info.is_multiraid and dat_info.n_raids > 1

        # Get loader
        loader = get_kspace_loader('siemens')

        # Build signal options
        signal_options = {
            'type': 'file',
            'options': {
                'type': 'local',
                'vendor': 'Siemens',
                'filename': signal_path,
                'multiraid': multiraid,
            }
        }

        # Load signal k-space
        SL = loader.get_signal_kspace(signal_options, signal=True, MR=False)
        if isinstance(SL, str):
            result['status'] = 'ERROR'
            result['error'] = SL
            return result, None

        result['n_slices'] = len(SL)
        result['matrix_size'] = SL[0]['size'][:2]
        result['n_coils'] = SL[0]['KSpace'].shape[2]
        result['spacing'] = SL[0]['spacing']
        result['origin'] = SL[0]['origin']
        result['fov'] = SL[0]['fov']

        # Load noise
        NOISE = None
        if multiraid:
            # Noise from multiraid (raid 0)
            NOISE = loader.get_noise_kspace(signal_options, 'all')
        elif noise_path:
            noise_options = {
                'type': 'file',
                'options': {
                    'type': 'local',
                    'vendor': 'Siemens',
                    'filename': noise_path,
                    'multiraid': False,
                }
            }
            NOISE = loader.get_noise_kspace(noise_options, 'all')

        # Compute noise covariance
        if NOISE is not None:
            NC, NCC = calculteNoiseCovariance(NOISE, verbose=False)
        else:
            # No noise: use identity (no prewhitening)
            n_coils = SL[0]['KSpace'].shape[2]
            NC = np.eye(n_coils, dtype=np.complex64)
            NCC = None

        # Determine reconstructor
        # Map recon_type to RID
        RID_MAP = {'rss': 0, 'sense': 2, 'grappa': 3}
        RID = RID_MAP.get(recon_type, 0)

        # For GRAPPA/SENSE, we need acceleration info
        acceleration = None
        autocalibration = None
        reference = None

        if RID >= 2:  # SENSE or GRAPPA
            accel_info, acl_info = loader.get_acceleration_info(signal_options)
            if accel_from_name:
                acceleration = [1, accel_from_name]
            elif accel_info[1] > 1:
                acceleration = accel_info
            else:
                # No acceleration detected — fall back to RSS
                RID = 0
                recon_type = 'rss'
                result['recon_type'] = 'rss (fallback)'

            if RID >= 2:
                autocalibration = acl_info
                # Try to get reference k-space
                reference = loader.get_reference_kspace(
                    signal_options,
                    signal_acceleration_realsize=SL[0]['size'][1],
                    slice_sel='all'
                )

        result['acceleration'] = acceleration

        # Use Kellman analytical SNR
        reconstructor_class = KELLMAN_classes[RID]

        # Compute SNR per slice
        snr_slices = []
        for counter, sl_data in enumerate(SL):
            O = {
                'signal': sl_data['KSpace'],
                'noise': None,
                'noisecovariance': NC,
                'reference': reference[counter] if reference and counter < len(reference) else None,
                'mask': False,
                'mimic': False,
                'acceleration': acceleration,
                'autocalibration': autocalibration,
                'grappakernel': [4, 4] if RID == 3 else None,
                'slice': counter,
                'NR': None,
                'boxSize': None,
                'reconstructor': reconstructor_class(),
                'savecoilsens': False,
                'savegfactor': False,
            }
            out = calcKellmanSNR(O)
            snr_map = out['images']['SNR']['data']
            snr_slices.append(np.abs(snr_map))

        # Stack slices
        if len(snr_slices) == 1:
            snr_3d = np.expand_dims(snr_slices[0], axis=-1)
        else:
            snr_3d = np.stack(snr_slices, axis=-1)

        # Stats
        mask = snr_3d > 0
        if mask.any():
            result['snr_mean'] = float(np.mean(snr_3d[mask]))
            result['snr_max'] = float(np.max(snr_3d[mask]))
            result['snr_median'] = float(np.median(snr_3d[mask]))
        else:
            result['snr_mean'] = 0.0
            result['snr_max'] = 0.0
            result['snr_median'] = 0.0

        return result, snr_3d

    except Exception as e:
        result['status'] = 'ERROR'
        result['error'] = f"{type(e).__name__}: {str(e)}"
        return result, None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Batch SNR calculation on all subdirectories of Siemens raw data"
    )
    parser.add_argument("-i", "--input", required=True,
                        help="Root directory with subdirectories of .dat files")
    parser.add_argument("-o", "--output", required=True,
                        help="Output root directory (mirrors input structure)")
    args = parser.parse_args()

    input_root = args.input
    output_root = args.output
    os.makedirs(output_root, exist_ok=True)

    # Find all subdirectories with .dat files
    all_results = []
    subdirs = []
    for root, dirs, files in os.walk(input_root):
        # Skip hidden dirs and __MACOSX
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__MACOSX']
        dat_files = [f for f in files if f.lower().endswith('.dat')]
        if dat_files:
            subdirs.append(root)

    print(f"Found {len(subdirs)} directories with .dat files\n")

    for dir_idx, dir_path in enumerate(sorted(subdirs)):
        rel_dir = os.path.relpath(dir_path, input_root)
        out_dir = os.path.join(output_root, rel_dir)
        os.makedirs(out_dir, exist_ok=True)

        print(f"\n[{dir_idx+1}/{len(subdirs)}] {rel_dir}/")
        print(f"  {'─' * 60}")

        pairs = scan_directory(dir_path)
        if not pairs:
            print("  (no signal files found)")
            continue

        # Show classification
        noise_name = os.path.basename(pairs[0]['noise']) if pairs[0]['noise'] else 'multiraid/prescan'
        print(f"  Noise: {noise_name}")
        print(f"  Signal files: {len(pairs)}")

        for pair in pairs:
            sig_name = os.path.basename(pair['signal'])
            print(f"    {sig_name} [{pair['recon_type']}] ... ", end='', flush=True)

            result, snr_3d = compute_snr(
                pair['signal'], pair['noise'],
                pair['recon_type'], pair['accel_from_name']
            )
            result['directory'] = rel_dir

            if result['status'] == 'OK':
                # Save SNR as NIfTI
                snr_nifti_name = os.path.splitext(sig_name)[0] + '_SNR.nii.gz'
                snr_path = os.path.join(out_dir, snr_nifti_name)

                try:
                    snr_3d[np.isnan(snr_3d)] = 0
                    snr_3d[np.isinf(snr_3d)] = 0
                    img = ima.numpyToImaginable(snr_3d)
                    direction = result.get('_direction', np.eye(3))
                    # Get direction from first slice if available
                    try:
                        dat_info = DatFileInfo(pair['signal'])
                        orient = dat_info.orientation(0)
                        direction = orient['direction'].flatten()
                    except:
                        direction = (-np.eye(3)).flatten()

                    saveImage(img, result['origin'], result['spacing'],
                              direction, snr_path)
                    result['snr_file'] = snr_nifti_name
                except Exception as e:
                    result['snr_file'] = f'SAVE_ERROR: {e}'

                print(f"OK  mean={result['snr_mean']:.1f} max={result['snr_max']:.1f} "
                      f"[{result.get('platform','?')}/{result.get('syngo_version','?')}] "
                      f"{result.get('n_slices',0)}sl {result.get('n_coils',0)}ch")
            else:
                print(f"ERROR: {result['error'][:60]}")
                result['snr_file'] = None

            all_results.append(result)

    # --- Write CSV summary ---
    csv_path = os.path.join(output_root, "snr_summary.csv")
    fieldnames = [
        'directory', 'signal_file', 'noise_file', 'recon_type', 'status',
        'platform', 'syngo_version', 'is_multiraid', 'n_slices', 'matrix_size',
        'n_coils', 'spacing', 'origin', 'fov', 'acceleration',
        'snr_mean', 'snr_max', 'snr_median', 'snr_file', 'error'
    ]
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for r in all_results:
            row = {k: r.get(k) for k in fieldnames}
            for k in ('matrix_size', 'spacing', 'origin', 'fov', 'acceleration'):
                if row.get(k) is not None:
                    row[k] = str(row[k])
            writer.writerow(row)

    # --- Print summary ---
    ok = [r for r in all_results if r['status'] == 'OK']
    errors = [r for r in all_results if r['status'] != 'OK']

    print(f"\n\n{'=' * 80}")
    print(f"BATCH SNR SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total signal files processed: {len(all_results)}")
    print(f"  OK:     {len(ok)}")
    print(f"  ERRORS: {len(errors)}")

    if ok:
        platforms = {}
        for r in ok:
            p = r.get('platform', '?')
            if p not in platforms:
                platforms[p] = []
            platforms[p].append(r)

        print(f"\n{'Platform':<8} {'Count':<7} {'Recon types':<30} {'Avg SNR'}")
        print('-' * 60)
        for p in sorted(platforms):
            items = platforms[p]
            recons = sorted(set(r.get('recon_type', '?') for r in items))
            avg_snr = np.mean([r['snr_mean'] for r in items if r.get('snr_mean', 0) > 0])
            print(f"{p:<8} {len(items):<7} {', '.join(recons):<30} {avg_snr:.1f}")

    if errors:
        print(f"\nFirst 5 errors:")
        for e in errors[:5]:
            print(f"  {e['directory']}/{e['signal_file']}: {e['error'][:70]}")

    print(f"\nCSV:    {csv_path}")
    print(f"Output: {output_root}")
    print(f"{'=' * 80}")

    # Save full JSON results
    json_path = os.path.join(output_root, "snr_results.json")
    with open(json_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)


if __name__ == "__main__":
    main()

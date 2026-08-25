"""
Test: FA correction via app-format JSON payload (faCorrection block)

Validates that when `correction.faCorrection` is present in the reconstructor
options, the SNR pipeline:
  1. Resolves the FA map from the JSON payload (no --fa-map CLI flag needed)
  2. Produces SNR_FA_corrected.nii.gz in addition to SNR.nii.gz
  3. FA-corrected values are finite and positive where signal is present
  4. FA-corrected map is different from the raw SNR map (i.e. correction ran)

Test data required (local paths):
  signal : /data/garbage/FA-test/meas_MID01584_FID266681_gre_1H_sag_17slices.dat
  noise  : /data/garbage/FA-test/meas_MID01585_FID266682_gre_1H_noi_17slices.dat
  FA map : /data/garbage/FA-test/fa_maps/fa_product_coil.nii.gz

Usage:
    conda run -n mro python tests/test_fa_correction_app_payload.py
    conda run -n mro python tests/test_fa_correction_app_payload.py --output /tmp/fa_test_out
"""
import os
import sys
import json
import argparse
import tempfile
import subprocess
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── test data paths ────────────────────────────────────────────────────────
SIGNAL_DAT = "/data/garbage/FA-test/meas_MID01584_FID266681_gre_1H_sag_17slices.dat"
NOISE_DAT  = "/data/garbage/FA-test/meas_MID01585_FID266682_gre_1H_noi_17slices.dat"
FA_NII     = "/data/garbage/FA-test/fa_maps/fa_product_coil.nii.gz"


def build_app_payload(signal_dat, noise_dat, fa_nii):
    """Build the app-format JSON payload with faCorrection block."""
    return {
        "name": "ac",
        "queued": False,
        "version": "v0",
        "acquisition": 2,
        "type": "snr",
        "id": 0,
        "options": {
            "reconstructor": {
                "type": "recon",
                "options": {
                    "signalMultiRaid": False,
                    "sensitivityMap": {
                        "type": "sensitivityMap",
                        "name": "inner",
                        "id": 2,
                        "options": {
                            "loadSensitivity": False,
                            "sensitivityMapMethod": "inner",
                            "mask": {"method": "percentage", "value": 10},
                        },
                    },
                    "correction": {
                        "useCorrection": True,
                        "faCorrection": {
                            "type": "file",
                            "options": {
                                "type": "local",
                                "filename": fa_nii,
                                "options": {},
                            },
                        },
                    },
                    "gfactor": False,
                    "signal": {
                        "type": "file",
                        "options": {
                            "type": "local",
                            "filename": signal_dat,
                            "options": {},
                            "multiraid": False,
                            "vendor": "Siemens",
                        },
                    },
                    "noise": {
                        "type": "file",
                        "options": {
                            "type": "local",
                            "filename": noise_dat,
                            "options": {},
                            "multiraid": False,
                            "vendor": "Siemens",
                        },
                    },
                },
                "id": 1,
                "name": "b1",
            }
        },
        "files": ["signal", "noise", "faCorrection"],
    }


def run_pipeline(job_json_path, output_dir, log_path):
    """Run mrotools.snr as a subprocess (same as the app does)."""
    cmd = [
        "conda", "run", "-n", "mro",
        "python", "-m", "mrotools.snr",
        "-j", job_json_path,
        "-o", output_dir,
        "--no-parallel",
        "--no-matlab",
        "--no-coilsens",
        "--no-gfactor",
        "--no-verbose",
        "-l", log_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def check_outputs(output_dir, log_path):
    """Validate pipeline outputs. Returns list of (passed, message) tuples."""
    checks = []

    data_dir = os.path.join(output_dir, "data")

    # ── 1. Expected files exist ──────────────────────────────────────────
    for fname in ["SNR.nii.gz", "SNR_FA_corrected.nii.gz", "NC.nii.gz", "NCC.nii.gz"]:
        path = os.path.join(data_dir, fname)
        checks.append((os.path.isfile(path), f"File exists: {fname}"))

    # ── 2. Log has no ERROR entries ───────────────────────────────────────
    with open(log_path) as f:
        log = json.load(f)
    errors = [x for x in log if x.get("type") == "ERROR"]
    checks.append((len(errors) == 0, f"No errors in log (found {len(errors)}: {[e['what'] for e in errors]})"))

    # ── 3. FA map was resolved from JSON (not CLI) ────────────────────────
    fa_resolved = any("FA map resolved from JSON payload" in x.get("what", "") for x in log)
    checks.append((fa_resolved, "FA map resolved from JSON payload"))

    # ── 4. FA normalization applied ───────────────────────────────────────
    fa_applied = any("FA normalization applied" in x.get("what", "") for x in log)
    checks.append((fa_applied, "FA normalization applied successfully"))

    # ── 5. SNR_FA_corrected values are finite and positive ────────────────
    fa_path = os.path.join(data_dir, "SNR_FA_corrected.nii.gz")
    snr_path = os.path.join(data_dir, "SNR.nii.gz")
    if os.path.isfile(fa_path) and os.path.isfile(snr_path):
        try:
            from pyable_eros_montin import imaginable as ima
            fa_img  = ima.Imaginable(fa_path)
            snr_img = ima.Imaginable(snr_path)
            fa_arr  = fa_img.getImageAsNumpy()
            snr_arr = snr_img.getImageAsNumpy()

            # Mask where SNR > 1 (signal region)
            mask = snr_arr > 1.0
            n_signal = mask.sum()
            checks.append((n_signal > 0, f"Signal region found ({n_signal} voxels with SNR > 1)"))

            if n_signal > 0:
                fa_signal = fa_arr[mask]
                checks.append((np.all(np.isfinite(fa_signal)),
                                f"FA-corrected values are finite in signal region"))
                checks.append((np.all(fa_signal >= 0),
                                f"FA-corrected values are non-negative"))
                checks.append((not np.allclose(fa_arr, snr_arr),
                                "FA-corrected map differs from raw SNR map"))

                # FA correction should generally increase SNR (sin(FA) < 1 for FA < 90°)
                ratio = np.nanmedian(fa_signal / snr_arr[mask][np.isfinite(fa_signal)])
                checks.append((ratio > 1.0,
                                f"Median FA-corrected/SNR ratio > 1  (got {ratio:.2f})"))
        except Exception as e:
            checks.append((False, f"Could not read NIfTI outputs: {e}"))

    return checks


def main(output_dir=None):
    # ── Check test data exists ─────────────────────────────────────────────
    for path, label in [(SIGNAL_DAT, "signal .dat"), (NOISE_DAT, "noise .dat"), (FA_NII, "FA NIfTI")]:
        if not os.path.isfile(path):
            print(f"SKIP: {label} not found at {path}")
            sys.exit(0)

    # ── Set up temp output ─────────────────────────────────────────────────
    cleanup = output_dir is None
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="mro_fa_test_")
    os.makedirs(output_dir, exist_ok=True)

    job_path = os.path.join(output_dir, "job.json")
    log_path = os.path.join(output_dir, "log.json")

    print(f"Output dir : {output_dir}")
    print(f"Signal     : {SIGNAL_DAT}")
    print(f"Noise      : {NOISE_DAT}")
    print(f"FA map     : {FA_NII}")
    print()

    # ── Write job JSON ─────────────────────────────────────────────────────
    payload = build_app_payload(SIGNAL_DAT, NOISE_DAT, FA_NII)
    with open(job_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Job JSON written: {job_path}")

    # ── Run pipeline ───────────────────────────────────────────────────────
    print("Running pipeline (this takes ~30 s)...")
    result = run_pipeline(job_path, output_dir, log_path)

    if result.returncode != 0:
        print("PIPELINE STDERR:")
        print(result.stderr[-2000:])

    # ── Validate outputs ───────────────────────────────────────────────────
    print()
    print("=" * 60)
    checks = check_outputs(output_dir, log_path)

    passed = 0
    failed = 0
    for ok, msg in checks:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {msg}")
        if ok:
            passed += 1
        else:
            failed += 1

    print("=" * 60)
    print(f"  {passed}/{passed + failed} checks passed")
    print()

    if failed > 0:
        print(f"Output kept at: {output_dir}")
        sys.exit(1)
    else:
        print(f"All checks passed. Output: {output_dir}")
        sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test FA correction via app JSON payload")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Output directory (temp dir if omitted)")
    args = parser.parse_args()
    main(args.output)

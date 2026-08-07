"""
Batch test: run DatFileInfo on all .dat files in a directory tree.
Produces a summary table (CSV + printed) and per-file JSON reports.

Usage:
    conda run -n mro python tests/run_dat_version_batch.py \
        -i /data/MYDATA/siemensrawdataexamples/ \
        -o /g/mrotest_20260807
"""

import argparse
import json
import os
import sys
import csv
import traceback
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mrotools.dat_version import DatFileInfo


def collect_dat_files(input_path):
    """Recursively find all .dat files, skip __MACOSX and hidden dirs."""
    dat_files = []
    for root, dirs, files in os.walk(input_path):
        # Skip junk directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__MACOSX']
        for f in sorted(files):
            if f.lower().endswith('.dat') and not f.startswith('.'):
                dat_files.append(os.path.join(root, f))
    return dat_files


def process_file(dat_path, output_dir):
    """
    Process a single .dat file: extract version info, orientation, acceleration.
    Returns a result dict (or error dict).
    """
    result = {
        "filepath": dat_path,
        "filename": os.path.basename(dat_path),
        "folder": os.path.basename(os.path.dirname(dat_path)),
        "status": "OK",
        "error": None,
    }

    try:
        info = DatFileInfo(dat_path)
        result["platform"] = info.platform
        result["syngo_version"] = info.syngo_version
        result["is_multiraid"] = info.is_multiraid
        result["n_raids"] = info.n_raids
        result["signal_raid"] = info.signal_raid
        result["noise_raid"] = info.noise_raid

        # Orientation
        orient = info.orientation(0)
        result["n_slices"] = orient["n_slices"]
        result["matrix_size"] = orient["size"]
        result["spacing"] = orient["spacing"]
        result["origin"] = orient["origin"]
        result["fov"] = orient["fov"]
        result["patient_position"] = orient["patient_position"]

        # Direction check
        det = float(np.linalg.det(orient["direction"]))
        result["direction_det"] = round(det, 4)
        result["direction_valid"] = abs(abs(det) - 1.0) < 0.5

        # Acceleration
        accel, acl = info.acceleration()
        result["acceleration"] = accel
        result["acl"] = [None if (isinstance(v, float) and np.isnan(v)) else v for v in acl]

        # Scan types
        result["scan_types"] = {str(k): v for k, v in info.scan_types.items()}

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = f"{type(e).__name__}: {str(e)}"
        result["platform"] = None
        result["syngo_version"] = None

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Batch dat version test on all .dat files"
    )
    parser.add_argument("-i", "--input", required=True,
                        help="Input directory with .dat files")
    parser.add_argument("-o", "--output", required=True,
                        help="Output directory for results")
    args = parser.parse_args()

    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)

    print(f"Scanning: {args.input}")
    dat_files = collect_dat_files(args.input)
    print(f"Found {len(dat_files)} .dat files\n")

    results = []
    for idx, fpath in enumerate(dat_files):
        rel = os.path.relpath(fpath, args.input)
        print(f"[{idx+1:3d}/{len(dat_files)}] {rel} ... ", end="", flush=True)
        r = process_file(fpath, output_dir)
        results.append(r)
        if r["status"] == "OK":
            print(f"{r['platform']} ({r['syngo_version']}) "
                  f"raids={r['n_raids']} slices={r['n_slices']} "
                  f"matrix={r['matrix_size'][:2]} accel={r['acceleration']}")
        else:
            print(f"ERROR: {r['error']}")

    # --- Save full JSON results ---
    json_path = os.path.join(output_dir, "results_full.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nFull results: {json_path}")

    # --- Save CSV summary ---
    csv_path = os.path.join(output_dir, "results_summary.csv")
    fieldnames = [
        "folder", "filename", "status", "platform", "syngo_version",
        "is_multiraid", "n_raids", "n_slices", "matrix_size",
        "spacing", "origin", "fov", "patient_position",
        "direction_det", "direction_valid", "acceleration", "acl", "error"
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            row = {k: r.get(k) for k in fieldnames}
            # Flatten lists to strings for CSV
            for k in ("matrix_size", "spacing", "origin", "fov", "acceleration", "acl"):
                if row.get(k) is not None:
                    row[k] = str(row[k])
            writer.writerow(row)
    print(f"CSV summary:  {csv_path}")

    # --- Print summary table ---
    print("\n" + "=" * 100)
    print("RESULTS SUMMARY TABLE")
    print("=" * 100)

    # Group by platform
    platforms = {}
    errors = []
    for r in results:
        if r["status"] == "OK":
            p = r["platform"]
            if p not in platforms:
                platforms[p] = []
            platforms[p].append(r)
        else:
            errors.append(r)

    print(f"\n{'Platform':<8} {'Count':<7} {'Versions':<30} {'Multiraid':<12} {'Slices range':<15} {'Accel'}")
    print("-" * 100)
    for platform in sorted(platforms.keys()):
        items = platforms[platform]
        versions = sorted(set(r["syngo_version"] for r in items))
        multiraid_vals = set(r["is_multiraid"] for r in items)
        slice_counts = [r["n_slices"] for r in items]
        accels = set(str(r["acceleration"]) for r in items)
        print(f"{platform:<8} {len(items):<7} {', '.join(versions):<30} "
              f"{str(multiraid_vals):<12} "
              f"{min(slice_counts)}-{max(slice_counts):<10} "
              f"{', '.join(sorted(accels))}")

    if errors:
        print(f"\nERRORS: {len(errors)}")
        for e in errors[:10]:
            print(f"  {e['folder']}/{e['filename']}: {e['error']}")
        if len(errors) > 10:
            print(f"  ... and {len(errors)-10} more")

    # --- Summary stats ---
    total = len(results)
    ok = len([r for r in results if r["status"] == "OK"])
    print(f"\n{'=' * 100}")
    print(f"TOTAL: {total} files | OK: {ok} | ERRORS: {total - ok}")
    print(f"PLATFORMS TESTED: {sorted(platforms.keys())}")
    all_versions = sorted(set(r["syngo_version"] for r in results if r.get("syngo_version")))
    print(f"VERSIONS FOUND:  {all_versions}")
    print(f"{'=' * 100}")

    # Save the summary stats
    stats = {
        "total_files": total,
        "ok": ok,
        "errors": total - ok,
        "platforms": {p: len(v) for p, v in platforms.items()},
        "all_versions": all_versions,
        "error_files": [{"file": e["filepath"], "error": e["error"]} for e in errors],
    }
    stats_path = os.path.join(output_dir, "stats.json")
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"\nStats: {stats_path}")


if __name__ == "__main__":
    main()

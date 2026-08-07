---
inclusion: auto
---

# MROptimum-Tools Codebase Index

## Project Overview
MR Optimum Tools (`mrotools`) is a Python package for SNR (Signal-to-Noise Ratio) calculation in MRI.
It reads Siemens raw data (.dat) or numpy/MATLAB files, performs coil combination reconstructions
(RSS, B1, SENSE, GRAPPA), and computes SNR maps using analytical (Kellman) or statistical
(Multiple Replicas, Pseudo-MR, Generalized PMR) methods.

- **Package**: `mrotools` v3.0.0 (on `dev_filetypes` branch)
- **Python**: 3.10+ (conda env: `mro`)
- **Run commands**: `conda run -n mro <command>`
- **Test command**: `conda run -n mro python -m pytest tests/ -v`

## Branch: `dev_filetypes` (active development)

### Core Library (`mrotools/`)

| File | Purpose |
|------|---------|
| `mro.py` | Core SNR functions: reconstructors, k-space extraction, orientation parsing, SNR calculators (Kellman, MR, PMR, CR). Imports from `cmtools`. |
| `snr.py` | CLI entry point (`python -m mrotools.snr -j config.json -o output/`). Parses JSON config, uses `kspace_loaders` factory, dispatches to parallel SNR computation. |
| `kspace_loaders.py` | Abstract `KSpaceLoader` + implementations: `SiemensLoader`, `NumpyLoader`, `MatlabLoader`. Factory: `get_kspace_loader(vendor)`. |
| `dat_version.py` | Version detection: `DatFileInfo` class identifies VB/VD/VE/XA platform, extracts orientation/acceleration version-aware. |
| `generate.py` | JSON config generator for different recon/SNR method combinations. |
| `generate-ui.py` | Tkinter GUI wrapper for generate.py. |

### Tools (`tools/`)

| File | Purpose |
|------|---------|
| `dat2numpy.py` | Siemens .dat -> .npz converter. Extracts signal, noise, reference + metadata. Auto-detects version. |
| `dat_inventory.py` | Full inventory of a .dat file: all raids, all scan types -> .npz + PNG previews + manifest JSON. |
| `file_type_inventory.py` | Multi-format handler (DAT/ISMRMRD/MAT) -> .npz inventory. |
| `ismrmrd2numpy.py` | ISMRMRD .h5 -> .npz converter. |

### Tests (`tests/`)

| File | Purpose |
|------|---------|
| `test_dat_version.py` | 75 unit tests for version detection + integration test CLI for real .dat files. |
| `test_numpy_snr.py` | End-to-end: synthetic phantom -> numpy -> SNR pipeline. |

### Dependencies
- `cmtools` (git: cloudmrhub/cloudmr-tools) - reconstruction math
- `raider_eros_montin` (git: erosmontin/raider) - multiraid noise extraction
- `pynico_eros_montin` (git: erosmontin/pynico@v2) - utilities, JSON, logging
- `pyable_eros_montin` (git: erosmontin/pyable@v2) - image I/O (NIfTI, etc.)
- `twixtools` - Siemens .dat file parsing
- `numpy`, `scipy`, `matplotlib`, `pydicom`, `SimpleITK`, `PIL`

## Siemens .dat File Versions

| Platform | Format | Raids | Key Differences |
|----------|--------|-------|-----------------|
| VB | Single-raid | 1 | Signal at raid 0, separate noise file, `relSliceNumber` for ordering |
| VD | Multi-raid | 2+ | Noise at raid 0, signal at last raid, `chronSliceIndices` |
| VE | Multi-raid | 2+ | Same as VD with minor header changes |
| XA | Multi-raid | 2+ | Patient position at `sPatPosition` instead of `tPatientPosition` |

Detection:
- Binary: `twixtools.helpers.idea_version_check(fid)` -> (is_ve, n_scans)
- Header: `twixtools.helpers.get_syngo_version(hdr)` -> version string
- Combined: `mrotools.dat_version.DatFileInfo(path)` -> full metadata

## JSON Config Format (v0)
```json
{
  "version": "v0",
  "acquisition": 2,
  "name": "AC|MR|PMR|CR",
  "options": {
    "reconstructor": {
      "name": "RSS|B1|Sense|Grappa",
      "options": {
        "signal": {"type": "file", "options": {"vendor": "siemens|numpy|matlab", "filename": "...", "multiraid": bool}},
        "noise": {...},
        "sensitivityMap": {...},
        "accelerations": [1, 2],
        "acl": [null, 24]
      }
    }
  }
}
```

## Key Architectural Patterns
- **Vendor abstraction**: `kspace_loaders.py` factory pattern lets SNR pipeline work with any input format
- **Per-slice parallelism**: `snr.py` builds a TASK list (one dict per slice) and maps through `multiprocessing.Pool`
- **Orientation from headers**: `Phoenix.sSliceArray.asSlice[i].sPosition/sNormal` for origin/direction
- **Version-aware extraction**: `dat_version.DatFileInfo` handles all platform differences transparently

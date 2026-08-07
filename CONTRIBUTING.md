# Contributing & Developer Testing Guide

This document explains how to set up a development environment, run tests, and validate the package before merging into `main`.

---

## Repository Layout (relevant to testing)

```
mrotools/
├── snr.py                  # CLI entry point
├── mro.py                  # core SNR/recon logic
├── kspace_loaders.py       # multi-vendor k-space loaders
└── collections/            # example JSON configs (one per SNR method/vendor)
    ├── AC/                 # Analytical / Kellman (Siemens .dat)
    ├── MR/                 # Multiple Replicas
    ├── PMR/                # Pseudo Multiple Replicas
    ├── CR/                 # Coil Replica
    ├── numpy/              # NumPy input files
    ├── matlab/             # MATLAB input files
    └── misc/               # miscellaneous

tests/
├── test_numpy_snr.py           # self-contained pytest suite (no data files needed)
├── run_all_collections.py      # Python batch runner for all collection JSONs
└── test_collections.sh         # Shell script: env setup + batch run + summary
```

---

## 1 — Set Up a Test Environment

Use an isolated conda environment to avoid touching your production `able` env.

```bash
# Create (skipped automatically if already exists)
conda create -n mrotools-test python=3.11 -y
conda activate mrotools-test

# Install the package in editable mode from the current branch
pip install -e .
```

> **Tip:** The `tests/test_collections.sh` script handles env creation and package installation automatically — see Section 3.

---

## 2 — Self-Contained Tests (no MRI data files required)

The pytest suite in `tests/test_numpy_snr.py` uses bundled `.npy` files and validates the core SNR logic end-to-end.

```bash
conda activate mrotools-test
python -m pytest tests/test_numpy_snr.py -v
```

Run this first — it is the fastest way to confirm nothing is broken.

---

## 3 — Batch Test All Collection JSON Configs

Collection JSONs point to real MRI data files (`.dat`, `.npy`, `.mat`) on disk. Tests are classified as:

| Result | Meaning |
|--------|---------|
| `✓ OK` | Config ran successfully |
| `⚠ SKIP` | Data file not on this machine — not a code bug |
| `✗ FAILED` | Real error — must be fixed before merging |

### Option A — Shell script (recommended)

Handles env creation, package install, and batch run in one command:

```bash
bash tests/test_collections.sh
```

Optional flags:
```bash
bash tests/test_collections.sh --output /tmp/my_output/
bash tests/test_collections.sh --collections mrotools/collections/AC   # subset only
```

### Option B — Python runner

```bash
conda activate mrotools-test
python tests/run_all_collections.py
python tests/run_all_collections.py --output /tmp/my_output/
python tests/run_all_collections.py --collections mrotools/collections/AC
```

### Option C — Single config manually

```bash
conda activate mrotools-test
python mrotools/snr.py \
    -j mrotools/collections/AC/b1_settings_20.json \
    -o /tmp/snr_test/ \
    --no-verbose \
    --no-gfactor
```

---

## 4 — VS Code Debug Configurations

Open `mrotools/snr.py` in the editor, then use the **Run and Debug** panel (`Ctrl+Shift+D`) to launch any of the 34 named configurations from `.vscode/launch.json`.

Each config maps to one collection JSON. Useful for stepping through the code with a real dataset.

---

## 5 — Merging into `main`

Only merge after all of the following pass:

- [ ] `pytest tests/test_numpy_snr.py` — all green
- [ ] `bash tests/test_collections.sh` — zero `✗ FAILED` results (`⚠ SKIP` is acceptable)
- [ ] Manual spot-check of at least one Siemens `.dat` config if data is available

Then:

```bash
git checkout main
git merge origin/dev_filetypes          # or your feature branch
# resolve any conflicts (typically pyproject.toml version + .vscode/launch.json)
git tag vX.Y.Z
git push origin main --tags
git push origin --delete dev_filetypes  # clean up after merge
```

---

## 6 — Updating the Remote URL

The repo has moved. Update your local remote to avoid redirect warnings:

```bash
git remote set-url origin https://github.com/cloudmrhub/mroptimum-tools.git
```

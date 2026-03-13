# **MR Optimum — SNR Tools**

![License](https://img.shields.io/github/license/cloudmrhub/mroptimum-tools)
![GitHub last commit](https://img.shields.io/github/last-commit/cloudmrhub/mroptimum-tools)
![GitHub issues](https://img.shields.io/github/issues/cloudmrhub/mroptimum-tools)
![GitHub forks](https://img.shields.io/github/forks/cloudmrhub/mroptimum-tools)
![GitHub stars](https://img.shields.io/github/stars/cloudmrhub/mroptimum-tools)

**MR Optimum** provides tools for advanced signal-to-noise ratio (SNR) estimation and image reconstruction methods for Magnetic Resonance Imaging (MRI). It is designed for researchers and developers to efficiently perform SNR calculations, reconstructions, and custom pipeline configurations.

---

## ⚙️ **Repository Structure**

### **1. 🐍 `mrotools/` — Core Source Code**

| File / Subfolder | Description |
| ---------------- | ----------- |
| `mro.py` | Core SNR and reconstruction method definitions: RSS, B1, SENSE, GRAPPA; multiple-replica and pseudo-multiple-replica methods. |
| `snr.py` | CLI entry point (`python -m mrotools.snr`) for running SNR calculations from a JSON configuration file. |
| `generate.py` | Programmatic helpers to build JSON configuration objects for each SNR/recon type. |
| `generate-ui.py` | Tkinter-based GUI for interactively building JSON configs and launching calculations. |
| `kspace_loaders.py` | Multi-vendor k-space loaders (Siemens, NumPy, MATLAB) with factory pattern. |
| `collections/` | Example JSON configurations organized by SNR method (AC/, MR/, PMR/, CR/, numpy/, matlab/, misc/). |

---

### **1b. 🔧 `tools/` — Conversion Utilities**

| File | Description |
| ---- | ----------- |
| `dat2numpy.py` | Convert Siemens `.dat` raw data to `.npz` files with embedded orientation and acceleration metadata. |
| `dat_inventory.py` | Full inventory of a Siemens `.dat` file: exports every raid/scan-type as `.npz` + RSS preview PNG + `inventory.json` manifest. Intended for upload backends to present all available data to the user before SNR calculation. |
| `ismrmrd2numpy.py` | Convert ISMRMRD `.h5` raw data (vendor-neutral format) to `.npz` files. Requires `pip install ismrmrd`. |

---

### **2. 📋 `json/` & `mrotools/collections/` — Example Configurations**

```
mrotools/collections/
├── AC/        # Analytical / Kellman configs (Siemens)
├── MR/        # Multiple Replicas configs (Siemens)
├── PMR/       # Pseudo Multiple Replicas configs (Siemens)
├── CR/        # Coil Replica / Generalized PMR configs (Siemens)
├── numpy/     # Example configs for NumPy input files
├── matlab/    # Example configs for MATLAB input files
└── misc/      # Miscellaneous example configs

json/
├── acsense.json
├── pmrsense.json
└── crsense.json
```

---

### **3. 📓 Notebooks**

| Notebook | Description |
| -------- | ----------- |
| `cloudmr_tools.ipynb` | Demonstrates integration with the cloudmr-tools library. |
| `mroptimum_tools.ipynb` | End-to-end walkthrough of SNR calculations using mrotools. |
| `snr_flowchart.ipynb` | Visual flowchart of the SNR pipeline. |

---

## 🔌 **SNR Methods & Reconstructors**

### SNR Methods

| ID | Name | Description |
| -- | ---- | ----------- |
| 0 | **AC** | Analytical / Kellman method. |
| 1 | **MR** | Multiple Replicas. |
| 2 | **PMR** | Pseudo Multiple Replicas. |
| 3 | **CR** | Coil Replica / Generalized Pseudo Multiple Replicas (Weiner). |

### Reconstructors

| ID | Name | Description |
| -- | ---- | ----------- |
| 1 | **RSS** | Root Sum of Squares reconstruction. |
| 2 | **B1** | B1-weighted reconstruction. |
| 3 | **SENSE** | SENSE reconstruction. |
| 4 | **GRAPPA** | GRAPPA reconstruction. |

---

## � **Supported Input File Formats**

MR Optimum supports three k-space input formats. Set `"vendor"` in the JSON config to select the loader.

| Vendor     | Extension(s)         | Description                                    |
| ---------- | -------------------- | ---------------------------------------------- |
| `siemens`  | `.dat`               | Siemens raw data via twixtools                 |
| `numpy`    | `.npy`, `.npz`       | NumPy arrays with optional orientation         |
| `matlab`   | `.mat`               | MATLAB v5 / v7.3 files with optional orientation |

### K-Space Array Shape Convention

All formats expect the k-space array shaped as:

| Dimensions | Shape                             | Use case                  |
| ---------- | --------------------------------- | ------------------------- |
| 3-D        | `(freq, phase, coils)`            | Single 2-D slice          |
| 4-D        | `(freq, phase, coils, slices)`    | Multi-slice               |
| 4-D (MR)   | `(freq, phase, coils, replicas)`  | Single-slice Multiple Replicas |
| 5-D        | `(freq, phase, coils, slices, replicas)` | Multi-slice Multiple Replicas |

### Orientation Metadata

Orientation is resolved with **three-level priority**:

1. **JSON `"orientation"` block** in the config (highest priority)
2. **Embedded in the file** (`.npz` keys or `.mat` variables)
3. **Defaults**: spacing = `[1, 1, 1]` mm, origin = `[0, 0, 0]`, direction = `eye(3)`

This means **a bare `.npy` or `.mat` file with only k-space data works out of the box** – orientation defaults to 1 mm isotropic.

| Field       | Type             | Description                              |
| ----------- | ---------------- | ---------------------------------------- |
| `spacing`   | array of 3       | Voxel size in mm: `[dx, dy, dz]`        |
| `origin`    | array of 3       | Image origin: `[ox, oy, oz]`            |
| `direction` | array of 9       | Row-major 3×3 direction cosine matrix    |
| `fov`       | array of 3       | Field of view in mm: `[fov_f, fov_p, fov_s]` |

---

### Writing NumPy Files

#### Minimal (just k-space):

```python
import numpy as np

# kspace shape: (frequency, phase, coils) for a single 2D slice
kspace = np.array(...)  # complex64 or complex128
np.save("signal.npy", kspace)
np.save("noise.npy", noise_kspace)
```

#### With embedded orientation (`.npz`):

```python
np.savez("signal.npz",
    kspace       = kspace,                                      # required
    spacing      = np.array([1.0, 1.0, 5.0]),                  # optional
    origin       = np.array([0.0, 0.0, 0.0]),                  # optional
    direction    = np.array([1,0,0, 0,1,0, 0,0,1], dtype=float), # optional (9 elems)
    fov          = np.array([256.0, 256.0, 50.0]),              # optional
    acceleration = np.array([1, 2]),                            # optional (freq, phase)
    acl          = np.array([0, 24]),                           # optional (autocalibration lines)
    reference    = reference_kspace,                            # optional (ACS data, same shape as kspace)
)
```

#### Multi-slice:

```python
# shape: (freq, phase, coils, n_slices)
kspace_multislice = np.stack([slice0, slice1, slice2], axis=3)
np.save("signal_multislice.npy", kspace_multislice)
```

---

### Writing MATLAB Files

#### From MATLAB:

```matlab
% kspace: complex array of size (freq, phase, coils)
kspace  = complex_kspace_data;      % required
spacing = [1.0, 1.0, 5.0];         % optional
origin  = [0.0, 0.0, 0.0];         % optional
direction = [1,0,0, 0,1,0, 0,0,1]; % optional (9 elements, row-major)
fov     = [256.0, 256.0, 50.0];    % optional

save('signal.mat', 'kspace', 'spacing', 'origin', 'direction', 'fov');
% or minimal:
save('signal.mat', 'kspace');
```

#### From Python:

```python
import scipy.io as sio

sio.savemat("signal.mat", {
    "kspace":  kspace,                          # required – complex array
    "spacing": np.array([1.0, 1.0, 5.0]),      # optional
    "origin":  np.array([0.0, 0.0, 0.0]),      # optional
})
```

---

### JSON Configuration for NumPy / MATLAB

A minimal JSON config using NumPy (RSS + Analytical):

```json
{
    "version": "v0",
    "acquisition": 2,
    "type": "SNR",
    "name": "AC",
    "options": {
        "reconstructor": {
            "type": "recon",
            "name": "RSS",
            "options": {
                "signal": {
                    "type": "file",
                    "options": {
                        "vendor": "numpy",
                        "filename": "/path/to/signal.npy"
                    }
                },
                "noise": {
                    "type": "file",
                    "options": {
                        "vendor": "numpy",
                        "filename": "/path/to/noise.npy"
                    }
                }
            }
        }
    }
}
```

For MATLAB, change `"vendor": "numpy"` → `"vendor": "matlab"` and point to `.mat` files.

To override orientation from JSON (takes priority over file-embedded values):

```json
"options": {
    "vendor": "numpy",
    "filename": "/path/to/signal.npy",
    "orientation": {
        "spacing": [0.5, 0.5, 3.0],
        "origin":  [10.0, 20.0, 30.0]
    }
}
```

See `mrotools/collections/numpy/` and `mrotools/collections/matlab/` for full examples.

---

### Acceleration & Reference Metadata

For accelerated acquisitions (SENSE / GRAPPA), the loader resolves acceleration info with the same three-level priority:

1. **JSON keys** `"accelerations"` and `"acl"` in the reconstructor options
2. **Embedded in the file** (`.npz` keys `acceleration`, `acl`; `.mat` variables)
3. **Defaults**: `[1, 1]` (no acceleration) / `[NaN, NaN]`

Reference / ACS k-space can be supplied as:
- A separate file via `"reference_filename"` in the JSON config
- Embedded inside the signal `.npz` file with the key `reference`

---

### Siemens `.dat` → NumPy Converter

The `tools/dat2numpy.py` script converts Siemens raw data into self-contained `.npz` files:

```bash
# Multiraid file (noise embedded in raid 0)
conda run -n mro python tools/dat2numpy.py \
    -i /path/to/signal.dat \
    -o /path/to/output_dir/ \
    --multiraid

# Separate noise file
conda run -n mro python tools/dat2numpy.py \
    -i /path/to/signal.dat \
    --noise /path/to/noise.dat \
    -o /path/to/output_dir/

# No noise flag — prescan noise is extracted automatically from the signal file
conda run -n mro python tools/dat2numpy.py \
    -i /path/to/signal.dat \
    -o /path/to/output_dir/

# Multiple Replicas (MR) data
conda run -n mro python tools/dat2numpy.py \
    -i /path/to/signal.dat \
    -o /path/to/output_dir/ \
    --multiraid --mr
```

**Noise source priority:**

| Priority | Source | When |
|----------|--------|------|
| 1 | `--multiraid` | Multiraid file; full noise scan in raid 0 |
| 2 | `--noise path` | Separate noise `.dat` file |
| 3 | Auto-fallback | Prescan noise (`noise` key) embedded in the signal file. Every Siemens scan includes a brief noise pre-adjustment (NOISEADJSCAN). Shape: `(cols, 1, coils)`. |

**Output files:**

| File              | Contents                                                      |
| ----------------- | ------------------------------------------------------------- |
| `signal.npz`      | Signal k-space + orientation + acceleration + ACL metadata    |
| `noise.npz`       | Noise k-space                                                 |
| `reference.npz`   | Reference / ACS k-space (only for accelerated acquisitions)   |
| `config_numpy.json`| Ready-to-use JSON config for the MR Optimum SNR pipeline     |

Each `.npz` file is self-contained — orientation and acceleration metadata are embedded alongside the k-space data, so the JSON config can be minimal.

---

## �🚀 **Getting Started**

1. Install **Python ≥ 3.9**.

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv MRO
   source MRO/bin/activate
   ```

3. Install the package:

   ```bash
   pip install git+https://github.com/cloudmrhub/mroptimum-tools.git
   ```

4. Run an SNR calculation from the CLI:

   ```bash
   python -m mrotools.snr -j /path/to/config.json -o /output/path/ -c True -g True -v True -m True
   ```

   Flags: `-j` JSON config path, `-o` output directory, `-c` save combined output, `-g` generate plots, `-v` verbose logging, `-m` save individual method outputs.

5. Example JSON configuration (GRAPPA + PMR):

   ```json
   {
       "version": "v0",
       "acquisition": 2,
       "type": "SNR",
       "id": 2,
       "name": "PMR",
       "options": {
           "NR": 20,
           "reconstructor": {
               "type": "recon",
               "name": "GRAPPA",
               "id": 4,
               "options": {
                   "noise": {
                       "type": "file",
                       "options": {
                           "filename": "/data/PROJECTS/mroptimum/_data/noise.dat",
                           "vendor": "Siemens"
                       }
                   },
                   "signal": {
                       "type": "file",
                       "options": {
                           "filename": "/data/PROJECTS/mroptimum/_data/signal.dat",
                           "vendor": "Siemens"
                       }
                   }
               }
           }
       }
   }
   ```

---


---

## 🌐 **Live Example**

Try MR Optimum in your browser — no installation required:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1-8wcaS9IBZ5aCcLvwY6D3mhwcNxlJr4y?usp=sharing)

---

## **Versioning**

The **MR Optimum** package has two versions:

| Feature | Version 1 (`v1`) | Version 2 (`main`) |
| ------- | ---------------- | ------------------ |
| Name | `mroptimum` | `mroptimum-tools` / `mrotools` |
| Maintenance | Deprecated | Actively maintained |
| Compatibility | Legacy projects | New and legacy projects |
| Features | Limited | GUI tools, expanded options |

**Version 1 (Deprecated)** — still functional for backward compatibility, but no longer receives updates or bug fixes:
```bash
pip install git+https://github.com/cloudmrhub/mroptimum-tools.git@v1
```

**Version 2 (Current)** — recommended for all new projects:
```bash
pip install git+https://github.com/cloudmrhub/mroptimum-tools.git
```

---

## 💬 **Acknowledgments**

This work is supported in part by NIH grants and performed under the **Center for Advanced Imaging Innovation and Research (CAI²R)**, an NIH National Center for Biomedical Imaging and Bioengineering (P41 EB017183).

---

## ⚠️ **Disclaimer**

This is a research tool intended for academic and research purposes. While every effort has been made to ensure its quality, the software may contain bugs. We do not assume responsibility for any errors or issues resulting from its use. We encourage users to report errors, warnings, and questions via the [Issues](https://github.com/cloudmrhub/mroptimum-tools/issues) page.

---

## 📃 **License**

MR Optimum is released under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## 👥 **Contributors**

[*Dr. Eros Montin, PhD*](http://me.biodimensional.com)\
[![GitHub](https://img.shields.io/badge/GitHub-erosmontin-blue)](https://github.com/erosmontin)\
[![ORCID](https://img.shields.io/badge/ORCID-0000--0002--1773--0064-green)](https://orcid.org/0000-0002-1773-0064)\
[![Scopus](https://img.shields.io/badge/Scopus-35604121500-orange)](https://www.scopus.com/authid/detail.uri?authorId=35604121500)

[*Prof. Riccardo Lattanzi, PhD*](https://med.nyu.edu/faculty/riccardo-lattanzi)\
[![GitHub](https://img.shields.io/badge/GitHub-rlattanzi-blue)](https://github.com/rlattanzi)\
[![ORCID](https://img.shields.io/badge/ORCID-0000--0002--8240--5903-green)](https://orcid.org/0000-0002-8240-5903)\
[![Scopus](https://img.shields.io/badge/Scopus-6701330033-orange)](https://www.scopus.com/authid/detail.uri?authorId=6701330033)

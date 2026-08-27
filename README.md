# **MR Optimum — Backend Tools**

Visit the [project page](https://cmr.cloudmrhub.com/apps/mroptimum/) for more information about MR Optimum.

![License](https://img.shields.io/github/license/cloudmrhub/mroptimum-tools)
![GitHub last commit](https://img.shields.io/github/last-commit/cloudmrhub/mroptimum-tools)
![GitHub issues](https://img.shields.io/github/issues/cloudmrhub/mroptimum-tools)
![GitHub forks](https://img.shields.io/github/forks/cloudmrhub/mroptimum-tools)
![GitHub stars](https://img.shields.io/github/stars/cloudmrhub/mroptimum-tools)

### Tested Siemens Raw Data Versions

![VB13](https://img.shields.io/badge/Siemens-VB13-green)
![VB15](https://img.shields.io/badge/Siemens-VB15-green)
![VB17](https://img.shields.io/badge/Siemens-VB17-green)
![VB20](https://img.shields.io/badge/Siemens-VB20-green)
![VD11](https://img.shields.io/badge/Siemens-VD11-green)
![VD13](https://img.shields.io/badge/Siemens-VD13-green)
![VE11](https://img.shields.io/badge/Siemens-VE11-green)
![XA51](https://img.shields.io/badge/Siemens-XA51-green)
![XA61](https://img.shields.io/badge/Siemens-XA61-green)

**MR Optimum** provides tools for signal-to-noise ratio (SNR) estimation and image reconstruction methods for Magnetic Resonance Imaging (MRI). It is designed for researchers and developers to perform SNR calculations, reconstructions, and custom pipeline configurations.

---

## ⚙️ **Repository Structure**

### **1. 🐍 `mrotools/` — Core Source Code**

| File / Subfolder | Description |
| ---------------- | ----------- |
| `mro.py` | Core SNR and reconstruction method definitions: RSS, B1, SENSE, GRAPPA; multiple-replica and pseudo-multiple-replica methods. |
| `snr.py` | CLI entry point (`python -m mrotools.snr`) for running SNR calculations from a JSON configuration file. |
| `generate.py` | Programmatic helpers to build JSON configuration objects for each SNR/recon type. |
| `generate-ui.py` | Tkinter-based GUI for interactively building JSON configs and launching calculations. |
| `kspace_loaders.py` | Multi-vendor k-space loaders (Siemens, NumPy, MATLAB) with factory pattern. The Siemens loader computes the correct NIfTI origin (slice center → first-voxel corner) and derives true inter-slice spacing from sorted physical slice positions, correctly handling interleaved acquisition and slice gaps. |
| `fa_normalization.py` | FA correction module: loads a user-supplied flip-angle map, resamples it onto the SNR grid with cubic B-spline interpolation (clamped to [0°, 180°]), inpaints near-zero sin(FA) boundary voxels via a 3×3×3 median filter, then computes `SNR / sin(FA)`. See section 1c. |
| `collections/` | Example JSON configurations organized by SNR method (AC/, MR/, PMR/, CR/, numpy/, matlab/, misc/). |

---

### **1c. 🧲 FA Normalization (`fa_normalization.py`)**

Converts raw SNR maps to **SNR at 90° flip angle** using a user-supplied FA map:

$$\text{SNR}_{90} = \frac{\text{SNR}}{\sin(\text{FA})}$$

This matches the formula in Ryan Brown's `snr_90_analysis.m` (line 1566).

#### CLI usage

Pass `--fa-map` to the SNR command:

```bash
python -m mrotools.snr \
    -j config.json \
    -o /output/dir/ \
    --fa-map /path/to/fa_map.nii.gz \
    --fa-interpolation bspline
```

The FA map must be in **degrees**. It does not need to share the same grid as the
SNR map — resampling is applied automatically. Cubic B-spline is the production
default; the explicit option above documents the choice in a reproducible command.

#### Preparing a Siemens GRE FA map from DICOM

Siemens stores the actual FA map as pixel value × 0.1 (i.e. `pixel / 10` gives
degrees). If the GRE nominal FA differs from the TFL prescribed FA used for the
map, apply the standard scale:

```python
import SimpleITK as sitk
import numpy as np

img = sitk.ReadImage('fa_map_dcm2nii.nii.gz')
arr = sitk.GetArrayFromImage(img).astype(np.float32)

GRE_nominal  = 75.0   # degrees — flip angle of your SNR scan
TFL_prescribed = 80.0 # degrees — flip angle prescribed for the TFL B1 map

fa_degrees = (arr / 10.0) * (GRE_nominal / TFL_prescribed)

out = sitk.GetImageFromArray(fa_degrees)
out.CopyInformation(img)
sitk.WriteImage(out, 'fa_gre.nii.gz')
```

#### Pipeline internals

| Step | Details |
|------|---------|
| **Load** | Any SimpleITK-readable format (NIfTI, MHA, …) |
| **Geometry check** | `isImaginableInTheSameSpace` — skip resampling if already aligned |
| **Resample** | Cubic B-spline (`sitk.sitkBSplineResampler`) onto SNR grid; result clamped to [0°, 180°] |
| **Inpaint** | Near-zero `\|sin(FA)\| < 0.02` voxels (BSpline fringe at FOV boundary) are replaced by a 3×3×3 median of their neighbours |
| **Mask** | Voxels still near-zero after inpainting (isolated deep background) → `NaN` → zeroed by snr.py cleanup |
| **Correct** | `SNR_corrected = SNR / sin(FA_resampled)` |

#### Output files

When `--fa-map` is supplied, two extra files appear in the output directory:

| File | Contents |
|------|----------|
| `SNR_FA_corrected.nii.gz` | Complex FA-corrected SNR map |
| `FA_on_SNR.nii.gz` | FA map resampled onto the SNR grid (degrees, float32) — useful for QC |

#### Colab example with real validation data

The [Google Colab notebook](mroptimum_tools.ipynb) contains a self-contained
**B-spline FA normalization (SNR90°)** section. It downloads
[`data/fa90_example_slice.pkl`](data/fa90_example_slice.pkl), a single slice
from the product-coil validation dataset containing:

- the original complex SNR at 256×256;
- the native FA map at 64×64 in degrees; and
- the origin, spacing, and direction of both grids.

The example reconstructs both image geometries, resamples FA onto the SNR grid
with the production cubic B-spline path, computes `SNR / sin(FA)`, writes the
corrected image as `FA90°.nii.gz`, and plots `abs(SNR)`, the resampled FA map,
and `abs(SNR90°)`. The committed pickle can be regenerated from the private
validation volumes with:

```bash
conda run -n mro python tools/build_fa_colab_example_data.py
```

#### Provenance

The log file records full provenance for every run:

```json
{
  "faCorrectionApplied": true,
  "faUnits": "degrees",
  "faCorrectionMethod": "snr_over_sin_fa",
  "faInterpolation": "bspline",
  "epsilonThreshold": 0.02,
  "fillWindow": 3,
  "nNearZeroVoxelsDetected": 25745,
  "nNearZeroVoxelsInpainted": 605,
  "nNearZeroVoxelsMasked": 25140,
  "faMin": 0.0,
  "faMax": 180.0
}
```

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

## **Tutorial**

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

## � **Riccardo Lattanzi SNR Toolbox — Python Porting Notes**

This section documents the mathematical and algorithmic correspondence between
the original MATLAB SNR toolbox (`snr_toolbox_batch.m`, Riccardo Lattanzi /
Ryan Brown, NYU) and the mroptimum-tools Python implementation.  It is intended
as a reference for cross-validation and for understanding what each processing
step does and why.

---

### Pipeline Overview

Both pipelines follow the same five-step sequence:

```
Raw k-space (.dat)
      │
      ▼
1. Read & extract k-space     mapVBVD (MATLAB)  /  twixtools (Python)
      │
      ▼
2. Noise covariance Ψ         calc_noise_cov.m  /  calculteNoiseCovariance()
      │
      ▼
3. Image reconstruction       MRifft + crop     /  cm2DKellman*.getOutput()
      │
      ▼
4. Analytical SNR map         mrir_array_SNR_*  /  cm2DKellman*.getOutput()
      │
      ▼
5. FA correction (optional)   snr_90_analysis.m /  fa_normalization.py
```

---

### Step 1 — K-Space Reading

**MATLAB (`snr_toolbox_batch.m`):**

```matlab
twix_obj    = mapVBVD(data_file);           % read entire .dat file
noise_obj   = twix_obj.noise.unsorted();    % embedded prescan noise
kdata       = twix_obj.image();             % signal k-space object

% Extract one slice: permute to [nfreq, nphase, ncoil]
signalrawdata = permute(squeeze(kdata(:,:,:,:,islice,...)),[1,3,2]);
signalrawdata = signalrawdata * K_ICE_AMPL_SCALE_FACTOR;  % amplitude scaling
noiserawdata  = permute(squeeze(noise_obj(:,:,:,:,1,...)), [1,3,2]);
noiserawdata  = noiserawdata  * K_ICE_AMPL_SCALE_FACTOR;
```

`K_ICE_AMPL_SCALE_FACTOR` is a fixed Siemens constant (≈ 4096 for most platforms)
that converts the raw ADC integers to physically meaningful units.

**Python (`kspace_loaders.py` / `mro.py` / twixtools):**

```python
loader = get_kspace_loader('siemens')
SL    = loader.get_signal_kspace(options, signal=True)   # list of slice dicts
NOISE = loader.get_noise_kspace(options, 'all')          # noise slices
```

twixtools applies the same `K_ICE_AMPL_SCALE_FACTOR` internally.  Each element
of `SL` is a dict with keys `KSpace` (freq × phase × coil, complex64),
`spacing`, `origin`, `direction`, `fov`.

**Geometry fixes applied in Python (not in MATLAB):**
- `sPosition` (slice centre) converted to first-voxel corner for correct NIfTI
  origin: `corner = centre − (N_ro/2)·dr·r̂ − (N_pe/2)·dp·p̂`
- True inter-slice spacing derived from sorted physical slice positions (handles
  interleaved acquisition and slice gap):
  `dz = median(|pos[i+1] − pos[i]|)` for positions projected onto slice normal.

---

### Step 2 — Noise Covariance Matrix

Both implementations compute the same **Siemens noise covariance** formula:

$$\Psi_{jk} = \frac{1}{N} \sum_{n=1}^{N} \eta_j[n] \cdot \eta_k^*[n]$$

where $\eta_j[n]$ is noise sample $n$ on coil $j$ and $N$ is the total number of
noise samples.

**MATLAB (`calc_noise_cov.m`):**

```matlab
for iCh = 1:nchan
    for jCh = 1:nchan
        noisecov(iCh,jCh) = sum(sum(noise(:,:,iCh) .* conj(noise(:,:,jCh)))) ...
                             / (size(noise,1) * size(noise,2));
    end
end
% optional: divide by noise_bandwidth (BW correction)
if bw_correction
    noise_bandwidth = mrir_noise_bandwidth(noise);
    noisecov = noisecov / noise_bandwidth;
end
```

**Python (`cm2DRecon.getNoiseCovariance()` via `calculteNoiseCovariance()`):**

```python
NC, NCC = calculteNoiseCovariance(NOISE, verbose=False)
# NC  = Ψ  (coil × coil, complex128)
# NCC = Ψ / sqrt(diag(Ψ) · diag(Ψ)ᵀ)  — correlation coefficients
```

The Python implementation concatenates all noise slices along the phase
dimension before computing Ψ, which is equivalent to increasing $N$ and gives a
more stable estimate.

---

### Step 3 — Image Reconstruction (ifft2 + crop)

**MATLAB:**

```matlab
img_matrix = MRifft(signalrawdata, [1, 2]);   % centred ifft2 (ifftshift + ifft)
img_matrix = img_matrix * sqrt(nrow * ncol);  % undo the ifft normalisation

% Crop 2× readout oversampling: keep central half of frequency dimension
snr_map = snr_map((size(snr_map,1)/4 + 1) : end - size(snr_map,1)/4, :);
```

`MRifft` = `ifft(ifftshift(x), [], dim)` — applies the centred inverse DFT
without any additional normalisation (MATLAB's `ifft` divides by N, so the
`*sqrt(N)` above compensates to get a unitary convention).

**Python (cmtools `cm2DKellmanRSS`):**

The `cm2DKellmanRSS` class applies the same unitary centred ifft2 internally and
crops the oversampled readout dimension before computing the SNR map.

---

### Step 4 — Analytical SNR (Kellman / RSS)

The **Kellman analytical** formula for RSS SNR at pixel $(i,j)$ is:

$$\text{SNR}_\text{RSS}(i,j)
  = \frac{\sqrt{\mathbf{s}^\dagger \mathbf{s}}}
         {\sqrt{\mathbf{s}^\dagger \Psi\, \mathbf{s}}}
  \cdot \frac{1}{\sqrt{2N}}$$

where $\mathbf{s} \in \mathbb{C}^{N_\text{coil}}$ is the complex image vector
at that pixel and $N = N_\text{freq} \times N_\text{phase}$ is the number of
k-space samples per coil.  The $1/\sqrt{2N}$ factor converts the k-space
normalisation convention to SNR units.

**MATLAB (`mrir_array_SNR_rss.m`):**

```matlab
for ii = 1:Ncol
    for jj = 1:Nlin
        S           = squeeze(sensitivity(ii,jj,:));
        signalmag   = abs(S' * S);
        noisepower  = abs(S' * covmtx * S);
        snr(ii,jj)  = signalmag / sqrt(noisepower);
    end
end
scale_factor = 1 / sqrt(2 * Ncol * Nlin);  % applied once to the whole map
snr = scale_factor * snr;
```

Note: `mrir_array_SNR_rss` labels its first argument `sensitivity` but it is
the **reconstructed image** array (freq × phase × coil) — the name is a
historical artefact from Roemer's sensitivity-based framework.

**Python (`cm2DKellmanRSS.getOutput()`):**

Implements the same formula vectorised over all pixels.  The noise covariance
Ψ is set via `reconstructor.setNoiseCovariance(NC)` inside `calcKellmanSNR()`.

**Other reconstructors available in both pipelines:**

| Method | Python class | MATLAB equivalent | Formula |
|--------|-------------|-------------------|---------|
| RSS (analytical) | `cm2DKellmanRSS` | `mrir_array_SNR_rss` | $\mathbf{s}^\dagger\mathbf{s} / \sqrt{\mathbf{s}^\dagger\Psi\mathbf{s}} / \sqrt{2N}$ |
| Optimal / Roemer | `cm2DKellmanB1` | `mrir_array_SNR_optimal` | $\sqrt{\mathbf{s}^\dagger\Psi^{-1}\mathbf{s}} / \sqrt{2N}$ |
| SENSE (analytical) | `cm2DKellmanSENSE` | `mrir_array_SENSE_SNR` | Pruessmann 1999 |
| GRAPPA (analytical) | `cm2DKellmanGRAPPA` | `mrir_array_GRAPPA_gfactor_analytical` | Griswold 2006 |
| Multiple replicas | `calcMultipleReplicasSNR` | `calc_snr_pseudomr` (PMR) | Empirical std over synthetic noise realisations |

---

### Step 5 — FA Correction (SNR₉₀)

#### Why FA correction?

An MRI GRE SNR measurement depends on the actual flip angle (FA) delivered at
each voxel.  Because of B₁⁺ inhomogeneity the local FA deviates from the
prescribed value, especially at high field.  To compare coils fairly — or across
field strengths and protocols — SNR is normalised to what it would be if every
voxel were excited at 90°:

$$\text{SNR}_{90}(i,j) = \frac{\text{SNR}(i,j)}{\sin\bigl(\text{FA}(i,j)\bigr)}$$

This removes the $\sin(\text{FA})$ weighting that GRE signal carries
(Ernst-angle steady-state signal $\propto \sin(\text{FA})$ for TR ≫ T₁).
The formula comes from Ryan Brown's `snr_90_analysis.m` line 1566.

---

#### FA Map Source — Siemens TFL B₁⁺ Mapping

Siemens scanners provide a vendor B₁⁺ map acquired with a turboFLASH (TFL)
sequence.  The map is exported as a DICOM series where:

$$\text{pixel value} = \text{actual FA}\ [°] \times 10$$

i.e. `pixel / 10 = measured FA in degrees` at the TFL prescribed FA.

Because the TFL is usually run at a different prescribed FA than the GRE SNR
scan, the map must be rescaled to the GRE nominal FA:

$$\text{FA}_\text{GRE}(i,j)
  = \frac{\text{pixel}(i,j)}{10}
  \times \frac{\text{FA}_\text{GRE,nominal}}{\text{FA}_\text{TFL,prescribed}}$$

**Example (product coil dataset):**
- TFL prescribed FA = 80°, GRE nominal FA = 75°
- `FA_GRE = (pixel / 10) × (75 / 80)`

**Example (12-channel coil dataset):**
- TFL prescribed FA = 72.16°, GRE nominal FA = 75°
- `FA_GRE = (pixel / 10) × (75 / 72.16)`

This is implemented in `prepare_fa_maps.py` and documented in section 1c.

---

#### MATLAB Pipeline (`snr_90_analysis.m`)

```matlab
% Load FA from DICOM — pixel / 10 gives FA in degrees at TFL prescribed angle
% then scaled to GRE nominal FA (snr_90_analysis.m ~line 950)
FA_dicom = dicomread(dcm_file);                      % int16 DICOM pixels
FA_deg   = double(FA_dicom) / 10;                    % → degrees at TFL FA

% Scale to GRE nominal FA (ratio = GRE_nominal / TFL_prescribed)
FA_deg   = FA_deg * (gre_nominal_fa / tfl_prescribed_fa);

% The B1+ map and SNR map have different grids and orientations.
% MATLAB aligns them interactively (user drags/flips/rotates in a GUI):
aligned_data = manual_alignment_adjustment(b1p_data, snr_data, aligned_data, config);

% Compute SNR90 — exact lines 1566-1570:
results.snr90 = aligned_data.snr_map ./ sind(results.FA);
results.snr90(~isfinite(results.snr90)) = 0;   % NaN / Inf → 0
results.snr90(results.snr90 < 0)        = 0;   % negative → 0
```

The manual alignment step is the biggest practical limitation of the MATLAB
pipeline: it requires a human to visually align two images every run, making
batch processing difficult and results non-reproducible.

---

#### Python Pipeline (`fa_normalization.py`)

The Python implementation replaces the manual alignment with geometry-aware
automatic resampling using the NIfTI affine/direction metadata from `dcm2niix`:

```python
# --- 1. Load FA map (already scaled to GRE FA in prepare_fa_maps.py) ---
fa_img = ima.Imaginable(fa_path)          # NIfTI preserving dcm2niix geometry

# --- 2. Geometry check ---
# If FA and SNR share the same grid, skip resampling entirely
same_space = snr_img.isImaginableInTheSameSpace(fa_img)

# --- 3. Resample onto SNR grid (BSpline order-3) ---
fa_resampled = fa_img.resampleOnTargetImage(
    snr_img,
    interpolator=sitk.sitkBSplineResampler,  # cubic B-spline
    default_value=0,                          # background outside FA FOV → 0
)
arr = np.clip(arr, 0.0, 180.0)              # suppress BSpline ringing overshoot

# --- 4. Inpaint near-zero sin(FA) boundary voxels ---
# BSpline resampling creates fringe voxels at the FA map boundary with FA ≈ 0-1°
# (pure interpolation artefact outside the acquired FA volume).
# Dividing SNR by sin(~0°) would produce enormous artefactual values.
# Instead of simply zeroing them, we heal each flagged voxel from its neighbours:
EPSILON = 0.02                              # catches FA < ~1.1°
near_zero_mask = np.abs(sin_fa) < EPSILON
sin_fa_filled  = median_filter(sin_fa, size=3, mode='nearest')
sin_fa[near_zero_mask] = sin_fa_filled[near_zero_mask]   # inpaint
# Voxels still near-zero after inpainting (deep background, no valid neighbours)
# → NaN → zeroed by snr.py cleanup
still_zero = near_zero_mask & (np.abs(sin_fa) < EPSILON)
sin_fa[still_zero] = np.nan

# --- 5. Divide ---
snr90 = snr_array / sin_fa
```

**Why median filter instead of hard zeroing?**

The BSpline fringe affects the 1–2 voxel ring at the boundary of the FA map
FOV.  Voxels in this ring that happen to sit inside the tissue region (where
SNR > 0) would be zeroed by a hard mask, creating artificial holes in the
corrected map.  The 3×3×3 median filter fills those voxels from their valid
tissue neighbours, preserving map continuity.  Truly isolated background
voxels (no valid neighbours within the window) still get masked.

**Provenance logged to JSON on every run:**

```json
{
  "faCorrectionApplied": true,
  "faUnits": "degrees",
  "faCorrectionMethod": "snr_over_sin_fa",
  "epsilonThreshold": 0.02,
  "fillWindow": 3,
  "nNearZeroVoxelsDetected": 25745,
  "nNearZeroVoxelsInpainted": 605,
  "nNearZeroVoxelsMasked": 25140,
  "faMin": 0.0,
  "faMax": 180.0
}
```

**Key improvements over MATLAB:**

| Issue | MATLAB | Python |
|-------|--------|--------|
| Grid alignment | Manual interactive UI (non-reproducible) | Automatic BSpline using NIfTI affines |
| In-plane interpolation | `imresize` nearest-neighbor | BSpline order-3 (smoother) |
| Through-slice interpolation | Slice pairing/reversal; no interpolation | 3D BSpline (single pass) |
| Ringing artefact | Not addressed | Clamped to [0°, 180°] after resample |
| Near-zero sin(FA) | Immediate → 0 | 3×3×3 median inpainting, then → NaN |
| Reproducibility | Requires human each run | Fully automated, same result every time |

---

### Known Differences Between MATLAB and Python Outputs

| Source | Effect | Notes |
|--------|--------|-------|
| Default `recon_method = 'opt'` in MATLAB | ~30% higher SNR in MATLAB | Use `'rss'` in `snr_toolbox_batch.m` line 69 for a like-for-like comparison |
| FA alignment | MATLAB: interactive manual UI; Python: geometry-aware BSpline | Python is fully automated and reproducible |
| FA interpolation | MATLAB: `imresize` (nearest-neighbor in this workflow); Python: 3D BSpline | The two methods use different voxel-center/grid conventions |
| Near-zero sin(FA) | MATLAB: immediate zero; Python: 3×3×3 median inpainting first | Python heals ~400–600 boundary voxels per dataset |
| Slice ordering | MATLAB: heuristic interleaved convention; Python: physical positions from header | Python is geometrically correct |
| Output format | MATLAB: `.mat` workspace; Python: NIfTI + JSON provenance | Python outputs are directly viewable in ITK-SNAP / FSLeyes |

---

## �💬 **Acknowledgments**

This research has been supported in part by the National Institute of Biomedical Imaging and
Bioengineering (NIBIB) under award numbers: R01 EB024536.

---

## ⚠️ **Disclaimer**

This is a research tool intended for academic and research purposes. While every effort has been made to ensure its quality, the software may contain bugs. We do not assume responsibility for any errors or issues resulting from its use. We encourage users to report errors, warnings, and questions via the [Issues](https://github.com/cloudmrhub/mroptimum-tools/issues) page.

---

## 📃 **License**

MR Optimum is released under the **MIT License**.

---

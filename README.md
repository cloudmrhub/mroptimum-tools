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
| `collections/` | Example JSON configurations organized by SNR method (AC/, MR/, PMR/, CR/, misc/). |

---

### **2. 📋 `json/` & `mrotools/collections/` — Example Configurations**

```
mrotools/collections/
├── AC/        # Analytical / Kellman configs
├── MR/        # Multiple Replicas configs
├── PMR/       # Pseudo Multiple Replicas configs
├── CR/        # Coil Replica / Generalized PMR configs
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

## 🚀 **Getting Started**

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

## 🖥️ **GUI Tool**

`mrotools/generate-ui.py` provides a **Tkinter-based GUI** for interactively building JSON configuration files and launching SNR calculations without writing code. Launch it with:

```bash
python mrotools/generate-ui.py
```

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

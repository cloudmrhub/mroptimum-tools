# MR Optimum
![License](https://img.shields.io/github/license/cloudmrhub/mroptimum-tools)
![GitHub last commit](https://img.shields.io/github/last-commit/cloudmrhub/mroptimum-tools)
![GitHub issues](https://img.shields.io/github/issues/cloudmrhub/mroptimum-tools)
![GitHub forks](https://img.shields.io/github/forks/cloudmrhub/mroptimum-tools)
![GitHub stars](https://img.shields.io/github/stars/cloudmrhub/mroptimum-tools)

**MR Optimum** provides tools for advanced signal-to-noise ratio (SNR) estimation and image reconstruction methods for Magnetic Resonance Imaging (MRI). It is designed for researchers and developers to efficiently perform SNR calculations, reconstructions, and custom pipeline configurations.

## Quickstart
Run an SNR calculation using a JSON configuration:

```bash
python -m mroptimum.snr -j /path/to/config.json -o /output/path/ -c True -g True -v True -m True
```

### Example JSON Configuration
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

# Installation
```
#create an environment 
python3 -m venv MRO
source MRO/bin/activate
pip install git+https://github.com/cloudmrhub/mroptimum-tools.git
```

---

# **Versioning**

The **MR Optimum** package has two versions:

### **V1 (Deprecated)**
- **Name:** `mroptimum`
- **Status:** Deprecated, but still functional for backward compatibility. (v1 branch)
- **Details:** This version is no longer actively maintained and will not receive updates or bug fixes.
- **Installation:**
  ```bash
  pip install git+https://github.com/cloudmrhub/mroptimum-tools.git@v1
  ```

### **Version 2 (Current)**
- **Name:** `mroptimum-tools`
- **Status:** Actively maintained (main branch).
- **Details:** This is the recommended version for new projects. It includes updated functionality, GUI tools, and expanded features.
- **Installation:**
  ```bash
  pip install git+https://github.com/cloudmrhub/mroptimum-tools.git
  ```

---

## **Key Differences**
| Feature                 | Version 1 (`v1`)             | Version 2 (`main`)          |
|-------------------------|------------------------------|-----------------------------|
| Maintenance             | Deprecated                  | Actively maintained         |
| Compatibility           | Legacy projects             | New and legacy projects     |
| Features                | Limited                     | GUI tools, expanded options |
---

## **Migration**
If you're currently using **Version 1**, consider migrating to **Version 2** to take advantage of the latest features and updates.

---

# Contributors
[*Dr. Eros Montin, PhD*](http://me.biodimensional.com)\
[![GitHub](https://img.shields.io/badge/GitHub-erosmontin-blue)](https://github.com/erosmontin)\
[![ORCID](https://img.shields.io/badge/ORCID-0000--0002--1773--0064-green)](https://orcid.org/0000-0002-1773-0064)\
[![Scopus](https://img.shields.io/badge/Scopus-35604121500-orange)](https://www.scopus.com/authid/detail.uri?authorId=35604121500)

[*Prof. Riccardo Lattanzi*](https://med.nyu.edu/faculty/riccardo-lattanzi)\
[![GitHub](https://img.shields.io/badge/GitHub-rlattanzi-blue)](https://github.com/rlattanzi)\
[![ORCID](https://img.shields.io/badge/ORCID-0000--0002--8240--5903-green)](https://orcid.org/0000-0002-8240-5903)\
[![Scopus](https://img.shields.io/badge/Scopus-6701330033-orange)](https://www.scopus.com/authid/detail.uri?authorId=6701330033)

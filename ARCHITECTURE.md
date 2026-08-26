# MR Optimum Stack — Architecture Reference for Agents

> **Purpose**: This document explains the full repository dependency chain, deployment modes,
> runtime call flow, and the rules for updating each component. Read this before making any
> changes to avoid the class of mistakes where the wrong file is edited (e.g. `worker/requirements.txt`
> instead of `calculation/src/requirements-fargate-compiled.txt`).

---

## 1. Repositories

| Repo | Language | Role | GitHub |
|---|---|---|---|
| `mroptimum-tools` | Python | **Computation library** — all SNR/FA math lives here | `cloudmrhub/mroptimum-tools` |
| `mroptimum-app` | Python + SAM/CloudFormation | **AWS compute infrastructure** — runs mrotools inside Docker | `cloudmrhub/mroptimum-app` |
| `mroptimum-webgui` | React/TypeScript | **Frontend** — user UI for uploading data and viewing results | `cloudmrhub/mroptimum-webgui` |
| `cloudmr-brain` | Python + SAM | **Managing API** — auth, job queue, pipeline orchestration | `cloudmrhub/cloudmr-brain` (or `py-cloudmr-brain`) |
| `cloudmr-tools` (`cmtools`) | Python | Shared utilities: file I/O, S3, AWS helpers | `cloudmrhub/cloudmr-tools` |

Local paths on this machine:
```
/data/PROJECTS/mroptimum-tools/
/data/PROJECTS/mroptimum-app/
/data/PROJECTS/mroptimum-webgui/
/data/PROJECTS/cloudmr-brain/
```

---

## 2. System Architecture

```
  Browser
    │
    ▼
mroptimum-webgui  (React, hosted on Amplify)
    │  REST/HTTP
    ▼
cloudmr-brain  (Python/SAM Lambda — API Gateway)
    │  manages users, pipelines, computing-units
    │  dispatches jobs to registered computing units
    ▼
mroptimum-app  (AWS Step Functions → Lambda → Fargate)
    │  receives JSON job payload
    │  downloads data from S3
    │  runs: python -m mrotools.snr -j <job.json>
    │  uploads results back to S3
    ▼
mroptimum-tools  (mrotools Python package — inside Docker image)
    │  performs the actual SNR / FA-correction calculation
    │  reads k-space .dat files via twixtools
    │  writes NIfTI results
```

---

## 3. Deployment Modes

### Mode 1 — CloudMRHub Managed (default)
- **Compute runs in CloudMRHub's AWS account** (us-east-1)
- CloudMRHub owns the ECR, S3, Fargate cluster, Step Functions state machine
- Users submit jobs via the webgui → cloudmr-brain queues them → mroptimum-app executes
- CI/CD auto-deploys on push to `main` (see §5)

### Mode 2 — User-Owned
- **Compute runs in the user's own AWS account**
- User deploys `mroptimum-app` into their account using `calculation/template.yaml`
- User registers their computing unit with cloudmr-brain
- All S3 data stays in the user's account
- Script: `scripts/deploy-mode1-local.sh` / `deploy-and-register-mode1.sh`
- Uses the **public ECR image** (no cross-account IAM needed)

### Local / SLURM / Other Clouds
- Same public ECR image, pulled without authentication
- SLURM: use Singularity/Apptainer to wrap the Docker image
- Other clouds (GCP, Azure): pull from public ECR, run as container

### Public Image URIs (no auth required)
```
Fargate: public.ecr.aws/r2m7t0q6/cloudmrhub/mroptimum-fargate:vX.Y.Z
Lambda:  public.ecr.aws/r2m7t0q6/cloudmrhub/mroptimum-lambda:vX.Y.Z
```
The semver tag matches the pinned mrotools version (e.g. `v3.1.0`).
`:latest` always points to the most recent build.

**Usage by platform:**
```bash
# Local Docker
docker run public.ecr.aws/r2m7t0q6/cloudmrhub/mroptimum-fargate:v3.1.0

# SLURM via Singularity/Apptainer
singularity pull mroptimum-v3.1.0.sif \
  docker://public.ecr.aws/r2m7t0q6/cloudmrhub/mroptimum-fargate:v3.1.0
apptainer exec mroptimum-v3.1.0.sif python -m mrotools.snr -j job.json -o out/

# Mode 2 AWS CloudFormation — reference in task definition:
#   image: public.ecr.aws/r2m7t0q6/cloudmrhub/mroptimum-fargate:v3.1.0
```

> **Mode 2 update procedure**: `build-images.yml` pushes to public ECR on every
> build with a versioned tag. Mode 2 users re-run their deployment script pointing
> to the new tag to update. No AWS credentials needed to pull the image.

---

## 4. Runtime Call Flow (detailed)

```
1. User configures job in mroptimum-webgui
      ↓ POST /pipeline  (JSON payload with signal/noise/faCorrection refs)
2. cloudmr-brain creates a Pipeline record in DynamoDB
      ↓ triggers Step Functions execution
3. Step Functions invokes mroptimum-app Lambda (orchestrator)
      ↓ passes job payload
4. Lambda spawns Fargate task (for heavy compute) OR runs inline
      ↓ mroptimum-app/calculation/src/app.py executes:
        a. Downloads signal .dat, noise .dat, FA NIfTI from S3 → /tmp/
        b. Resolves faCorrection file if present (app.py lines ~285–298)
        c. Writes updated job JSON to /tmp/<uuid>.json
        d. Runs: python -m mrotools.snr -j /tmp/<uuid>.json -o /tmp/out/ ...
5. mrotools.snr (mroptimum-tools) runs inside the same Docker container:
        a. Reads signal/noise k-space
        b. Computes SNR (AC/PMR/CR depending on type)
        c. Applies FA correction if faCorrection present in JSON
        d. Writes SNR.nii.gz, SNR_FA_corrected.nii.gz, NC.nii.gz, NCC.nii.gz
6. app.py uploads results from /tmp/out/ → S3
7. cloudmr-brain marks pipeline as complete → webgui polls and shows results
```

---

## 5. CI/CD — What Triggers a Docker Rebuild

**This is the most important section for avoiding deployment mistakes.**

### GitHub Actions workflows (in `mroptimum-app/.github/workflows/`):

| Workflow file | Trigger paths | What it does |
|---|---|---|
| `build-images.yml` | `calculation/src/**`, `calculation/Dockerfile*`, `.github/workflows/build-images.yml` | Builds `DockerfileLambda` + `DockerfileFargate`, pushes to **private ECR** always; pushes to **public ECR only on `main`** |
| `deploy-and-register.yml` | depends on `build-images.yml` or `workflow_dispatch` | SAM deploy to branch-specific stack, registers computing unit with cloudmr-brain |
| `register-computing-unit.yml` | manual | Re-registers the computing unit only (no rebuild) |

### Branch strategy:

| Branch | Deploys to | Public ECR push | Purpose |
|---|---|---|---|
| `dev` | `mroptimum-app-dev` (Mode 1 staging) | ❌ No | Work in progress, testing |
| `main` | `mroptimum-app-test` (Mode 1 prod) | ✅ Yes | Stable release, updates Mode 2 / local / SLURM |

**Workflow:** develop on `dev` → test in staging → PR merge to `main` → prod deploys + public ECR updates.

### ⚠️ Files that DO and DO NOT trigger a rebuild:

| File | Triggers rebuild? | Notes |
|---|---|---|
| `calculation/src/requirements-fargate-compiled.txt` | ✅ YES | **This is the real Fargate Docker requirements** |
| `calculation/src/requirements-lambda-frozen.txt` | ✅ YES | **This is the real Lambda Docker requirements** |
| `calculation/src/DockerfileFargate` | ✅ YES | Fargate image definition |
| `calculation/src/DockerfileLambda` | ✅ YES | Lambda image definition |
| `calculation/src/app.py` | ✅ YES | Main compute entrypoint |
| `worker/requirements.txt` | ❌ NO | Reference/documentation only — NOT used by Docker |
| `template.yaml` | ❌ (deploy only) | SAM stack, not image build |
| `README.md`, `scripts/` | ❌ NO | |

---

## 6. Updating mroptimum-tools (the computation library)

### Step-by-step:

```bash
# 1. Make changes in mroptimum-tools
cd /data/PROJECTS/mroptimum-tools

# 2. Bump version in pyproject.toml
#    Patch (bug fix):   3.1.0 → 3.1.1
#    Minor (new feature): 3.1.0 → 3.2.0
#    Major (breaking):    3.x.x → 4.0.0
vim pyproject.toml   # edit version = "..."

# 3. Commit, tag, push
git add -A
git commit -m "feat/fix: description"
git tag v3.x.x
git push origin main --tags

# 4. Pin in mroptimum-app — update BOTH files:
cd /data/PROJECTS/mroptimum-app
# Edit these two files (same line in each):
#   calculation/src/requirements-fargate-compiled.txt
#   calculation/src/requirements-lambda-frozen.txt
# Change:
#   mrotools @ git+https://github.com/cloudmrhub/mroptimum-tools.git@v3.OLD
# To:
#   mrotools @ git+https://github.com/cloudmrhub/mroptimum-tools.git@v3.NEW

git add calculation/src/requirements-fargate-compiled.txt \
        calculation/src/requirements-lambda-frozen.txt
git commit -m "chore: pin mrotools to vX.Y.Z"
git push origin main
# → this triggers build-images.yml → Docker rebuilt → new version deployed
```

**Never edit `worker/requirements.txt` alone** — it is not part of the Docker build.

---

## 7. Job JSON Payload Format

The JSON sent from webgui → cloudmr-brain → mroptimum-app → mrotools.snr.

```json
{
    "name": "ac",           // SNR method: "ac" (analytical), "pmr", "cr", "mr"
    "version": "v0",
    "acquisition": 2,       // always 2 (2D k-space)
    "type": "snr",
    "id": 0,
    "options": {
        "reconstructor": {
            "name": "b1",   // reconstructor: "rss", "b1", "sense", "grappa"
            "id": 1,
            "options": {
                "signal": {                     // signal k-space file
                    "type": "file",
                    "options": {
                        "type": "s3",           // or "local" for testing
                        "filename": "...",
                        "bucket": "...",
                        "key": "...",
                        "vendor": "Siemens",    // "Siemens" or "numpy"
                        "multiraid": false
                    }
                },
                "noise": { ... },               // same structure as signal
                "sensitivityMap": {
                    "options": {
                        "sensitivityMapMethod": "inner",
                        "mask": {"method": "percentage", "value": 10}
                    }
                },
                "correction": {
                    "useCorrection": true,
                    "faCorrection": {           // optional FA map
                        "type": "file",
                        "options": {
                            "type": "s3",       // or "local"
                            "filename": "fa_map.nii.gz",
                            "bucket": "...",
                            "key": "..."
                        }
                    }
                },
                "gfactor": false
            }
        }
    },
    "files": ["signal", "noise", "faCorrection"]
}
```

### SNR method (`name`) values:
| Value | Method | Notes |
|---|---|---|
| `"ac"` | Analytical (Kellman) | Fast, single acquisition |
| `"pmr"` | Pseudo Multiple Replicas | Requires `NR` |
| `"cr"` | Corrected Replicas | Requires `NR`, `boxSize` |
| `"mr"` | Multiple Replicas | True repeated acquisitions |

### Reconstructor (`name`) values:
| Value | Class | Notes |
|---|---|---|
| `"rss"` | Root Sum of Squares | No sensitivity needed |
| `"b1"` | B1/Kellman | Uses inner k-space for sensitivities |
| `"sense"` | SENSE | Requires acceleration |
| `"grappa"` | GRAPPA | Requires ACS lines |

---

## 8. FA Correction — How it flows through the stack

```
webgui: user uploads NIfTI FA map → S3
    ↓ payload includes correction.faCorrection.options (S3 ref)
app.py (mroptimum-app): downloads FA NIfTI to /tmp/, resolves path
    ↓ (app.py lines ~285–298 handle faCorrection before calling mrotools)
mrotools/snr.py: if args.fa_map is None → reads faCorrection from JSON
    ↓ normalize_snr_with_fa(snr_array, fa_path)
fa_normalization.py:
    - resamples FA map to SNR grid (SimpleITK)
    - masks |sin(FA)| < EPSILON=0.02 (FA < ~1.1°)
    - inpaints boundary voxels with 3×3×3 median filter
    - computes SNR_FA_corrected = SNR / sin(FA)
Output files: SNR_FA_corrected.nii.gz, FA_on_SNR.nii.gz
```

**Note**: `app.py` resolves the S3 FA file and downloads it before calling mrotools.
`mrotools/snr.py` also resolves `faCorrection` from JSON (via `getFile`) as a fallback
for local testing. Both paths converge on `normalize_snr_with_fa()`.

---

## 9. Local Testing

### Test computation only (no AWS):
```bash
conda activate mro
cd /data/PROJECTS/mroptimum-tools

# Using CLI flag (old format):
python -m mrotools.snr -j job_product_coil.json -o /tmp/out \
    --fa-map /data/garbage/FA-test/fa_maps/fa_product_coil.nii.gz \
    --no-parallel --no-matlab

# Using app JSON payload format (new format — tests full faCorrection path):
python tests/test_fa_correction_app_payload.py
```

### Test data (local):
```
/data/garbage/FA-test/
├── meas_MID01584_*_sag_17slices.dat   # product coil signal
├── meas_MID01585_*_noi_17slices.dat   # product coil noise
├── meas_MID02739_*_sag_17slices.dat   # 12ch coil signal
├── meas_MID02740_*_noi_17slices.dat   # 12ch coil noise
├── fa_maps/
│   ├── fa_product_coil.nii.gz         # FA map in degrees
│   └── fa_12ch_coil.nii.gz
└── output_product_coil/data/          # reference Python output
    ├── SNR.nii.gz
    ├── SNR_FA_corrected.nii.gz
    └── ...
```

---

## 10. Package Versions & Dependencies

```
mroptimum-tools (mrotools)
    ├── cmtools (cloudmr-tools)          git+github.com/cloudmrhub/cloudmr-tools
    ├── pynico_eros_montin               git+github.com/erosmontin/pynico@v2
    ├── pyable_eros_montin               git+github.com/erosmontin/pyable@v2
    ├── raider_eros_montin               git+github.com/erosmontin/raider
    ├── twixtools                        (Siemens k-space reading)
    ├── SimpleITK                        (image resampling for FA maps)
    └── scipy, numpy, matplotlib

mroptimum-app Docker images (Fargate + Lambda)
    pinned in: calculation/src/requirements-fargate-compiled.txt
               calculation/src/requirements-lambda-frozen.txt
    current:   mrotools @ ...@v3.1.0

Conda env for local dev: mro
    activate: conda activate mro
    run:      conda run -n mro python ...
```

---

## 11. Key Files Quick Reference

| File | What it does |
|---|---|
| `mroptimum-tools/mrotools/snr.py` | CLI entrypoint + full pipeline orchestration |
| `mroptimum-tools/mrotools/fa_normalization.py` | FA correction math (normalize_snr_with_fa) |
| `mroptimum-tools/mrotools/kspace_loaders.py` | Siemens/numpy k-space readers |
| `mroptimum-tools/mrotools/mro.py` | Reconstructors, SNR calculators, getFile() |
| `mroptimum-tools/pyproject.toml` | Package version — bump this on every release |
| `mroptimum-app/calculation/src/app.py` | Docker entrypoint — downloads files, calls mrotools.snr |
| `mroptimum-app/calculation/src/DockerfileFargate` | Fargate image (heavy jobs) |
| `mroptimum-app/calculation/src/DockerfileLambda` | Lambda image (light jobs) |
| `mroptimum-app/calculation/src/requirements-fargate-compiled.txt` | **Real Fargate deps — edit this to update mrotools** |
| `mroptimum-app/calculation/src/requirements-lambda-frozen.txt` | **Real Lambda deps — edit this to update mrotools** |
| `mroptimum-app/worker/requirements.txt` | ⚠️ Reference only — NOT used by Docker build |
| Public Fargate image | `public.ecr.aws/r2m7t0q6/cloudmrhub/mroptimum-fargate:vX.Y.Z` — no auth, use on Mode 2 / local / SLURM |
| Public Lambda image  | `public.ecr.aws/r2m7t0q6/cloudmrhub/mroptimum-lambda:vX.Y.Z` — no auth |
| `mroptimum-app/.github/workflows/build-images.yml` | CI: rebuilds Docker on `calculation/src/**` changes |
| `mroptimum-app/.github/workflows/deploy-and-register.yml` | CI: SAM deploy + computing unit registration |
| `mroptimum-tools/tests/test_fa_correction_app_payload.py` | Integration test: FA from JSON payload (12/12) |
| `mroptimum-tools/tests/test_fa_normalization.py` | Unit tests: fa_normalization.py |

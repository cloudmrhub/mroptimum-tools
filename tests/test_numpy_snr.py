"""
Test: Image → K-space → NumPy → SNR calculation

This script demonstrates the numpy file format workflow:
1. Load a 2D MRI image (or generate a synthetic phantom)
2. Simulate multi-coil k-space data
3. Save signal and noise as .npy files
4. Build a JSON config and run the SNR pipeline

Usage:
    conda run -n mro python tests/test_numpy_snr.py
"""
import numpy as np
import os
import sys
import json
import tempfile
import shutil

# Add parent to path so we can import mrotools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ═══════════════════════════════════════════════════════════════════════════
# 1. Create a 2D image (load real image or fall back to phantom)
# ═══════════════════════════════════════════════════════════════════════════
def load_or_create_image(image_path=None, size=(128, 128)):
    """
    Load a 2D grayscale image from file, or create a Shepp-Logan–style
    phantom if no file is provided.
    """
    if image_path and os.path.isfile(image_path):
        from PIL import Image
        img = Image.open(image_path).convert("L")
        img = img.resize(size, Image.LANCZOS)
        image = np.array(img, dtype=np.float64)
        print(f"Loaded image from {image_path}  shape={image.shape}")
    else:
        # Synthetic circular phantom with internal structure
        y, x = np.mgrid[-1:1:complex(0, size[0]), -1:1:complex(0, size[1])]
        r = np.sqrt(x**2 + y**2)
        image = np.zeros(size, dtype=np.float64)
        image[r < 0.85] = 200        # outer ellipse
        image[r < 0.70] = 400        # inner tissue
        image[(x - 0.2)**2 + (y + 0.1)**2 < 0.05] = 800   # bright spot
        image[(x + 0.3)**2 + (y - 0.2)**2 < 0.08] = 100   # dark region
        print(f"Created synthetic phantom  shape={image.shape}")
    return image


# ═══════════════════════════════════════════════════════════════════════════
# 2. Simulate multi-coil k-space from a 2D image
# ═══════════════════════════════════════════════════════════════════════════
def simulate_coil_sensitivities(shape, n_coils=8):
    """
    Generate smooth coil sensitivity maps using a simple Biot-Savart model.
    Coils are distributed in a ring around the FOV.
    """
    ny, nx = shape
    y, x = np.mgrid[0:ny, 0:nx].astype(np.float64)
    cy, cx = ny / 2.0, nx / 2.0

    sensitivities = np.zeros((ny, nx, n_coils), dtype=np.complex128)
    for c in range(n_coils):
        angle = 2 * np.pi * c / n_coils
        # Coil position outside the FOV
        coil_x = cx + 1.5 * cx * np.cos(angle)
        coil_y = cy + 1.5 * cy * np.sin(angle)
        # Distance-based sensitivity (1/r fall-off with smooth phase)
        dist = np.sqrt((x - coil_x)**2 + (y - coil_y)**2) + 1e-6
        magnitude = 1.0 / dist
        phase = np.angle((x - coil_x) + 1j * (y - coil_y))
        sensitivities[:, :, c] = magnitude * np.exp(1j * phase)

    # Normalize so RSS of sensitivities ~ 1
    rss = np.sqrt(np.sum(np.abs(sensitivities)**2, axis=2, keepdims=True))
    sensitivities /= (rss + 1e-12)
    return sensitivities


def image_to_multichannel_kspace(image, n_coils=8, noise_level=0.01):
    """
    Convert a 2D image to multi-coil k-space.

    Args:
        image: 2D array (freq, phase) – the ground truth image
        n_coils: number of coils
        noise_level: standard deviation of complex Gaussian noise
                     relative to the max k-space magnitude

    Returns:
        signal_kspace: (freq, phase, coils) – complex
        noise_kspace:  (freq, phase, coils) – pure noise in k-space
    """
    sensitivities = simulate_coil_sensitivities(image.shape, n_coils)

    # Coil images (image-domain)
    coil_images = image[:, :, np.newaxis] * sensitivities  # (freq, phase, coils)

    # Forward FFT to k-space per coil
    signal_kspace = np.zeros_like(coil_images, dtype=np.complex128)
    for c in range(n_coils):
        signal_kspace[:, :, c] = np.fft.fftshift(
            np.fft.fft2(np.fft.ifftshift(coil_images[:, :, c]))
        )

    # Noise k-space (pure noise, same statistics across coils)
    kmax = np.abs(signal_kspace).max()
    sigma = noise_level * kmax
    noise_kspace = (
        np.random.randn(*signal_kspace.shape) +
        1j * np.random.randn(*signal_kspace.shape)
    ) * sigma / np.sqrt(2)

    # Add noise to signal
    signal_kspace += noise_kspace

    return signal_kspace.astype(np.complex64), noise_kspace.astype(np.complex64)


# ═══════════════════════════════════════════════════════════════════════════
# 3. Save as numpy and build JSON config
# ═══════════════════════════════════════════════════════════════════════════
def save_and_build_config(signal_kspace, noise_kspace, output_dir, spacing=None):
    """
    Save signal/noise k-space as .npy and create a JSON config for MR Optimum.

    Returns:
        config_path: path to the JSON config file
    """
    os.makedirs(output_dir, exist_ok=True)

    sig_path = os.path.join(output_dir, "signal.npy")
    noi_path = os.path.join(output_dir, "noise.npy")
    np.save(sig_path, signal_kspace)
    np.save(noi_path, noise_kspace)
    print(f"Saved signal k-space: {sig_path}  shape={signal_kspace.shape}")
    print(f"Saved noise  k-space: {noi_path}  shape={noise_kspace.shape}")

    # Build JSON config (Analytical RSS – simplest SNR method)
    config = {
        "version": "v0",
        "acquisition": 2,
        "type": "SNR",
        "id": 0,
        "name": "AC",
        "options": {
            "reconstructor": {
                "type": "recon",
                "id": 1,
                "name": "RSS",
                "options": {
                    "signal": {
                        "type": "file",
                        "options": {
                            "type": "local",
                            "vendor": "numpy",
                            "filename": sig_path,
                            "multiraid": False,
                        }
                    },
                    "noise": {
                        "type": "file",
                        "options": {
                            "type": "local",
                            "vendor": "numpy",
                            "filename": noi_path,
                            "multiraid": False,
                        }
                    }
                }
            }
        }
    }

    # Add orientation if spacing provided
    if spacing is not None:
        config["options"]["reconstructor"]["options"]["signal"]["options"]["orientation"] = {
            "spacing": spacing,
        }

    config_path = os.path.join(output_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Saved config: {config_path}")
    return config_path


# ═══════════════════════════════════════════════════════════════════════════
# 4. Run the SNR pipeline programmatically
# ═══════════════════════════════════════════════════════════════════════════
def run_snr(config_path, output_dir):
    """
    Run the SNR calculation using the same logic as snr.py main block.
    """
    from pynico_eros_montin import pynico as pn
    from pyable_eros_montin import imaginable as ima
    from mrotools.mro import (
        RECON, RECON_classes, SNR, KELLMAN_classes, SNR_calculator,
        calculteNoiseCovariance, saveImage, getPackagesVersion,
    )
    from mrotools.kspace_loaders import get_kspace_loader

    # Read config
    with open(config_path) as f:
        J = json.load(f)

    reconstructor_dictionary = J["options"]["reconstructor"]
    RID = RECON.index(reconstructor_dictionary["name"].lower())
    SID = SNR.index(J["name"].lower())

    reconstructor = RECON_classes[RID]
    if SID == 0:
        reconstructor = KELLMAN_classes[RID]

    print(f"Reconstructor: {reconstructor.__name__}  (RID={RID}, SID={SID})")

    # Get loader
    vendor = reconstructor_dictionary["options"]["signal"]["options"]["vendor"]
    loader = get_kspace_loader(vendor)
    print(f"Loader: {type(loader).__name__}")

    # Load signal
    SL = loader.get_signal_kspace(
        reconstructor_dictionary["options"]["signal"],
        signal=True, MR=False,
    )
    print(f"Loaded {len(SL)} slice(s), k-space shape: {SL[0]['KSpace'].shape}")

    # Load noise
    NOISE = loader.get_noise_kspace(
        reconstructor_dictionary["options"]["noise"], "all"
    )

    # Noise covariance
    NC, NCC = calculteNoiseCovariance(NOISE, verbose=False)
    print(f"Noise covariance: {NC.shape}")

    # Get SNR calculator
    _SNR_calculator = SNR_calculator[SID]

    # Build tasks (one per slice)
    results_all = []
    for counter, sl in enumerate(SL):
        O = {
            "signal": sl["KSpace"],
            "noise": None,
            "noisecovariance": NC,
            "reference": None,
            "mask": False,
            "mimic": False,
            "acceleration": None,
            "autocalibration": None,
            "grappakernel": None,
            "slice": counter,
            "NR": None,
            "boxSize": None,
            "reconstructor": reconstructor(),
            "savecoilsens": False,
            "savegfactor": False,
        }
        result = _SNR_calculator(O)
        results_all.append(result)
        snr_map = result["images"]["SNR"]["data"]
        print(f"  Slice {counter}: SNR map shape={snr_map.shape}, "
              f"mean={np.abs(snr_map).mean():.2f}, max={np.abs(snr_map).max():.2f}")

    # Save output SNR as nifti
    snr_data = results_all[0]["images"]["SNR"]["data"]
    snr_3d = np.expand_dims(np.abs(snr_data), axis=-1)  # add slice dim
    out_img = ima.numpyToImaginable(snr_3d)

    spacing = SL[0]["spacing"]
    origin = SL[0]["origin"]
    direction = SL[0]["direction"].flatten()
    snr_path = os.path.join(output_dir, "SNR.nii.gz")
    saveImage(out_img, origin, spacing, direction, snr_path)
    print(f"\nSNR map saved to: {snr_path}")

    return snr_data


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test: Image → K-space → NumPy → SNR")
    parser.add_argument("-i", "--image", type=str, default=None,
                        help="Path to a 2D image (PNG/JPG). Uses phantom if omitted.")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Output directory. Uses a temp dir if omitted.")
    parser.add_argument("-c", "--coils", type=int, default=8,
                        help="Number of simulated coils (default: 8)")
    parser.add_argument("-n", "--noise", type=float, default=0.02,
                        help="Noise level relative to max k-space (default: 0.02)")
    parser.add_argument("-s", "--size", type=int, nargs=2, default=[128, 128],
                        help="Image size (freq phase), default: 128 128")
    args = parser.parse_args()

    # Output directory
    if args.output:
        output_dir = args.output
        cleanup = False
    else:
        output_dir = tempfile.mkdtemp(prefix="mro_test_numpy_")
        cleanup = False  # keep for inspection
    print(f"Output directory: {output_dir}")

    # Step 1: Get image
    image = load_or_create_image(args.image, tuple(args.size))

    # Step 2: Simulate multi-coil k-space
    np.random.seed(42)
    signal_kspace, noise_kspace = image_to_multichannel_kspace(
        image, n_coils=args.coils, noise_level=args.noise
    )

    # Step 3: Save as numpy + build config
    config_path = save_and_build_config(
        signal_kspace, noise_kspace, output_dir,
        spacing=[1.0, 1.0, 1.0],
    )

    # Step 4: Run SNR
    print("\n" + "=" * 60)
    print("Running SNR calculation...")
    print("=" * 60)
    snr = run_snr(config_path, output_dir)

    print("\n" + "=" * 60)
    print(f"DONE. Results in: {output_dir}")
    print(f"  signal.npy       : signal k-space ({signal_kspace.shape})")
    print(f"  noise.npy        : noise k-space  ({noise_kspace.shape})")
    print(f"  config.json      : MR Optimum JSON config")
    print(f"  SNR.nii.gz       : SNR map")
    print("=" * 60)

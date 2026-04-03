import numpy as np
from pathlib import Path
from typing import Tuple, Optional

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib import rcParams
def load_covariance_matrices(path1: str, path2: str) -> Tuple[np.ndarray, np.ndarray]:
    """Load two covariance matrices from numpy files."""
    cov1 = np.load(path1)
    cov2 = np.load(path2)
    return cov1, cov2

def plot_covariance_comparison(cov1: np.ndarray, cov2: np.ndarray, 
                               title1: str = "Covariance 1", 
                               title2: str = "Covariance 2",
                               output_path: Optional[str] = None,
                               value_unit: Optional[str] = None,
                               show: bool = True) -> None:
    """
    Plot two covariance matrices and their differences.
    
    Args:
        cov1, cov2: Covariance matrices
        title1, title2: Titles for the matrices
        output_path: Path to save the figure (optional)
    """
    # Convert complex matrices to magnitude
    if np.iscomplexobj(cov1):
        cov1 = np.abs(cov1)
    if np.iscomplexobj(cov2):
        cov2 = np.abs(cov2)
    
    # Styling for clearer plots
    rcParams.update({'font.size': 11, 'axes.titlesize': 12, 'axes.titleweight': 'bold'})
    plt.style.use('ggplot')

    # Compute difference and statistics
    diff = cov2 - cov1
    vmin, vmax = np.min(cov1), np.max(cov1)

    # Create a square 2x2 grid and enforce square aspect for each axis
    fig, axes = plt.subplots(2, 2, figsize=(10, 10), constrained_layout=True)
    ax1 = axes[0, 0]
    ax2 = axes[0, 1]
    ax3 = axes[1, 0]
    ax4 = axes[1, 1]

    # Top-left: cov1
    im1 = ax1.imshow(cov1, cmap='viridis', vmin=vmin, vmax=vmax, origin='lower', interpolation='nearest')
    ax1.set_title(title1)
    ax1.set_xlabel('Features')
    ax1.set_ylabel('Features')
    ax1.set_aspect('equal')

    # Top-right: cov2
    im2 = ax2.imshow(cov2, cmap='viridis', vmin=vmin, vmax=vmax, origin='lower', interpolation='nearest')
    ax2.set_title(title2)
    ax2.set_xlabel('Features')
    ax2.set_ylabel('Features')
    ax2.set_aspect('equal')

    # Shared colorbar for the two covariance images (placed below them)
    cbar = fig.colorbar(im2, ax=[ax1, ax2], orientation='horizontal', pad=0.04, fraction=0.06)
    cbar.set_label('Covariance Values')

    # Bottom-left: signed difference with diverging colormap (centered at 0)
    diff_vmax = np.max(np.abs(diff)) if diff.size else 1.0
    im3 = ax3.imshow(diff, cmap='RdBu_r', vmin=-diff_vmax, vmax=diff_vmax, origin='lower', interpolation='nearest')
    ax3.set_title('Difference (Cov2 - Cov1)')
    ax3.set_xlabel('Features')
    ax3.set_ylabel('Features')
    ax3.set_aspect('equal')
    # Label for difference colorbar includes units if provided
    diff_label = f"Difference ({value_unit})" if value_unit else 'Difference'
    fig.colorbar(im3, ax=ax3, fraction=0.046, pad=0.02, label=diff_label)

    # Bottom-right: absolute differences with hotter colormap
    abs_diff = np.abs(diff)
    im4 = ax4.imshow(abs_diff, cmap='magma', origin='lower', interpolation='nearest')
    ax4.set_title('Absolute Differences')
    ax4.set_xlabel('Features')
    ax4.set_ylabel('Features')
    ax4.set_aspect('equal')
    fig.colorbar(im4, ax=ax4, fraction=0.046, pad=0.02, label='|Difference|')

    # Highlight top differences with visible markers
    try:
        top_indices = np.argsort(abs_diff.flatten())[-5:]
        for idx in top_indices:
            i, j = np.unravel_index(idx, abs_diff.shape)
            ax4.scatter(j, i, s=180, facecolors='none', edgecolors='cyan', linewidths=2)
    except Exception:
        pass
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Figure saved to {output_path}")

    if show:
        plt.show()
    else:
        plt.close(fig)
    
    # Print report
    print_comparison_report(cov1, cov2, diff)

def print_comparison_report(cov1: np.ndarray, cov2: np.ndarray, 
                            diff: np.ndarray) -> None:
    """Print statistical comparison report."""
    print("\n" + "="*60)
    print("COVARIANCE MATRICES COMPARISON REPORT")
    print("="*60)
    
    # Use scientific formatting for small magnitudes
    fmt = lambda x: f"{x:.3e}"

    print(f"\nMatrix Dimensions: {cov1.shape}")
    print(f"\n--- Matrix 1 Statistics ---")
    print(f"  Min: {fmt(np.min(cov1))}")
    print(f"  Max: {fmt(np.max(cov1))}")
    print(f"  Mean: {fmt(np.mean(cov1))}")
    print(f"  Std Dev: {fmt(np.std(cov1))}")
    print(f"  Trace: {fmt(np.trace(cov1))}")

    print(f"\n--- Matrix 2 Statistics ---")
    print(f"  Min: {fmt(np.min(cov2))}")
    print(f"  Max: {fmt(np.max(cov2))}")
    print(f"  Mean: {fmt(np.mean(cov2))}")
    print(f"  Std Dev: {fmt(np.std(cov2))}")
    print(f"  Trace: {fmt(np.trace(cov2))}")

    # Difference statistics (absolute and percent)
    abs_diff = np.abs(diff)
    max_abs = np.max(abs_diff) if abs_diff.size else 0.0
    mean_abs = np.mean(abs_diff) if abs_diff.size else 0.0
    rms = np.sqrt(np.mean(diff**2)) if diff.size else 0.0
    frob = np.linalg.norm(diff)

    # Percent differences relative to cov1 where possible. Where cov1 is zero,
    # fall back to cov2 magnitude or an epsilon to avoid division by zero.
    eps = np.finfo(float).eps
    denom = np.where(np.abs(cov1) > eps, np.abs(cov1), np.where(np.abs(cov2) > eps, np.abs(cov2), eps))
    percent_diff = (diff / denom) * 100.0
    abs_percent = np.abs(percent_diff)
    # Mask entries where both cov1 and cov2 were effectively zero
    undefined_mask = (np.abs(cov1) <= eps) & (np.abs(cov2) <= eps)
    # Compute summary stats ignoring undefined entries
    valid_percent = abs_percent[~undefined_mask]
    max_pct = np.nan if valid_percent.size == 0 else np.nanmax(valid_percent)
    mean_pct = np.nan if valid_percent.size == 0 else np.nanmean(valid_percent)
    median_pct = np.nan if valid_percent.size == 0 else np.nanmedian(valid_percent)

    print(f"\n--- Difference Statistics ---")
    print(f"  Max Absolute Diff: {fmt(max_abs)}")
    print(f"  Mean Absolute Diff: {fmt(mean_abs)}")
    print(f"  RMS Difference: {fmt(rms)}")
    print(f"  Frobenius Norm: {fmt(frob)}")
    print(f"  Max Percent Diff: {('NaN' if np.isnan(max_pct) else f'{max_pct:.2f}%')}")
    print(f"  Mean Percent Diff: {('NaN' if np.isnan(mean_pct) else f'{mean_pct:.2f}%')}")
    print(f"  Median Percent Diff: {('NaN' if np.isnan(median_pct) else f'{median_pct:.2f}%')}")
    if np.any(undefined_mask):
        print(f"  Undefined percent entries (both values ~0): {int(np.sum(undefined_mask))}")

    # Find largest differences
    top_5_idx = np.argsort(abs_diff.flatten())[-5:][::-1] if abs_diff.size else []
    print(f"\n--- Top 5 Largest Differences (value, |value|, percent) ---")
    for rank, idx in enumerate(top_5_idx, 1):
        i, j = np.unravel_index(idx, abs_diff.shape)
        pct = percent_diff[i, j]
        pct_str = 'NaN' if undefined_mask[i, j] else f"{pct:.2f}%"
        print(f"  {rank}. Position ({i},{j}): {fmt(diff[i,j])} (|{fmt(abs_diff[i,j])}|), {pct_str}")

    print("="*60 + "\n")


def plot_complex_components(mat: np.ndarray,
                            title_root: str = "Matrix",
                            output_path: Optional[str] = None,
                            value_unit: Optional[str] = None,
                            show: bool = True) -> None:
    """Plot 2x2 components of a complex matrix: magnitude, real, imag, phase.

    Args:
        mat: Complex-valued 2D array
        title_root: Base title for subplots
        output_path: Optional path to save the figure (will append suffix)
        value_unit: Optional unit string to append to magnitude/real/imag colorbars
    """
    # Prepare components
    mag = np.abs(mat)
    real = np.real(mat)
    imag = np.imag(mat)
    phase = np.angle(mat)  # radians

    rcParams.update({'font.size': 11, 'axes.titlesize': 12, 'axes.titleweight': 'bold'})
    plt.style.use('ggplot')

    fig, axes = plt.subplots(2, 2, figsize=(10, 10), constrained_layout=True)
    ax1, ax2, ax3, ax4 = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]

    # Magnitude
    im1 = ax1.imshow(mag, cmap='viridis', origin='lower', interpolation='nearest')
    ax1.set_title(f"{title_root} — Magnitude")
    ax1.set_aspect('equal')
    c1 = fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.02)
    c1.set_label(f"Magnitude {value_unit}" if value_unit else "Magnitude")

    # Real
    vmax = max(np.nanmax(np.abs(real)), np.finfo(float).eps)
    im2 = ax2.imshow(real, cmap='RdBu_r', vmin=-vmax, vmax=vmax, origin='lower', interpolation='nearest')
    ax2.set_title(f"{title_root} — Real")
    ax2.set_aspect('equal')
    c2 = fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.02)
    c2.set_label(f"Real {value_unit}" if value_unit else "Real")

    # Imag
    vmax_i = max(np.nanmax(np.abs(imag)), np.finfo(float).eps)
    im3 = ax3.imshow(imag, cmap='RdBu_r', vmin=-vmax_i, vmax=vmax_i, origin='lower', interpolation='nearest')
    ax3.set_title(f"{title_root} — Imag")
    ax3.set_aspect('equal')
    c3 = fig.colorbar(im3, ax=ax3, fraction=0.046, pad=0.02)
    c3.set_label(f"Imag {value_unit}" if value_unit else "Imag")

    # Phase
    im4 = ax4.imshow(phase, cmap='twilight', vmin=-np.pi, vmax=np.pi, origin='lower', interpolation='nearest')
    ax4.set_title(f"{title_root} — Phase")
    ax4.set_aspect('equal')
    c4 = fig.colorbar(im4, ax=ax4, fraction=0.046, pad=0.02)
    c4.set_label('Phase (rad)')

    if output_path:
        out_path = Path(output_path)
        # append suffix if output path looks like a file
        if out_path.suffix:
            save_path = str(out_path.with_name(out_path.stem + '_components' + out_path.suffix))
        else:
            save_path = str(out_path / (title_root + '_components.png'))
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Complex components figure saved to {save_path}")

    if show:
        plt.show()
    else:
        plt.close(fig)

# Usage example
if __name__ == "__main__":
    # Load matrices
    
    cov1, cov2 = load_covariance_matrices("/data/garbage/SNR/misc/RSS_VB2/NC.npy", "/data/garbage/SNR/misc/RSS_VB2_multiraid/NC.npy")
    
    # Plot and generate report
    # Save comparison figure (no interactive show) and complex-component figures for each matrix
    plot_covariance_comparison(cov1, cov2,
                               title1="Covariance Matrix 1",
                               title2="Covariance Matrix 2",
                               output_path="covariance_comparison.png",
                               value_unit='(a.u.)',
                               show=False)

    # Save complex components for cov1 and cov2
    plot_complex_components(cov1, title_root='Covariance1', output_path='cov1.png', value_unit='(a.u.)', show=False)
    plot_complex_components(cov2, title_root='Covariance2', output_path='cov2.png', value_unit='(a.u.)', show=False)

    # Optionally also save for the difference matrix
    diff = cov2 - cov1
    plot_complex_components(diff, title_root='CovarianceDiff', output_path='cov_diff.png', value_unit='(a.u.)', show=False)
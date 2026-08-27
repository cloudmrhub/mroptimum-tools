import nibabel as nib
import numpy as np
import pyvista as pv


def make_box_edges(corners):
    """
    corners must be ordered:
        0..3 = bottom rectangle
        4..7 = top rectangle
    """

    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]

    lines = []

    for a, b in edges:
        lines.extend([2, a, b])

    poly = pv.PolyData()
    poly.points = corners
    poly.lines = np.array(lines)

    return poly


def slice_box_corners(img, axis, k):
    """
    Return the 8 physical-space corners of one voxel-thick slice.

    Importantly, this uses voxel BOUNDARIES:
        k - 0.5
        k + 0.5

    rather than just voxel centers.
    """

    shape = img.shape[:3]
    affine = img.affine

    # full physical extent of the two in-plane directions
    bounds = [
        (-0.5, shape[0] - 0.5),
        (-0.5, shape[1] - 0.5),
        (-0.5, shape[2] - 0.5),
    ]

    # this particular slice occupies k ± 0.5
    bounds[axis] = (k - 0.5, k + 0.5)

    other = [i for i in range(3) if i != axis]
    u, v = other

    corners_voxel = []

    # lower face
    for uu, vv in [
        (bounds[u][0], bounds[v][0]),
        (bounds[u][1], bounds[v][0]),
        (bounds[u][1], bounds[v][1]),
        (bounds[u][0], bounds[v][1]),
    ]:
        p = np.zeros(3)
        p[axis] = bounds[axis][0]
        p[u] = uu
        p[v] = vv
        corners_voxel.append(p)

    # upper face
    for uu, vv in [
        (bounds[u][0], bounds[v][0]),
        (bounds[u][1], bounds[v][0]),
        (bounds[u][1], bounds[v][1]),
        (bounds[u][0], bounds[v][1]),
    ]:
        p = np.zeros(3)
        p[axis] = bounds[axis][1]
        p[u] = uu
        p[v] = vv
        corners_voxel.append(p)

    corners_voxel = np.asarray(corners_voxel)

    return nib.affines.apply_affine(
        affine,
        corners_voxel
    )


def add_pancake_stack(
    plotter,
    filename,
    axis=2,
    color="red",
    label="volume",
    slice_step=1,
    opacity=0.65,
    line_width=2,
):
    img = nib.load(filename)

    print("\n-----------------------------------")
    print(label)
    print("-----------------------------------")
    print("Shape:", img.shape)
    print("Voxel spacing:", img.header.get_zooms()[:3])
    print("Orientation:", nib.aff2axcodes(img.affine))
    print("Affine:")
    print(img.affine)

    nslices = img.shape[axis]

    # direction and spacing of slice axis
    slice_vector = img.affine[:3, axis]

    print("Slice vector:", slice_vector)
    print("Slice spacing:", np.linalg.norm(slice_vector), "mm")

    for k in range(0, nslices, slice_step):

        corners = slice_box_corners(
            img,
            axis,
            k
        )

        edges = make_box_edges(corners)

        plotter.add_mesh(
            edges,
            color=color,
            opacity=opacity,
            line_width=line_width,
        )


def compare_slice_geometry(
    file1,
    file2,
    axis=2,
    slice_step=1,
):
    plotter = pv.Plotter()
    plotter.set_background("black")

    add_pancake_stack(
        plotter,
        file1,
        axis=axis,
        color="red",
        label="SNR",
        slice_step=slice_step,
    )

    add_pancake_stack(
        plotter,
        file2,
        axis=axis,
        color="cyan",
        label="FA",
        slice_step=slice_step,
    )

    plotter.add_axes(
        xlabel="X",
        ylabel="Y",
        zlabel="Z"
    )

    plotter.show_grid(
        xlabel="X [mm]",
        ylabel="Y [mm]",
        zlabel="Z [mm]"
    )

    # Extremely useful for medical-image geometry
    plotter.enable_parallel_projection()

    plotter.show()


compare_slice_geometry(
    "/data/garbage/FA-test/output_product_coil_b1/data/SNR.nii.gz",
    "/data/garbage/FA-test/tfl_b1map_sag17_7001_MR/_tfl_b1map_sag17_20260809095310_7001.nii",
    axis=2,
    slice_step=1,
)
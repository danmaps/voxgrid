import numpy as np
from typing import Tuple, Optional


def voxelize_points(
    xyz: np.ndarray,
    voxel_size: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    bounds: Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float]]] = None,
) -> Tuple[np.ndarray, np.ndarray, Tuple[int, int, int]]:
    """
    Convert point cloud (N,3) array into a regular 3D voxel grid using simple counts per voxel.

    Parameters
    ----------
    xyz : np.ndarray
        Array of shape (N,3) with columns x, y, z (float).
    voxel_size : (sx, sy, sz)
        Size of each voxel cell in the same units as xyz.
    bounds : ((xmin, ymin, zmin), (xmax, ymax, zmax)) or None
        Explicit bounds for the grid. If None, they are computed from data min/max.

    Returns
    -------
    grid : np.ndarray
        3D array (shape) with integer counts per voxel.
    origin : np.ndarray
        3-element array [xmin, ymin, zmin] used as origin for the grid.
    shape : (nx, ny, nz)
        Number of voxels along each axis.
    """
    if xyz.ndim != 2 or xyz.shape[1] != 3:
        raise ValueError("xyz must be a (N,3) array")

    xyz = np.asarray(xyz, dtype=np.float32)

    if bounds is None:
        mn = xyz.min(axis=0)
        mx = xyz.max(axis=0)
    else:
        mn = np.array(bounds[0], dtype=np.float32)
        mx = np.array(bounds[1], dtype=np.float32)

    vs = np.array(voxel_size, dtype=np.float32)
    shape = np.ceil((mx - mn) / vs).astype(int)
    shape = np.maximum(shape, 1)  # ensure at least 1 cell per axis

    # Map points to integer voxel indices
    ijk = np.floor((xyz - mn) / vs).astype(int)
    ijk = np.clip(ijk, 0, shape - 1)

    # Aggregate counts per voxel via linear indices
    linear_idx = np.ravel_multi_index(ijk.T, shape)
    counts = np.bincount(linear_idx, minlength=int(np.prod(shape))).reshape(shape)

    return counts, mn, tuple(int(x) for x in shape)


def slice2d(grid: np.ndarray, axis: str, idx: int) -> np.ndarray:
    """
    Extract a 2D slice from a 3D grid along axis 'X' | 'Y' | 'Z'.
    """
    axis = axis.upper()
    if axis not in {"X", "Y", "Z"}:
        raise ValueError("axis must be one of 'X', 'Y', 'Z'")

    if axis == "Z":
        idx = max(0, min(idx, grid.shape[2] - 1))
        return grid[:, :, idx]
    if axis == "Y":
        idx = max(0, min(idx, grid.shape[1] - 1))
        return grid[:, idx, :]
    # X
    idx = max(0, min(idx, grid.shape[0] - 1))
    return grid[idx, :, :]


def voxel_centers(indices: np.ndarray, origin: np.ndarray, voxel_size: Tuple[float, float, float]) -> np.ndarray:
    """
    Convert voxel indices (N,3) to world coordinates at voxel centers.
    """
    vs = np.array(voxel_size, dtype=np.float32)
    return origin + (indices.astype(np.float32) + 0.5) * vs


def voxelize_labeled_points(
    xyz: np.ndarray,
    labels: np.ndarray,
    voxel_size: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    bounds: Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float]]] = None,
):
    """
    Voxelize points with categorical labels. Returns total grid, origin, shape, and per-label grids.

    Parameters
    ----------
    xyz : (N,3) float32
    labels : (N,) int or uint8, category id per point
    voxel_size : (sx, sy, sz)
    bounds : optional explicit bounds

    Returns
    -------
    total_grid : np.ndarray (nx, ny, nz)
    origin : np.ndarray (3,)
    shape : (nx, ny, nz)
    label_grids : dict[int, np.ndarray] mapping label -> grid counts
    """
    if xyz.ndim != 2 or xyz.shape[1] != 3:
        raise ValueError("xyz must be a (N,3) array")
    if labels.ndim != 1 or labels.shape[0] != xyz.shape[0]:
        raise ValueError("labels must be a (N,) array aligned with xyz")

    xyz = np.asarray(xyz, dtype=np.float32)
    labels = np.asarray(labels)

    if bounds is None:
        mn = xyz.min(axis=0)
        mx = xyz.max(axis=0)
    else:
        mn = np.array(bounds[0], dtype=np.float32)
        mx = np.array(bounds[1], dtype=np.float32)

    vs = np.array(voxel_size, dtype=np.float32)
    shape = np.ceil((mx - mn) / vs).astype(int)
    shape = np.maximum(shape, 1)

    ijk = np.floor((xyz - mn) / vs).astype(int)
    ijk = np.clip(ijk, 0, shape - 1)
    linear_idx = np.ravel_multi_index(ijk.T, shape)

    total_counts = np.bincount(linear_idx, minlength=int(np.prod(shape))).reshape(shape)

    label_grids = {}
    for lab in np.unique(labels):
        mask = labels == lab
        li = linear_idx[mask]
        if li.size == 0:
            label_grids[int(lab)] = np.zeros(shape, dtype=np.int64)
        else:
            label_grids[int(lab)] = np.bincount(li, minlength=int(np.prod(shape))).reshape(shape)

    return total_counts, mn, tuple(int(x) for x in shape), label_grids


def voxelize_to_voxel_grid(
    xyz: np.ndarray,
    labels: np.ndarray,
    voxel_size: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    bounds: Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float]]] = None,
) -> Tuple[np.ndarray, np.ndarray, Tuple[int, int, int]]:
    """
    Create a true voxel grid (3D array of category IDs) from labeled point cloud, VoxCity-style.
    
    Steps:
    1. Aggregate points to 2D horizontal grid (xy plane)
    2. Per cell: find dominant label and max height
    3. Extrude each cell vertically to create 3D voxel grid
    
    Parameters
    ----------
    xyz : (N,3) float32
    labels : (N,) uint8 category IDs
    voxel_size : (sx, sy, sz)
    bounds : optional explicit bounds
    
    Returns
    -------
    voxel_grid : (nx, ny, nz) uint8 array of category IDs (0=void/air)
    origin : (3,) array
    shape : (nx, ny, nz) tuple
    """
    if xyz.ndim != 2 or xyz.shape[1] != 3:
        raise ValueError("xyz must be a (N,3) array")
    if labels.ndim != 1 or labels.shape[0] != xyz.shape[0]:
        raise ValueError("labels must be (N,) aligned with xyz")
    
    xyz = np.asarray(xyz, dtype=np.float32)
    labels = np.asarray(labels, dtype=np.uint8)
    
    if bounds is None:
        mn = xyz.min(axis=0)
        mx = xyz.max(axis=0)
    else:
        mn = np.array(bounds[0], dtype=np.float32)
        mx = np.array(bounds[1], dtype=np.float32)
    
    vs = np.array(voxel_size, dtype=np.float32)
    
    # 2D horizontal grid (xy plane only)
    shape_2d = np.ceil((mx[:2] - mn[:2]) / vs[:2]).astype(int)
    shape_2d = np.maximum(shape_2d, 1)
    
    # Map xy to 2D grid indices
    ij = np.floor((xyz[:, :2] - mn[:2]) / vs[:2]).astype(int)
    ij = np.clip(ij, 0, shape_2d - 1)
    
    # Aggregate: per cell, find dominant label and max height
    cell_to_label = {}
    cell_to_maxz = {}
    for idx, (i, j) in enumerate(ij):
        key = (i, j)
        label = labels[idx]
        z = xyz[idx, 2]
        if key not in cell_to_label:
            cell_to_label[key] = [label]
            cell_to_maxz[key] = z
        else:
            cell_to_label[key].append(label)
            cell_to_maxz[key] = max(cell_to_maxz[key], z)
    
    # Determine dominant label per cell
    cell_dominant = {}
    for key, label_list in cell_to_label.items():
        # Most common label in the cell
        unique, counts = np.unique(label_list, return_counts=True)
        cell_dominant[key] = unique[np.argmax(counts)]
    
    # Determine z-extent
    z_min = mn[2]
    z_max_vals = list(cell_to_maxz.values())
    if z_max_vals:
        z_max = max(z_max_vals)
    else:
        z_max = z_min + vs[2]
    
    # Number of voxels in z direction
    nz = max(1, int(np.ceil((z_max - z_min) / vs[2])))
    
    # Create 3D voxel grid (initialized to 0 = void/air)
    voxel_grid = np.zeros((shape_2d[0], shape_2d[1], nz), dtype=np.uint8)
    
    # Create dense synthetic ground plane: fill entire base layer with terrain (category 0)
    # This ensures wall-to-wall continuous ground coverage independent of sparse point data
    voxel_grid[:, :, 0] = 0  # terrain/water base at z=0 for ALL xy positions
    
    # Extrude each cell vertically (will overwrite base terrain where buildings/roads/trees exist)
    for (i, j), label in cell_dominant.items():
        max_z = cell_to_maxz[(i, j)]
        # Number of voxels to fill from z_min to max_z
        n_fill = int(np.ceil((max_z - z_min) / vs[2]))
        n_fill = min(n_fill, nz)  # Clip to grid bounds
        if n_fill > 0:
            voxel_grid[i, j, :n_fill] = label
    
    origin = mn
    shape = tuple([shape_2d[0], shape_2d[1], nz])
    
    return voxel_grid, origin, shape

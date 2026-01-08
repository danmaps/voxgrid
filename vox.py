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

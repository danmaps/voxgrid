"""
Voxel to mesh conversion for proper cubic rendering, inspired by VoxCity.
"""
import numpy as np
from typing import Tuple, Dict, List


def voxel_grid_to_mesh_faces(
    voxel_grid: np.ndarray,
    voxel_size: Tuple[float, float, float],
    origin: np.ndarray,
) -> Dict[int, Dict[str, np.ndarray]]:
    """
    Convert a voxel grid to mesh faces (vertices and triangles) per category.
    Only generates faces for exposed surfaces (not occluded by adjacent voxels).
    
    Returns
    -------
    Dict mapping category_id -> {'vertices': (N,3), 'faces': (M,3)}
    """
    nx, ny, nz = voxel_grid.shape
    dx, dy, dz = voxel_size
    
    # Create occluder mask (any non-zero voxel blocks)
    occluder = (voxel_grid != 0)
    
    result = {}
    categories = np.unique(voxel_grid)
    # Include category 0 (terrain/ground) if present, but process it specially to avoid generating interior faces
    
    for cat_id in categories:
        # For terrain (0), only generate bottom faces to avoid rendering interior voxels
        if cat_id == 0:
            # Limit terrain rendering to the ground plane (z==0) so it doesn't fill all empty space
            z0_mask = np.zeros_like(voxel_grid, dtype=bool)
            z0_mask[:, :, 0] = True
            cat_mask = (voxel_grid == cat_id) & z0_mask
            
            # Render the top surface of the terrain base (ground plane)
            pad_above = np.pad(occluder, ((0,0),(0,0),(0,1)), constant_values=False)
            posz = cat_mask & (~pad_above[:,:,1:])
            
            verts, faces = _generate_face_geometry(posz, '+z', voxel_size, origin)
            if verts.size > 0:
                result[0] = {
                    'vertices': verts,
                    'faces': faces
                }
            continue
        
        cat_mask = (voxel_grid == cat_id)
        
        # Find exposed faces by checking neighbors
        # +x face: exposed if no voxel at [i+1, j, k]
        pad_right = np.pad(occluder, ((0,1),(0,0),(0,0)), constant_values=False)
        posx = cat_mask & (~pad_right[1:,:,:])
        
        # -x face: exposed if no voxel at [i-1, j, k]
        pad_left = np.pad(occluder, ((1,0),(0,0),(0,0)), constant_values=False)
        negx = cat_mask & (~pad_left[:-1,:,:])
        
        # +y face: exposed if no voxel at [i, j+1, k]
        pad_top = np.pad(occluder, ((0,0),(0,1),(0,0)), constant_values=False)
        posy = cat_mask & (~pad_top[:,1:,:])
        
        # -y face: exposed if no voxel at [i, j-1, k]
        pad_bottom = np.pad(occluder, ((0,0),(1,0),(0,0)), constant_values=False)
        negy = cat_mask & (~pad_bottom[:,:-1,:])
        
        # +z face: exposed if no voxel at [i, j, k+1]
        pad_above = np.pad(occluder, ((0,0),(0,0),(0,1)), constant_values=False)
        posz = cat_mask & (~pad_above[:,:,1:])
        
        # -z face: exposed if no voxel at [i, j, k-1]
        pad_below = np.pad(occluder, ((0,0),(0,0),(1,0)), constant_values=False)
        negz = cat_mask & (~pad_below[:,:,:-1])
        
        # Collect all vertices and faces
        all_verts = []
        all_faces = []
        vert_offset = 0
        
        for mask, plane in [(posx, '+x'), (negx, '-x'), (posy, '+y'), 
                            (negy, '-y'), (posz, '+z'), (negz, '-z')]:
            verts, faces = _generate_face_geometry(mask, plane, voxel_size, origin)
            if verts.size > 0:
                all_verts.append(verts)
                all_faces.append(faces + vert_offset)
                vert_offset += len(verts)
        
        if all_verts:
            result[int(cat_id)] = {
                'vertices': np.vstack(all_verts),
                'faces': np.vstack(all_faces)
            }
    
    return result


def _generate_face_geometry(
    mask: np.ndarray,
    plane: str,
    voxel_size: Tuple[float, float, float],
    origin: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate vertices and triangle indices for one face direction."""
    idx = np.argwhere(mask)
    if idx.size == 0:
        return np.empty((0, 3)), np.empty((0, 3), dtype=np.int32)
    
    dx, dy, dz = voxel_size
    
    # Voxel centers
    xi, yi, zi = idx[:, 0], idx[:, 1], idx[:, 2]
    xc = origin[0] + xi * dx
    yc = origin[1] + yi * dy
    zc = origin[2] + zi * dz
    
    # Voxel corners
    x0, x1 = xc - dx/2, xc + dx/2
    y0, y1 = yc - dy/2, yc + dy/2
    z0, z1 = zc - dz/2, zc + dz/2
    
    # Generate quad vertices for each face
    if plane == '+x':
        v0 = np.stack([x1, y0, z0], axis=1)
        v1 = np.stack([x1, y1, z0], axis=1)
        v2 = np.stack([x1, y1, z1], axis=1)
        v3 = np.stack([x1, y0, z1], axis=1)
    elif plane == '-x':
        v0 = np.stack([x0, y0, z1], axis=1)
        v1 = np.stack([x0, y1, z1], axis=1)
        v2 = np.stack([x0, y1, z0], axis=1)
        v3 = np.stack([x0, y0, z0], axis=1)
    elif plane == '+y':
        v0 = np.stack([x0, y1, z0], axis=1)
        v1 = np.stack([x1, y1, z0], axis=1)
        v2 = np.stack([x1, y1, z1], axis=1)
        v3 = np.stack([x0, y1, z1], axis=1)
    elif plane == '-y':
        v0 = np.stack([x0, y0, z1], axis=1)
        v1 = np.stack([x1, y0, z1], axis=1)
        v2 = np.stack([x1, y0, z0], axis=1)
        v3 = np.stack([x0, y0, z0], axis=1)
    elif plane == '+z':
        v0 = np.stack([x0, y0, z1], axis=1)
        v1 = np.stack([x1, y0, z1], axis=1)
        v2 = np.stack([x1, y1, z1], axis=1)
        v3 = np.stack([x0, y1, z1], axis=1)
    elif plane == '-z':
        v0 = np.stack([x0, y1, z0], axis=1)
        v1 = np.stack([x1, y1, z0], axis=1)
        v2 = np.stack([x1, y0, z0], axis=1)
        v3 = np.stack([x0, y0, z0], axis=1)
    else:
        return np.empty((0, 3)), np.empty((0, 3), dtype=np.int32)
    
    # Stack vertices: 4 per quad
    vertices = np.stack([v0, v1, v2, v3], axis=1).reshape(-1, 3)
    
    # Generate triangle indices: 2 triangles per quad
    n_quads = len(idx)
    base = np.arange(0, 4 * n_quads, 4, dtype=np.int32)
    tri1 = np.stack([base, base+1, base+2], axis=1)
    tri2 = np.stack([base, base+2, base+3], axis=1)
    faces = np.vstack([tri1, tri2])
    
    return vertices, faces

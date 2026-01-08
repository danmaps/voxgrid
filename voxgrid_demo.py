import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from typing import Optional

from vox import voxelize_points, slice2d, voxel_centers, voxelize_labeled_points, voxelize_to_voxel_grid
from tools.voxcity_api import generate_voxcity_points, generate_voxcity_points_labeled
from tools.voxcity_colors import VOXCITY_COLORS, LABEL_NAMES
from tools.voxel_mesh import voxel_grid_to_mesh_faces

st.set_page_config(layout="wide", page_title="VoxGrid")
st.title("VoxGrid")
st.caption("Upload point data or fetch VoxCity sources, voxelize with NumPy, and explore slices.")

@st.cache_data
def load_xyz_from_npz(data: BytesIO) -> np.ndarray:
    buf = BytesIO(data.read())
    npz = np.load(buf)
    if "xyz" in npz:
        xyz = npz["xyz"]
    else:
        if all(k in npz for k in ("x", "y", "z")):
            xyz = np.vstack([npz["x"], npz["y"], npz["z"]]).T
        else:
            raise ValueError("NPZ must contain 'xyz' or ('x','y','z') arrays")
    return xyz.astype(np.float32)

@st.cache_data
def load_xyz_from_csv(data: BytesIO, has_header: bool = True) -> np.ndarray:
    text = data.read().decode("utf-8")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    start = 1 if has_header else 0
    pts = []
    for ln in lines[start:]:
        parts = ln.replace("\t", ",").split(",")
        if len(parts) < 3:
            continue
        x, y, z = map(float, parts[:3])
        pts.append((x, y, z))
    if not pts:
        raise ValueError("CSV must have at least 1 data row with x,y,z")
    return np.asarray(pts, dtype=np.float32)

@st.cache_data
def make_vox(xyz: np.ndarray, voxel_size: float, bounds: Optional[tuple] = None):
    grid, origin, shape = voxelize_points(xyz, (voxel_size, voxel_size, voxel_size), bounds=bounds)
    return grid, origin, shape

# Sidebar for controls
with st.sidebar:
    st.subheader("📊 Data & Settings")
    f = st.file_uploader("Upload .npz (xyz) or .csv (x,y,z)", type=["npz", "csv"])
    voxel_size = st.number_input("Voxel size (meters)", value=1.0, min_value=0.1, step=0.1)
    thr = st.number_input("Threshold (min count per voxel)", value=1, min_value=0, step=1)
    st.markdown("---")
    st.subheader("🌎 VoxCity Sources")
    use_voxcity = st.checkbox("Use VoxCity (OSM buildings/roads + greens)", value=True)
    st.caption("Uses Overpass API; may take ~10-40s depending on area.")
    st.markdown("**Area (Lon/Lat bbox):**")
    min_lon = st.number_input("min_lon", value=-74.020343, format="%.6f")
    min_lat = st.number_input("min_lat", value=40.699929, format="%.6f")
    max_lon = st.number_input("max_lon", value=-74.005551, format="%.6f")
    max_lat = st.number_input("max_lat", value=40.711185, format="%.6f")
    voxcity_colors = st.checkbox("Use VoxCity categorical colors", value=True)
    solid_voxels = st.checkbox("Render as solid voxels (VoxCity-style)", value=True)
    terrain_exag = st.slider("Terrain vertical exaggeration", min_value=1.0, max_value=10.0, value=1.0, step=0.5)
    with st.expander("Advanced (Overpass)"):
        skip_verify = st.checkbox("Skip SSL verification (corporate proxies)", value=True)
        timeout_sec = st.number_input("Timeout (seconds)", value=90, min_value=10, step=10)

xyz = None
f_uploader = st.sidebar.file_uploader if 'f' in locals() else None

# Re-read file uploader from sidebar context
if f is not None:
    try:
        if f.type == "application/octet-stream" or f.name.endswith(".npz"):
            xyz = load_xyz_from_npz(f)
        elif f.type in ("text/csv", "application/vnd.ms-excel") or f.name.endswith(".csv"):
            xyz = load_xyz_from_csv(f, has_header=True)
        else:
            st.error("Unsupported file type. Please upload .npz or .csv")
    except Exception as e:
        st.error(f"Failed to load data: {e}")

if xyz is None:
    if use_voxcity:
        with st.status("Fetching VoxCity data...", expanded=True) as status:
            try:
                bbox = (float(min_lon), float(min_lat), float(max_lon), float(max_lat))
                
                def progress(msg):
                    st.write(f"➤ {msg}")
                
                xyz, labels = generate_voxcity_points_labeled(
                    bbox,
                    voxel_size_m=float(voxel_size),
                    verify_ssl=not bool(skip_verify),
                    timeout=int(timeout_sec),
                    progress_callback=progress,
                )
                if xyz.size == 0:
                    st.warning("No features returned for this area; falling back to synthetic cloud.")
                else:
                    unique, counts = np.unique(labels, return_counts=True)
                    for lab, cnt in zip(unique, counts):
                        st.write(f"  {LABEL_NAMES.get(lab, f'Cat {lab}')}: {cnt} points")
                    status.update(label="✓ VoxCity data loaded", state="complete")
            except Exception as e:
                st.error(f"Failed to fetch VoxCity sources: {e}")
                st.info("Tip: Try enabling 'Skip SSL verification' or increasing timeout, or retry later.")
                xyz = None
                labels = None
                status.update(label="✗ Failed to fetch", state="error")

    if xyz is None or xyz.size == 0:
        st.info("No file or VoxCity data available. Generating a synthetic point cloud for demo.")
        # synthetic: sphere shell
        n = 100_000
        rng = np.random.default_rng(42)
        phi = rng.uniform(0, 2*np.pi, n)
        costheta = rng.uniform(-1, 1, n)
        u = rng.uniform(0.9, 1.0, n)  # shell thickness
        theta = np.arccos(costheta)
        r = u * 50.0
        x = r * np.sin(theta) * np.cos(phi)
        y = r * np.sin(theta) * np.sin(phi)
        z = r * np.cos(theta)
        xyz = np.vstack([x,y,z]).T.astype(np.float32)
        labels = None

# Initialize voxel_grid and grid to None (will be set below)
voxel_grid = None
grid = None
label_grids = None

# Apply terrain vertical exaggeration to z-coordinates if used
if use_voxcity and terrain_exag > 1.0:
    xyz_scaled = xyz.copy()
    xyz_scaled[:, 2] = xyz[:, 2] * terrain_exag
else:
    xyz_scaled = xyz

# Voxelization
if use_voxcity and labels is not None:
    if solid_voxels:
        # Create true voxel grid (3D array of category IDs)
        voxel_grid, origin, shape = voxelize_to_voxel_grid(xyz_scaled, labels, (voxel_size, voxel_size, voxel_size))
        grid = None  # Use voxel_grid for rendering instead
    else:
        total_grid, origin, shape, label_grids = voxelize_labeled_points(xyz_scaled, labels, (voxel_size, voxel_size, voxel_size))
        grid = total_grid
        voxel_grid = None
else:
    grid, origin, shape = make_vox(xyz_scaled, voxel_size)
    voxel_grid = None

# Display grid info
st.markdown(f"**Grid:** {shape} | **Origin:** {tuple(round(x, 2) for x in origin)}")

# Primary: Large 3D preview
st.markdown("## 3D Voxel Preview")

if voxel_grid is not None and solid_voxels:
    # Render solid voxel grid using Mesh3d (VoxCity-style cubic voxels)
    mask_3d = voxel_grid > 0
    if not np.any(mask_3d):
        st.info("No voxels in the grid.")
    else:
        import plotly.graph_objects as go
        
        # Convert voxel grid to mesh faces
        mesh_data = voxel_grid_to_mesh_faces(voxel_grid, (voxel_size, voxel_size, voxel_size), origin)
        
        if not mesh_data:
            st.info("No mesh faces generated.")
        else:
            fig3d = go.Figure()
            
            # Lighting setup (VoxCity-style)
            cx = (origin[0] + voxel_grid.shape[0] * voxel_size / 2)
            cy = (origin[1] + voxel_grid.shape[1] * voxel_size / 2)
            cz = (origin[2] + voxel_grid.shape[2] * voxel_size / 2)
            extent = max(voxel_grid.shape[0] * voxel_size, voxel_grid.shape[1] * voxel_size, voxel_grid.shape[2] * voxel_size)
            lx = cx + extent * 0.9
            ly = cy + extent * 0.6
            lz = cz + extent * 1.4
            
            lighting = dict(ambient=0.35, diffuse=1.0, specular=0.4, roughness=0.5, fresnel=0.1)
            
            # Add mesh trace for each category (terrain first, then buildings last for proper depth)
            for cat_id in [0, 3, 2, 1]:  # terrain, vegetation, roads, buildings
                if cat_id not in mesh_data:
                    continue
                
                V = mesh_data[cat_id]['vertices']
                F = mesh_data[cat_id]['faces']
                
                color_hex = VOXCITY_COLORS.get(cat_id, '#888888')
                # Convert hex to rgb string
                r = int(color_hex[1:3], 16)
                g = int(color_hex[3:5], 16)
                b = int(color_hex[5:7], 16)
                color_str = f'rgb({r},{g},{b})'
                
                fig3d.add_trace(go.Mesh3d(
                    x=V[:, 0], y=V[:, 1], z=V[:, 2],
                    i=F[:, 0], j=F[:, 1], k=F[:, 2],
                    color=color_str,
                    opacity=1.0,
                    flatshading=False,
                    lighting=lighting,
                    lightposition=dict(x=lx, y=ly, z=lz),
                    showscale=False,
                    name=LABEL_NAMES.get(cat_id, f'Cat {cat_id}')
                ))
            
            fig3d.update_layout(
                scene=dict(
                    xaxis_title="X (m)",
                    yaxis_title="Y (m)", 
                    zaxis_title="Z (m)",
                    aspectmode='data',
                    camera=dict(eye=dict(x=1.6, y=1.6, z=1.0))
                ),
                margin=dict(l=0, r=0, b=0, t=30),
                height=700,
                legend=dict(orientation='h')
            )
            st.plotly_chart(fig3d, use_container_width=True)
elif grid is not None:
    # Render point-based density grid
    mask_3d = grid >= thr
    if not np.any(mask_3d):
        st.info("No voxels above threshold in the entire grid.")
    else:
        indices = np.argwhere(mask_3d)
        # downsample for perf
        max_pts = 30000
        if indices.shape[0] > max_pts:
            rng = np.random.default_rng(0)
            sel = rng.choice(indices.shape[0], max_pts, replace=False)
            indices = indices[sel]

        centers = voxel_centers(indices, origin, (voxel_size, voxel_size, voxel_size))
        import plotly.graph_objects as go

        fig3d = go.Figure()

        if use_voxcity and 'label_grids' in locals() and voxcity_colors:
            # Determine dominant category per voxel index
            # Build a stack in label id order 0..3; missing labels treated as zeros
            cats = [0,1,2,3]
            cat_grids = [label_grids.get(c, np.zeros_like(grid)) for c in cats]
            cat_counts = np.stack(cat_grids, axis=-1)  # (nx,ny,nz, C)
            # Extract per-index category
            cat_vals = cat_counts[indices[:,0], indices[:,1], indices[:,2], :]
            dom = np.argmax(cat_vals, axis=1)  # index into cats
            # Create separate traces per category
            for c_idx, c in enumerate(cats):
                sel = dom == c_idx
                if not np.any(sel):
                    continue
                pts = centers[sel]
                fig3d.add_trace(go.Scatter3d(
                    x=pts[:,0], y=pts[:,1], z=pts[:,2],
                    mode='markers',
                    marker=dict(size=2, color=VOXCITY_COLORS.get(c, '#888'), opacity=0.85),
                    name=LABEL_NAMES.get(c, f'Cat {c}')
                ))
            fig3d.update_layout(legend=dict(orientation='h'))
        else:
            # Density coloring fallback
            values = grid[mask_3d]
            if values.shape[0] > max_pts:
                values = values[sel]
            fig3d.add_trace(go.Scatter3d(
                x=centers[:,0], y=centers[:,1], z=centers[:,2],
                mode='markers',
                marker=dict(size=2, color=values, colorscale='Viridis', opacity=0.8, showscale=True, colorbar=dict(title='Density'))
            ))

        fig3d.update_layout(scene=dict(aspectmode='data'), margin=dict(l=0,r=0,b=0,t=30), height=600)
        st.plotly_chart(fig3d, width=1200)
else:
    st.info("No data to display.")

st.markdown("---")
st.caption("VoxGrid | NumPy voxelization + Streamlit | © 2026")

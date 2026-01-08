import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from typing import Optional

from vox import voxelize_points, slice2d, voxel_centers

st.set_page_config(layout="wide", page_title="VoxGrid")
st.title("VoxGrid")
st.caption("Upload simple point data, voxelize with NumPy, and explore slices.")

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

left, right = st.columns([1,1])
with left:
    st.subheader("1) Upload point data")
    f = st.file_uploader("Upload .npz (xyz) or .csv (x,y,z)", type=["npz", "csv"])
    voxel_size = st.number_input("Voxel size (meters)", value=2.0, min_value=0.1, step=0.1)
    thr = st.number_input("Threshold (min count per voxel)", value=5, min_value=0, step=1)
    axis = st.selectbox("Slice axis", options=["Z","Y","X"], index=0)
    idx = st.number_input("Slice index", value=0, min_value=0, step=1)

    xyz = None
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
        st.info("No file uploaded. Generating a synthetic point cloud for demo.")
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

    grid, origin, shape = make_vox(xyz, voxel_size)
    st.write({"Grid shape": shape, "Origin": origin.tolist()})

with right:
    st.subheader("2) Explore slices and 3D preview")
    # slice
    s2d = slice2d(grid, axis, int(idx))
    fig, ax = plt.subplots(figsize=(6,5))
    im = ax.imshow(s2d.T, origin='lower', cmap='viridis', vmin=thr)
    fig.colorbar(im, ax=ax, label='density')
    ax.set_title(f"Slice {axis}[{int(idx)}]")
    st.pyplot(fig)

    st.markdown("---")
    st.markdown("### Compact 3D preview (thresholded)")
    # thresholded voxel centers
    mask = s2d >= thr  # only for selected slice, keeps perf sane
    if not np.any(mask):
        st.info("No voxels above threshold in this slice.")
    else:
        # Build indices in 3D for the selected slice
        if axis == "Z":
            zz = int(idx)
            ii, jj = np.nonzero(mask)
            indices = np.column_stack([ii, jj, np.full(ii.shape, zz)])
        elif axis == "Y":
            yy = int(idx)
            ii, kk = np.nonzero(mask)
            indices = np.column_stack([ii, np.full(ii.shape, yy), kk])
        else:  # X
            xx = int(idx)
            jj, kk = np.nonzero(mask)
            indices = np.column_stack([np.full(jj.shape, xx), jj, kk])

        # downsample for perf
        max_pts = 30000
        if indices.shape[0] > max_pts:
            rng = np.random.default_rng(0)
            sel = rng.choice(indices.shape[0], max_pts, replace=False)
            indices = indices[sel]

        centers = voxel_centers(indices, origin, (voxel_size, voxel_size, voxel_size))
        import plotly.graph_objects as go
        fig3d = go.Figure(data=[go.Scatter3d(
            x=centers[:,0], y=centers[:,1], z=centers[:,2],
            mode='markers',
            marker=dict(size=2, color=centers[:,2], colorscale='Viridis', opacity=0.8)
        )])
        fig3d.update_layout(scene=dict(aspectmode='data'), margin=dict(l=0,r=0,b=0,t=30))
        st.plotly_chart(fig3d, use_container_width=True)

st.markdown("---")
st.caption("VoxGrid | NumPy voxelization + Streamlit slices | © 2026")

# VoxGrid

A GDAL-free, Streamlit-based exploration of voxelization and visualization techniques inspired by VoxCity, applied in manageable contexts.

## Vision

VoxGrid borrows the best visualization tricks and voxelization patterns from VoxCity and applies them to scoped problems without heavy geospatial dependencies. The goal is rapid prototyping: turn simple point data (CSV/NPZ) into compelling 3D grid views with interactive slices, thresholding, and compact previews.

## What This Project Is (and Isn’t)

- Is: A lightweight, NumPy-first voxelization toolkit with Streamlit UI.
- Is: A practical demo for GIS-ish workflows using simple inputs (CSV/NPZ), point clouds (LAS via laspy), and pure Python processing.
- Isn’t: A full urban planning stack that auto-downloads multi-source GIS datasets.

## Features

- Upload `.npz` (with `xyz`) or `.csv` (`x,y,z`) point data
- Voxelize into a regular 3D grid using pure NumPy
- Explore 2D slices (X/Y/Z), with thresholds and color maps
- Compact 3D preview of thresholded voxels (Plotly)
- Optional pathways to MIP (max intensity projection) and isosurface extraction (skimage)

### VoxCity Mode (OSM-backed)

- Toggle "Use VoxCity" in the sidebar to fetch buildings, roads, and green areas from OpenStreetMap via Overpass for a given lon/lat rectangle.
- This generates a synthetic point cloud: buildings extruded by estimated heights (from OSM tags), roads as surface ribbons, greens as canopy volumes.
- Category-aware voxelization with VoxCity-inspired colors:
  - Buildings: light gray, Roads: asphalt gray, Vegetation: green, Terrain/Water: blue.
- Some networks (corporate proxies) cause SSL certificate errors. Use the sidebar "Advanced (Overpass)" → "Skip SSL verification" to work around.
- The app tries multiple Overpass mirrors; increase the timeout if requests fail intermittently.
- You can also set your proxy environment (e.g., `HTTP_PROXY`, `HTTPS_PROXY`) before running Streamlit.

## Quick Start

### 1) Create and activate a virtual environment

```powershell
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

```bash
# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Run the demo app

```bash
streamlit run voxgrid_demo.py
```

Upload `.npz` (with `xyz`) or `.csv` containing `x,y,z`. Adjust voxel size, slice axis/index, and threshold.

### 4) Convert CSV to NPZ (helper script)

```bash
python tools/make_npz_from_csv.py input.csv output.npz
```

## Project Structure

```
voxgrid/
├── vox.py                     # NumPy voxelization helpers
├── voxgrid_demo.py            # Streamlit demo app
├── tools/
│   └── make_npz_from_csv.py   # CSV → NPZ conversion helper
│   └── voxcity_api.py          # Overpass (OSM) fetch + sampling into points
├── requirements.txt           # Minimal dependencies
└── voxcity_demo.ipynb         # Original notebook (reference only)
```

## Design Principles

- Keep data ingestion simple: CSV/NPZ and LAS via `laspy`
- Favor compute in NumPy with straightforward aggregation
- Use visualization techniques that scale: slices, MIP, thresholded point previews
- Cache expensive steps; cap points rendered for browser performance

## Roadmap (Incremental)

- Add MIP view and slice heatmaps with configurable colormaps
- Optional isosurface extraction with `skimage.measure.marching_cubes` (button-triggered)
- Add LAS/LAZ upload via `laspy` and simple preprocessing
- URL state encoding for shareable deep links (axis/index/threshold)
- Lightweight analysis layers (e.g., density-based hotspots)
- Optional Earth Engine integration for DEM (USGS 3DEP), canopy (Meta Trees), landcover (UrbanWatch), and Microsoft Building Footprints enrichment

## License

Specify your license (e.g., MIT, Apache 2.0).

## Acknowledgments

- Inspired by VoxCity’s visualization and voxelization concepts
- Built with Streamlit, NumPy, Plotly, and friends
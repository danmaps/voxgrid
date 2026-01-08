# Product Requirements Document: VoxGrid (GDAL-free)

**Version:** 1.0  
**Date:** January 7, 2026  
**Status:** Draft

---

## Executive Summary

VoxGrid is a lightweight, GDAL-free Streamlit application that borrows visualization tricks and voxelization techniques from VoxCity and applies them within manageable contexts. It transforms simple point datasets (CSV/NPZ, optionally LAS via `laspy`) into interactive 3D voxel views with slice browsing, thresholding, and compact previews—enabling rapid prototyping for GIS-ish analyses without heavy geospatial dependencies.

---

## 1. Goals & Objectives

- **Rapid prototyping:** Convert simple inputs into voxel grids fast, with a frictionless setup.
- **Compelling visuals:** Provide slice views, MIP, and thresholded 3D previews that communicate structure clearly.
- **Scoped ingestion:** Favor CSV/NPZ and LAS via pure-Python readers; avoid heavyweight stacks.
- **Extensible:** Leave room for optional features (isosurfaces, LAS ingestion, URL state) as buttons/toggles.

Success Metrics:
- Setup time < 10 minutes on a clean machine
- Voxelization and initial visualization for 100k–1M points in < 5 seconds
- Smooth interaction with capped point counts in the browser

---

## 2. Users & Use Cases

- **GIS Analyst / Data Explorer:** Load small areas of point data and explore density hotspots, slices, and simple previews.
- **Engineer / Researcher:** Prototype voxel-based views for classification ideas (e.g., linearness vs. planarness), without large dependencies.
- **Ops / Planning Support:** Review snapshots quickly using MIP or thresholded views for targeted context.

Example manageable contexts:
- Point cloud subsets around assets (1–5 km²) → density grids → slices/MIP
- Vegetation proximity bands via precomputed arrays → binary voxel layers → thresholded views
- Time-differenced scans → ΔMIP to reveal change

---

## 3. Product Scope

### In Scope (MVP)
- Upload `.npz` (with `xyz`) or `.csv` (`x,y,z`)
- NumPy voxelization to 3D count grids
- Slice browsing (X/Y/Z), thresholds, colormaps
- Thresholded 3D compact preview (Plotly points, LOD cap)
- Helper script to convert CSV → NPZ

### Out of Scope (Initial)
- Automated multi-source data downloads
- Heavy geospatial stacks or runtime GIS servers
- Complex analysis pipelines beyond basic voxel aggregation

---

## 4. Features

### F1: Data Ingest (CSV/NPZ)
- Parse `.csv` with headers `x,y,z` or `.npz` with `xyz` array
- Basic validation and helpful errors

### F2: Voxelization
- Pure NumPy aggregation to 3D grid
- Configurable voxel size and optional bounds

### F3: Visualization
- Slice views with color maps and thresholds
- Compact 3D preview of thresholded voxels (capped points)
- Optional MIP (max intensity projection)

### F4: Utilities
- CSV → NPZ converter script
- Caching of expensive steps via Streamlit

---

## 5. Architecture

- **Frontend:** Streamlit (tabs, controls, caching)
- **Core compute:** NumPy voxelization (`vox.py`)
- **Visualization:** Plotly for 3D preview; Matplotlib for 2D slices
- **Optional:** `laspy` for LAS/LAZ ingest; `scikit-image` for marching cubes

---

## 6. Data & Performance

- Inputs: CSV (x,y,z), NPZ (xyz), optional LAS/LAZ
- Typical sizes: 100k–1M points
- Performance strategies:
  - Cap rendered points for 3D previews (e.g., 30k)
  - Cache voxelization results
  - Downsample for zoomed-out views

---

## 7. UX Flow

1. Upload data (CSV/NPZ)
2. Choose voxel size and thresholds
3. Inspect slice (axis/index)
4. Preview compact 3D thresholded points
5. (Optional) Export slice/MIP images

---

## 8. Roadmap

- LAS/LAZ upload using `laspy`
- MIP view and heatmaps
- Optional isosurface extraction (button-triggered) via `skimage.measure.marching_cubes`
- URL state encoding for deep-linking
- Simple analysis overlays (density hotspots)

---

## 9. Risks & Mitigations

- **Browser perf:** Cap points and cache results
- **Data variety:** Provide CSV/NPZ helper and clear schema expectations
- **Scope creep:** Keep focus on voxelization + visualization; defer heavy ingest

---

## 10. Success Criteria

- Frictionless local setup without heavy dependencies
- Clear, responsive visuals for typical point datasets
- Reusable voxelization utilities for future experiments

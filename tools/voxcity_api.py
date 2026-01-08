import json
import math
from typing import Dict, List, Tuple, Optional

import numpy as np
import requests

BBox = Tuple[float, float, float, float]  # (min_lon, min_lat, max_lon, max_lat)

# Default Overpass mirrors (ordered by typical reliability)
DEFAULT_OVERPASS_URLS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]


def meters_per_degree(lat: float) -> Tuple[float, float]:
    """Approximate meters per degree for lat/lon at a given latitude.
    Returns (meters_per_deg_lon, meters_per_deg_lat).
    """
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(lat))
    return m_per_deg_lon, m_per_deg_lat


def ll_to_local_xy(lon: float, lat: float, origin_lon: float, origin_lat: float) -> Tuple[float, float]:
    """Convert lon/lat to local meters (x,y) relative to an origin using equirectangular approximation."""
    m_per_deg_lon, m_per_deg_lat = meters_per_degree((lat + origin_lat) * 0.5)
    x = (lon - origin_lon) * m_per_deg_lon
    y = (lat - origin_lat) * m_per_deg_lat
    return x, y


def point_in_polygon(x: float, y: float, poly_xy: List[Tuple[float, float]]) -> bool:
    """Ray casting point-in-polygon test. poly_xy is a list of (x,y) tuples (closed or open)."""
    inside = False
    n = len(poly_xy)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = poly_xy[i]
        xj, yj = poly_xy[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def fetch_overpass(
    bbox: BBox,
    query_body: str,
    overpass_urls: Optional[List[str]] = None,
    verify_ssl: bool = True,
    timeout: int = 90,
    progress_callback = None,
) -> Dict:
    """Execute an Overpass API query constrained to bbox and return JSON.
    Tries multiple mirrors; raises the last error if all fail.
    progress_callback: optional callable(message_str) for status updates.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    bbox_str = f"({min_lat},{min_lon},{max_lat},{max_lon})"
    q = f"[out:json][timeout:{timeout}];{query_body.replace('{{bbox}}', bbox_str)}"
    urls = overpass_urls or DEFAULT_OVERPASS_URLS
    last_err: Optional[Exception] = None
    session = requests.Session()
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    for url in urls:
        try:
            if progress_callback:
                progress_callback(f"Querying {url.split('://')[1].split('/')[0]}...")
            resp = session.post(url, data=q, headers=headers, timeout=timeout, verify=verify_ssl)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_err = e
            continue
    if last_err:
        raise last_err
    raise RuntimeError("Overpass request failed with unknown error")


def fetch_osm_features(
    bbox: BBox,
    overpass_urls: Optional[List[str]] = None,
    verify_ssl: bool = True,
    timeout: int = 90,
    progress_callback = None,
) -> Dict[str, List[Dict]]:
    """Fetch buildings, roads, and green polygons from OSM via Overpass.
    Returns a dict with keys: buildings, roads, greens; each a list of elements.
    Simplified to ways only (no relations) for speed.
    """
    buildings_q = "way[\"building\"]{{bbox}};out geom;"
    roads_q = "way[\"highway\"]{{bbox}};out geom;"
    greens_q = (
        "way[\"landuse\"=\"forest\"]{{bbox}};"
        "way[\"natural\"=\"wood\"]{{bbox}};"
        "way[\"leisure\"=\"park\"]{{bbox}};"
        "out geom;"
    )
    if progress_callback:
        progress_callback("Fetching buildings...")
    buildings = fetch_overpass(bbox, buildings_q, overpass_urls, verify_ssl, timeout, progress_callback).get("elements", [])
    if progress_callback:
        progress_callback(f"Fetching roads (found {len(buildings)} buildings)...")
    roads = fetch_overpass(bbox, roads_q, overpass_urls, verify_ssl, timeout, progress_callback).get("elements", [])
    if progress_callback:
        progress_callback(f"Fetching vegetation (found {len(roads)} roads)...")
    greens = fetch_overpass(bbox, greens_q, overpass_urls, verify_ssl, timeout, progress_callback).get("elements", [])
    return {"buildings": buildings, "roads": roads, "greens": greens}


def element_geometry_ll(elem: Dict) -> List[Tuple[float, float]]:
    """Extract lon/lat pairs from an Overpass element with geometry list."""
    geom = elem.get("geometry", [])
    return [(g.get("lon"), g.get("lat")) for g in geom if ("lon" in g and "lat" in g)]


def estimate_building_height(tags: Dict) -> float:
    """Estimate building height from OSM tags; default to 10m if unknown."""
    h = tags.get("height") or tags.get("building:height")
    if h:
        try:
            return float(str(h).replace("m", "").strip())
        except Exception:
            pass
    levels = tags.get("building:levels") or tags.get("levels")
    if levels:
        try:
            return float(levels) * 3.0
        except Exception:
            pass
    return 10.0


def estimate_road_width(tags: Dict) -> float:
    """Estimate road width from OSM tags; defaults vary by highway class."""
    hw = tags.get("highway", "road")
    default = {
        "motorway": 20.0,
        "trunk": 18.0,
        "primary": 14.0,
        "secondary": 12.0,
        "tertiary": 10.0,
        "residential": 8.0,
        "service": 6.0,
        "footway": 3.0,
        "path": 2.0,
        "cycleway": 3.0,
    }.get(hw, 8.0)
    width = tags.get("width")
    if width:
        try:
            return float(str(width).replace("m", "").strip())
        except Exception:
            pass
    return default


def sample_polygon_points(poly_ll: List[Tuple[float, float]], origin_ll: Tuple[float, float], xy_step: float) -> List[Tuple[float, float]]:
    """Return sample XY points inside polygon at a grid step, in local meters."""
    # Convert polygon to local XY
    poly_xy = [ll_to_local_xy(lon, lat, origin_ll[0], origin_ll[1]) for lon, lat in poly_ll]
    xs = [p[0] for p in poly_xy]
    ys = [p[1] for p in poly_xy]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    pts = []
    x = xmin
    while x <= xmax:
        y = ymin
        while y <= ymax:
            if point_in_polygon(x, y, poly_xy):
                pts.append((x, y))
            y += xy_step
        x += xy_step
    return pts


def sample_road_points(line_ll: List[Tuple[float, float]], origin_ll: Tuple[float, float], xy_step: float, width: float) -> List[Tuple[float, float]]:
    """Sample points along a polyline with a given width by offsetting perpendicular stripes."""
    # Convert line to local XY
    line_xy = [ll_to_local_xy(lon, lat, origin_ll[0], origin_ll[1]) for lon, lat in line_ll]
    pts: List[Tuple[float, float]] = []
    if len(line_xy) < 2:
        return pts
    half = max(width * 0.5, xy_step)
    offsets = np.arange(-half, half + 1e-6, xy_step)
    for (x0, y0), (x1, y1) in zip(line_xy[:-1], line_xy[1:]):
        dx, dy = x1 - x0, y1 - y0
        seg_len = math.hypot(dx, dy)
        if seg_len < 1e-6:
            continue
        ux, uy = dx / seg_len, dy / seg_len
        # Perpendicular unit
        px, py = -uy, ux
        # March along segment
        s = 0.0
        while s <= seg_len:
            cx, cy = x0 + ux * s, y0 + uy * s
            for o in offsets:
                pts.append((cx + px * o, cy + py * o))
            s += xy_step
    return pts


def generate_voxcity_points(
    bbox: BBox,
    voxel_size_m: float = 2.0,
    canopy_default_h: float = 12.0,
    overpass_urls: Optional[List[str]] = None,
    verify_ssl: bool = True,
    timeout: int = 90,
    progress_callback = None,
) -> np.ndarray:
    """Generate a synthetic point cloud representing buildings, roads, vegetation using OSM.
    - Buildings: filled volumes up to height from tags (levels->3m per level) or 10m default
    - Roads: surface ribbons at z in [0, 0.5m]
    - Vegetation: volumes up to canopy_default_h
    Terrain is approximated as z=0 plane by sparse points (optional).
    Returns xyz as float32 array.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    origin_ll = (min_lon, min_lat)
    osm = fetch_osm_features(bbox, overpass_urls=overpass_urls, verify_ssl=verify_ssl, timeout=timeout, progress_callback=progress_callback)

    points: List[Tuple[float, float, float]] = []

    # Buildings
    for elem in osm["buildings"]:
        tags = elem.get("tags", {})
        poly_ll = element_geometry_ll(elem)
        # Ensure closed polygon
        if len(poly_ll) < 3:
            continue
        if poly_ll[0] != poly_ll[-1]:
            poly_ll.append(poly_ll[0])
        height = estimate_building_height(tags)
        base_pts = sample_polygon_points(poly_ll, origin_ll, xy_step=voxel_size_m)
        if not base_pts:
            continue
        z_vals = np.arange(0.0, max(voxel_size_m, height) + 1e-6, voxel_size_m)
        for x, y in base_pts:
            for z in z_vals:
                points.append((x, y, z))

    # Roads
    for elem in osm["roads"]:
        tags = elem.get("tags", {})
        line_ll = element_geometry_ll(elem)
        if len(line_ll) < 2:
            continue
        width = estimate_road_width(tags)
        base_pts = sample_road_points(line_ll, origin_ll, xy_step=voxel_size_m, width=width)
        for x, y in base_pts:
            points.append((x, y, 0.0))
            if voxel_size_m >= 0.5:
                points.append((x, y, 0.5))

    # Vegetation greens
    for elem in osm["greens"]:
        poly_ll = element_geometry_ll(elem)
        if len(poly_ll) < 3:
            continue
        if poly_ll[0] != poly_ll[-1]:
            poly_ll.append(poly_ll[0])
        base_pts = sample_polygon_points(poly_ll, origin_ll, xy_step=voxel_size_m)
        if not base_pts:
            continue
        z_vals = np.arange(0.0, canopy_default_h + 1e-6, voxel_size_m)
        for x, y in base_pts:
            for z in z_vals:
                points.append((x, y, z))

    # Optional sparse terrain: corners and grid
    m_per_deg_lon, m_per_deg_lat = meters_per_degree((min_lat + max_lat) * 0.5)
    # Add a sparse ground lattice to help define bounds
    nx = int(((max_lon - min_lon) * m_per_deg_lon) / max(voxel_size_m, 10.0)) + 1
    ny = int(((max_lat - min_lat) * m_per_deg_lat) / max(voxel_size_m, 10.0)) + 1
    for ix in range(nx):
        for iy in range(ny):
            lon = min_lon + (ix / max(1, nx - 1)) * (max_lon - min_lon)
            lat = min_lat + (iy / max(1, ny - 1)) * (max_lat - min_lat)
            x, y = ll_to_local_xy(lon, lat, origin_ll[0], origin_ll[1])
            points.append((x, y, 0.0))

    if not points:
        return np.empty((0, 3), dtype=np.float32)
    xyz = np.asarray(points, dtype=np.float32)
    return xyz


def generate_voxcity_points_labeled(
    bbox: BBox,
    voxel_size_m: float = 2.0,
    canopy_default_h: float = 12.0,
    overpass_urls: Optional[List[str]] = None,
    verify_ssl: bool = True,
    timeout: int = 90,
    progress_callback = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Same as generate_voxcity_points, but also returns per-point labels:
    0=terrain/water, 1=building, 2=road, 3=vegetation
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    origin_ll = (min_lon, min_lat)
    osm = fetch_osm_features(bbox, overpass_urls=overpass_urls, verify_ssl=verify_ssl, timeout=timeout, progress_callback=progress_callback)

    if progress_callback:
        progress_callback("Processing buildings...")
    pts: List[Tuple[float, float, float]] = []
    labs: List[int] = []
    
    xy_step = voxel_size_m * 0.5  # Use finer sampling for denser representation

    # Buildings
    for elem in osm["buildings"]:
        tags = elem.get("tags", {})
        poly_ll = element_geometry_ll(elem)
        if len(poly_ll) < 3:
            continue
        if poly_ll[0] != poly_ll[-1]:
            poly_ll.append(poly_ll[0])
        height = estimate_building_height(tags)
        base_pts = sample_polygon_points(poly_ll, origin_ll, xy_step=xy_step)
        if not base_pts:
            continue
        z_vals = np.arange(0.0, max(voxel_size_m, height) + 1e-6, voxel_size_m)
        for x, y in base_pts:
            for z in z_vals:
                pts.append((x, y, z))
                labs.append(1)

    if progress_callback:
        progress_callback(f"Processing roads ({len(pts)} points so far)...")
    # Roads
    for elem in osm["roads"]:
        tags = elem.get("tags", {})
        line_ll = element_geometry_ll(elem)
        if len(line_ll) < 2:
            continue
        width = estimate_road_width(tags)
        base_pts = sample_road_points(line_ll, origin_ll, xy_step=xy_step, width=width)
        for x, y in base_pts:
            pts.append((x, y, 0.0))
            labs.append(2)
            if voxel_size_m >= 0.5:
                pts.append((x, y, 0.5))
                labs.append(2)

    if progress_callback:
        progress_callback(f"Processing vegetation ({len(pts)} points so far)...")
    # Vegetation greens
    for elem in osm["greens"]:
        poly_ll = element_geometry_ll(elem)
        if len(poly_ll) < 3:
            continue
        if poly_ll[0] != poly_ll[-1]:
            poly_ll.append(poly_ll[0])
        base_pts = sample_polygon_points(poly_ll, origin_ll, xy_step=xy_step)
        if not base_pts:
            continue
        z_vals = np.arange(0.0, canopy_default_h + 1e-6, voxel_size_m)
        for x, y in base_pts:
            for z in z_vals:
                pts.append((x, y, z))
                labs.append(3)

    if progress_callback:
        progress_callback(f"Building terrain lattice ({len(pts)} points total)...")
    # Sparse terrain lattice
    m_per_deg_lon, m_per_deg_lat = meters_per_degree((min_lat + max_lat) * 0.5)
    nx = int(((max_lon - min_lon) * m_per_deg_lon) / max(voxel_size_m, 10.0)) + 1
    ny = int(((max_lat - min_lat) * m_per_deg_lat) / max(voxel_size_m, 10.0)) + 1
    for ix in range(nx):
        for iy in range(ny):
            lon = min_lon + (ix / max(1, nx - 1)) * (max_lon - min_lon)
            lat = min_lat + (iy / max(1, ny - 1)) * (max_lat - min_lat)
            x, y = ll_to_local_xy(lon, lat, origin_ll[0], origin_ll[1])
            pts.append((x, y, 0.0))
            labs.append(0)

    if progress_callback:
        progress_callback(f"Voxelizing {len(pts)} points...")
    if not pts:
        return np.empty((0, 3), dtype=np.float32), np.empty((0,), dtype=np.uint8)
    xyz = np.asarray(pts, dtype=np.float32)
    labels = np.asarray(labs, dtype=np.uint8)
    return xyz, labels

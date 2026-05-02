"""Base map renderer.

Composes a stylized SVG of an uploaded trail using:
  - GPX trackpoints (read from the project directory)
  - NED elevation grid
  - NLCD 2021 land cover
  - OSM features (water, buildings, peaks, scrub)
  - NYS tax parcels (when bbox falls inside NY)

Ported from trail-maps/generate_illustrated.py. The original was a CLI script
producing full HTML; this module returns just the inner SVG so the frontend
can embed it in its own page.
"""

from __future__ import annotations

import math
from pathlib import Path

from app.config import settings
from app.core import geodata
from app.core.gpx import parse_gpx
from app.models.project import Project

# Render canvas (SVG viewBox dimensions)
W, H = 1100, 860
PAD = 72
ROT_DEFAULT = 0  # no rotation by default; user can override per project later
MARGIN_DEFAULT = 0.014  # extra lat/lon degrees beyond trail bbox per side
ELE_COLS, ELE_ROWS = 36, 28
NLCD_PX = 70
TREE_SCALE = 1.0
MAX_TREES = 700
MIN_TREE_DIST = 18

CAT_COLORS = {
    "forest": "rgba(55,120,45,0.52)",
    "shrub": "rgba(140,160,80,0.42)",
    "meadow": "rgba(200,220,100,0.38)",
    "pasture": "rgba(200,210,80,0.38)",
    "developed": "rgba(200,160,140,0.30)",
    "crops": "rgba(180,160,100,0.30)",
    "wetland": "rgba(120,180,200,0.38)",
    "water": "rgba(90,150,200,0.50)",
    "barren": "rgba(180,170,155,0.30)",
}


# ─── Coordinate transform ──────────────────────────────────────────────────
def make_transform(bb_geo: tuple[float, float, float, float], rot_deg: float):
    """Return (transform_fn, scale).

    bb_geo is (lat_min, lat_max, lon_min, lon_max). transform_fn maps a
    (lat, lon) point to (x_px, y_px) on a W×H canvas with PAD padding.
    """
    lat_min, lat_max, lon_min, lon_max = bb_geo
    lat_c = (lat_min + lat_max) / 2
    lon_c = (lon_min + lon_max) / 2
    cos_lat = math.cos(math.radians(lat_c))

    a = math.radians(rot_deg)
    ca, sa = math.cos(a), math.sin(a)

    def to_local_rotated(lat: float, lon: float) -> tuple[float, float]:
        x = (lon - lon_c) * cos_lat * 111320
        y = -(lat - lat_c) * 111320
        return x * ca - y * sa, x * sa + y * ca

    corners = [
        (lat_min, lon_min),
        (lat_min, lon_max),
        (lat_max, lon_min),
        (lat_max, lon_max),
    ]
    rots = [to_local_rotated(la, lo) for la, lo in corners]
    min_rx = min(r[0] for r in rots)
    max_rx = max(r[0] for r in rots)
    min_ry = min(r[1] for r in rots)
    max_ry = max(r[1] for r in rots)
    rx, ry = max_rx - min_rx, max_ry - min_ry
    scale = min((W - 2 * PAD) / rx, (H - 2 * PAD) / ry)
    off_x = (W - scale * rx) / 2 - scale * min_rx
    off_y = (H - scale * ry) / 2 - scale * min_ry

    def xform(lat: float, lon: float) -> tuple[float, float]:
        xr, yr = to_local_rotated(lat, lon)
        return xr * scale + off_x, yr * scale + off_y

    return xform, scale


# ─── Geometry helpers ───────────────────────────────────────────────────────
def _centroid(pts: list[tuple[float, float]]) -> tuple[float, float]:
    n = len(pts)
    return sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n


def _find_highest_peaks(
    ele_data: dict, bb_geo: tuple[float, float, float, float], xform, n: int = 2, min_dist_px: float = 110
) -> list[tuple[float, float, float]]:
    ecols, erows = ele_data["cols"], ele_data["rows"]
    eles = ele_data["elevations"]
    lat_min, lat_max, lon_min, lon_max = bb_geo

    candidates: list[tuple[float, float, float]] = []
    for r in range(erows):
        for c in range(ecols):
            e = eles[r * ecols + c]
            if not e or e <= 0:
                continue
            lat = lat_min + (lat_max - lat_min) * r / (erows - 1)
            lon = lon_min + (lon_max - lon_min) * c / (ecols - 1)
            x, y = xform(lat, lon)
            candidates.append((e, x, y))

    candidates.sort(key=lambda c: -c[0])
    peaks: list[tuple[float, float, float]] = []
    for e, x, y in candidates:
        if all((x - px) ** 2 + (y - py) ** 2 >= min_dist_px**2 for _, px, py in peaks):
            peaks.append((e, x, y))
        if len(peaks) >= n:
            break
    return peaks


# ─── SVG symbols ────────────────────────────────────────────────────────────
def _svg_pine(cx: float, cy: float, sz: float = 13) -> str:
    w = sz
    h = sz * 1.7
    tw = sz * 0.24
    return (
        f'<polygon points="{cx:.0f},{cy-h:.0f} {cx-w:.0f},{cy-sz*.2:.0f} {cx+w:.0f},{cy-sz*.2:.0f}" '
        f'fill="#2d6a28" stroke="#1a4018" stroke-width="0.7" opacity="0.92"/>'
        f'<polygon points="{cx:.0f},{cy-h*1.3:.0f} {cx-w*.7:.0f},{cy-h*.55:.0f} {cx+w*.7:.0f},{cy-h*.55:.0f}" '
        f'fill="#3a8030" stroke="#1a4018" stroke-width="0.6" opacity="0.92"/>'
        f'<rect x="{cx-tw:.0f}" y="{cy-sz*.2:.0f}" width="{tw*2:.0f}" height="{sz*.55:.0f}" fill="#7a5030"/>'
    )


def _svg_shrub(cx: float, cy: float, sz: float = 9) -> str:
    return (
        f'<ellipse cx="{cx:.0f}" cy="{cy-sz*.6:.0f}" rx="{sz:.0f}" ry="{sz*.7:.0f}" '
        f'fill="#5a8a40" stroke="#3a6020" stroke-width="0.8" opacity="0.8"/>'
    )


def _svg_house(cx: float, cy: float, w: float = 22, h: float = 16) -> str:
    rx = cx - w / 2
    ry = cy - h / 2
    tw = w * 0.22
    th = h * 0.42
    dx = cx - tw / 2
    dy = ry + h - th
    ww = w * 0.22
    wh = h * 0.28
    wx = rx + w * 0.64 - ww / 2
    wy = ry + h * 0.22
    return (
        f'<rect x="{rx:.0f}" y="{ry:.0f}" width="{w:.0f}" height="{h:.0f}" '
        f'fill="#ede0c8" stroke="#8b6040" stroke-width="1.4"/>'
        f'<polygon points="{rx-3:.0f},{ry:.0f} {cx:.0f},{cy-h*.9:.0f} {rx+w+3:.0f},{ry:.0f}" '
        f'fill="#b84030" stroke="#8b2020" stroke-width="1.1"/>'
        f'<rect x="{dx:.0f}" y="{dy:.0f}" width="{tw:.0f}" height="{th:.0f}" fill="#8b6040"/>'
        f'<rect x="{wx:.0f}" y="{wy:.0f}" width="{ww:.0f}" height="{wh:.0f}" '
        f'fill="#a8d4e8" stroke="#8b6040" stroke-width="0.7"/>'
    )


def _svg_peak_marker(cx: float, cy: float, elev_ft: float, sz: float = 44) -> str:
    h = sz * 1.72
    w = sz * 1.42
    sn = sz * 0.46
    bx, by = cx + sz * 0.28, cy + sz * 0.14
    bh, bw = h * 0.72, w * 0.72
    back = (
        f'<polygon points="{bx:.0f},{by-bh:.0f} {bx-bw:.0f},{by:.0f} {bx+bw:.0f},{by:.0f}" '
        f'fill="#7a8e9c" stroke="#5a6e7c" stroke-width="1"/>'
    )
    shad = (
        f'<polygon points="{cx+4:.0f},{cy-h+4:.0f} {cx-w+4:.0f},{cy+4:.0f} {cx+w+4:.0f},{cy+4:.0f}" '
        f'fill="rgba(40,50,60,0.25)" stroke="none"/>'
    )
    body = (
        f'<polygon points="{cx:.0f},{cy-h:.0f} {cx-w:.0f},{cy:.0f} {cx+w:.0f},{cy:.0f}" '
        f'fill="#a8bbc8" stroke="#6a7a88" stroke-width="1.8"/>'
    )
    lface = (
        f'<polygon points="{cx:.0f},{cy-h:.0f} {cx-w:.0f},{cy:.0f} {cx:.0f},{cy:.0f}" '
        f'fill="#8a9eac" stroke="none" opacity="0.6"/>'
    )
    snow = (
        f'<polygon points="{cx:.0f},{cy-h:.0f} {cx-sn:.0f},{cy-h+sn*1.65:.0f} {cx+sn:.0f},{cy-h+sn*1.65:.0f}" '
        f'fill="white" stroke="rgba(200,210,220,0.6)" stroke-width="0.8"/>'
    )
    snows = (
        f'<polygon points="{cx:.0f},{cy-h:.0f} {cx-sn:.0f},{cy-h+sn*1.65:.0f} {cx:.0f},{cy-h+sn*1.1:.0f}" '
        f'fill="rgba(180,195,210,0.5)" stroke="none"/>'
    )
    badge_y = cy + sz * 0.32
    badge_w = 64
    badge_h = 20
    badge = (
        f'<rect x="{cx-badge_w/2:.0f}" y="{badge_y:.0f}" width="{badge_w}" height="{badge_h}" '
        f'rx="5" fill="rgba(30,45,60,0.82)" stroke="rgba(160,190,210,0.6)" stroke-width="1"/>'
        f'<text x="{cx:.0f}" y="{badge_y+13.5:.0f}" text-anchor="middle" '
        f'font-size="11" fill="white" font-family="monospace" font-weight="bold">'
        f"{elev_ft:.0f} ft</text>"
    )
    return back + shad + body + lface + snow + snows + badge


def _svg_water_label(cx: float, cy: float, name: str) -> str:
    return (
        f'<text x="{cx:.0f}" y="{cy:.0f}" text-anchor="middle" '
        f'font-size="10" fill="#3060a0" font-style="italic" font-family="Georgia,serif">{name}</text>'
    )


def _compass_rose(cx: float, cy: float, sz: float = 30) -> str:
    out: list[str] = []
    for deg, lbl in [(0, "N"), (90, "E"), (180, "S"), (270, "W")]:
        a = math.radians(deg - 90)
        ca, sa = math.cos(a), math.sin(a)
        ox, oy = cx + ca * sz, cy + sa * sz
        ix, iy = cx + ca * sz * 0.32, cy + sa * sz * 0.32

        def pt(angle: float, r: float) -> tuple[float, float]:
            return cx + math.cos(angle) * sz * r, cy + math.sin(angle) * sz * r

        b1 = pt(a + math.radians(26), 0.35)
        b2 = pt(a - math.radians(26), 0.35)
        b3 = pt(a + math.radians(206), 0.35)
        b4 = pt(a + math.radians(154), 0.35)
        col = "#c0392b" if lbl == "N" else "#2c3e50"
        out.append(
            f'<polygon points="{ox:.0f},{oy:.0f} {b1[0]:.0f},{b1[1]:.0f} '
            f'{ix:.0f},{iy:.0f} {b2[0]:.0f},{b2[1]:.0f}" fill="{col}" stroke="white" stroke-width="0.5"/>'
        )
        out.append(
            f'<polygon points="{ox:.0f},{oy:.0f} {b3[0]:.0f},{b3[1]:.0f} '
            f'{ix:.0f},{iy:.0f} {b4[0]:.0f},{b4[1]:.0f}" fill="white" stroke="{col}" stroke-width="0.5"/>'
        )
        tx = cx + ca * (sz + 13)
        ty = cy + sa * (sz + 13)
        size = "12" if lbl == "N" else "9"
        out.append(
            f'<text x="{tx:.0f}" y="{ty:.0f}" text-anchor="middle" dominant-baseline="middle" '
            f'font-size="{size}" font-weight="bold" fill="{col}">{lbl}</text>'
        )
    out.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="3" fill="#2c3e50"/>')
    return "\n".join(out)


def _smooth_path(pts: list[tuple[float, float]], t: float = 0.25) -> str:
    if len(pts) < 2:
        return ""
    d = f"M{pts[0][0]:.0f},{pts[0][1]:.0f}"
    for i in range(len(pts) - 1):
        p0 = pts[max(0, i - 1)]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[min(len(pts) - 1, i + 2)]
        cx1 = p1[0] + (p2[0] - p0[0]) * t
        cy1 = p1[1] + (p2[1] - p0[1]) * t
        cx2 = p2[0] - (p3[0] - p1[0]) * t
        cy2 = p2[1] - (p3[1] - p1[1]) * t
        d += f" C{cx1:.0f},{cy1:.0f} {cx2:.0f},{cy2:.0f} {p2[0]:.0f},{p2[1]:.0f}"
    return d


def _ele_color(frac: float) -> tuple[int, int, int]:
    stops = [
        (0.0, (192, 224, 160)),
        (0.30, (212, 210, 150)),
        (0.58, (210, 188, 130)),
        (0.80, (188, 162, 122)),
        (1.0, (210, 198, 186)),
    ]
    for i in range(len(stops) - 1):
        f0, c0 = stops[i]
        f1, c1 = stops[i + 1]
        if f0 <= frac <= f1:
            tt = (frac - f0) / (f1 - f0)
            return (
                int(c0[0] + tt * (c1[0] - c0[0])),
                int(c0[1] + tt * (c1[1] - c0[1])),
                int(c0[2] + tt * (c1[2] - c0[2])),
            )
    return (210, 198, 186)


def _det_shuffle(lst: list, seed: int) -> list:
    """Deterministic shuffle so tree placement is stable across renders."""
    out = list(lst)
    s = seed
    for i in range(len(out) - 1, 0, -1):
        s = (s * 6364136223846793005 + 1) & 0xFFFFFFFFFFFFFFFF
        j = s % (i + 1)
        out[i], out[j] = out[j], out[i]
    return out


# ─── Public API ────────────────────────────────────────────────────────────
def render_base_map(project: Project) -> str:
    """Render the project's base SVG by fetching geodata and assembling the scene.

    Returns the full <svg>…</svg> as a string with viewBox 0 0 W H.
    """
    project_dir = settings.projects_dir / project.id
    gpx_path = next(project_dir.glob("source.*"), None)
    if gpx_path is None or gpx_path.suffix.lower() != ".gpx":
        # Fallback for non-GPX inputs (KML/GeoJSON not yet implemented)
        return _placeholder_svg(project)

    track = parse_gpx(gpx_path)
    gpx_pts = track.points

    lons = [p[1] for p in gpx_pts]
    lats = [p[0] for p in gpx_pts]
    bb_geo = (
        min(lats) - MARGIN_DEFAULT,
        max(lats) + MARGIN_DEFAULT,
        min(lons) - MARGIN_DEFAULT,
        max(lons) + MARGIN_DEFAULT,
    )
    api_bbox = (bb_geo[2], bb_geo[0], bb_geo[3], bb_geo[1])  # (lon_min, lat_min, lon_max, lat_max)

    xform, _ = make_transform(bb_geo, ROT_DEFAULT)

    ele_data = geodata.fetch_elevation_grid(api_bbox, ELE_COLS, ELE_ROWS)
    nlcd_data = geodata.fetch_nlcd(api_bbox, NLCD_PX)
    osm_data = geodata.fetch_osm(api_bbox)
    parcel_data = geodata.fetch_parcels(api_bbox)

    return _compose_svg(project, gpx_pts, ele_data, nlcd_data, osm_data, parcel_data, bb_geo, xform)


def _placeholder_svg(project: Project) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
        f'<rect width="{W}" height="{H}" fill="#f3eedd"/>'
        f'<text x="{W/2:.0f}" y="{H/2:.0f}" font-family="serif" font-size="22" '
        f'text-anchor="middle" fill="#3a2f22">{project.name}</text>'
        f'<text x="{W/2:.0f}" y="{H/2+30:.0f}" font-family="monospace" font-size="12" '
        f'text-anchor="middle" fill="#7a6e5a">non-GPX input — parser not yet implemented</text>'
        f"</svg>"
    )


def _compose_svg(
    project: Project,
    gpx_pts: list[tuple[float, float, float | None]],
    ele_data: dict,
    nlcd_data: dict,
    osm_data: dict,
    parcel_data: dict,
    bb_geo: tuple[float, float, float, float],
    xform,
) -> str:
    lat_min, lat_max, lon_min, lon_max = bb_geo

    # Elevation cells (blurred terrain)
    ecols, erows = ele_data["cols"], ele_data["rows"]
    eles = ele_data["elevations"]
    valid_eles = [e for e in eles if e and e > 0]
    min_e = min(valid_eles) if valid_eles else 0
    max_e = max(valid_eles) if valid_eles else 1
    ele_range = max_e - min_e if max_e > min_e else 1

    ele_cells: list[str] = []
    for r in range(erows - 1):
        for c in range(ecols - 1):
            idx = [r * ecols + c, r * ecols + c + 1, (r + 1) * ecols + c, (r + 1) * ecols + c + 1]
            avg_e = sum(eles[i] for i in idx if eles[i]) / 4
            frac = (avg_e - min_e) / ele_range
            rgb = _ele_color(frac)
            color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            la_lo = lat_min + (lat_max - lat_min) * r / (erows - 1)
            la_hi = lat_min + (lat_max - lat_min) * (r + 1) / (erows - 1)
            lo_lo = lon_min + (lon_max - lon_min) * c / (ecols - 1)
            lo_hi = lon_min + (lon_max - lon_min) * (c + 1) / (ecols - 1)
            corners = [(la_lo, lo_lo), (la_lo, lo_hi), (la_hi, lo_hi), (la_hi, lo_lo)]
            cxy = [xform(la, lo) for la, lo in corners]
            pts_str = " ".join(f"{x:.0f},{y:.0f}" for x, y in cxy)
            ele_cells.append(
                f'<polygon points="{pts_str}" fill="{color}" stroke="{color}" stroke-width="0.8"/>'
            )

    # NLCD cells
    ncols, nrows = nlcd_data["cols"], nlcd_data["rows"]
    nlcd_grid = nlcd_data["grid"]
    nlcd_cells: list[str] = []
    for r in range(nrows):
        for c in range(ncols):
            cat = nlcd_grid[r][c]
            if cat not in CAT_COLORS or cat == "unknown":
                continue
            color = CAT_COLORS[cat]
            la_lo = lat_min + (lat_max - lat_min) * r / max(1, nrows - 1)
            la_hi = lat_min + (lat_max - lat_min) * (r + 1) / max(1, nrows - 1) if r < nrows - 1 else lat_max
            lo_lo = lon_min + (lon_max - lon_min) * c / max(1, ncols - 1)
            lo_hi = lon_min + (lon_max - lon_min) * (c + 1) / max(1, ncols - 1) if c < ncols - 1 else lon_max
            corners = [(la_lo, lo_lo), (la_lo, lo_hi), (la_hi, lo_hi), (la_hi, lo_lo)]
            cxy = [xform(la, lo) for la, lo in corners]
            pts_str = " ".join(f"{x:.0f},{y:.0f}" for x, y in cxy)
            nlcd_cells.append(
                f'<polygon points="{pts_str}" fill="{color}" stroke="{color}" stroke-width="0.3"/>'
            )

    # Parcel rings
    parcel_svgs: list[str] = []
    for ring in parcel_data.get("rings", []):
        if len(ring) < 3:
            continue
        xy = [xform(coord[1], coord[0]) for coord in ring]
        pts_str = " ".join(f"{x:.0f},{y:.0f}" for x, y in xy)
        parcel_svgs.append(
            f'<polygon points="{pts_str}" fill="none" stroke="#7a5820" '
            f'stroke-dasharray="6,4" stroke-width="1.2" opacity="0.75"/>'
        )

    # Trees on forest/shrub NLCD pixels
    forest_centers: list[tuple[float, float]] = []
    shrub_centers: list[tuple[float, float]] = []
    for r in range(nrows):
        for c in range(ncols):
            cat = nlcd_grid[r][c]
            if cat not in ("forest", "shrub"):
                continue
            la = lat_min + (lat_max - lat_min) * (r + 0.5) / nrows
            lo = lon_min + (lon_max - lon_min) * (c + 0.5) / ncols
            x, y = xform(la, lo)
            (forest_centers if cat == "forest" else shrub_centers).append((x, y))

    forest_centers = _det_shuffle(forest_centers, seed=42)
    shrub_centers = _det_shuffle(shrub_centers, seed=99)

    placed: list[tuple[float, float]] = []

    def too_close(x: float, y: float) -> bool:
        return any((x - px) ** 2 + (y - py) ** 2 < MIN_TREE_DIST**2 for px, py in placed)

    tree_svgs: list[str] = []
    seed = 42
    for x, y in forest_centers:
        if len(placed) >= MAX_TREES:
            break
        seed = (seed * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        jx = ((seed >> 16) & 0xFF) / 255 * 10 - 5
        jy = ((seed >> 8) & 0xFF) / 255 * 10 - 5
        tx, ty = x + jx, y + jy
        if not too_close(tx, ty):
            sz = max(2.5, (10 + ((seed >> 24) & 3)) * TREE_SCALE)
            tree_svgs.append(_svg_pine(tx, ty, sz))
            placed.append((tx, ty))

    for x, y in shrub_centers:
        if len(placed) >= MAX_TREES:
            break
        seed = (seed * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        jx = ((seed >> 16) & 0xFF) / 255 * 8 - 4
        jy = ((seed >> 8) & 0xFF) / 255 * 8 - 4
        tx, ty = x + jx, y + jy
        if not too_close(tx, ty):
            tree_svgs.append(_svg_shrub(tx, ty, max(2.0, 8 * TREE_SCALE)))
            placed.append((tx, ty))

    # OSM features
    water_svgs: list[str] = []
    water_labels: list[str] = []
    building_svgs: list[str] = []
    peak_svgs: list[str] = []

    for elem in osm_data.get("elements", []):
        tags = elem.get("tags", {})
        etype = elem.get("type")

        if etype == "node" and tags.get("natural") == "peak":
            x, y = xform(elem["lat"], elem["lon"])
            ele = tags.get("ele", "")
            try:
                ele_ft = float(ele) * 3.28084 if ele else max_e * 3.28084
            except ValueError:
                ele_ft = max_e * 3.28084
            peak_svgs.append(_svg_peak_marker(x, y - 10, ele_ft))

        elif etype == "way":
            geom = elem.get("geometry", [])
            if not geom:
                continue
            xy_pts = [xform(g["lat"], g["lon"]) for g in geom]
            pts_str = " ".join(f"{x:.0f},{y:.0f}" for x, y in xy_pts)

            if tags.get("natural") == "water":
                water_svgs.append(
                    f'<polygon points="{pts_str}" fill="#7ab8d8" stroke="#4880a8" '
                    f'stroke-width="1.5" opacity="0.85"/>'
                )
                name = tags.get("name", "")
                if name:
                    cx, cy = _centroid(xy_pts)
                    water_labels.append(_svg_water_label(cx, cy, name))
            elif "waterway" in tags:
                wtype = tags.get("waterway", "")
                width = "2.5" if wtype == "stream" else "4"
                water_svgs.append(
                    f'<polyline points="{pts_str}" fill="none" stroke="#5890c0" '
                    f'stroke-width="{width}" stroke-linecap="round" opacity="0.8"/>'
                )
            elif "building" in tags:
                cx, cy = _centroid(xy_pts)
                xs = [p[0] for p in xy_pts]
                ys = [p[1] for p in xy_pts]
                bw = min(36, max(18, (max(xs) - min(xs)) * 1.1))
                bh = min(28, max(14, (max(ys) - min(ys)) * 1.1))
                building_svgs.append(_svg_house(cx, cy, bw, bh))

    for e_m, px, py in _find_highest_peaks(ele_data, bb_geo, xform):
        peak_svgs.append(_svg_peak_marker(px, py - 10, e_m * 3.28084))

    # Trail
    trail_xy = [xform(p[0], p[1]) for p in gpx_pts[::4]]
    if gpx_pts:
        trail_xy.append(xform(gpx_pts[-1][0], gpx_pts[-1][1]))
    trail_path = _smooth_path(trail_xy)
    sx, sy = trail_xy[0] if trail_xy else (W / 2, H / 2)
    ex, ey = trail_xy[-1] if trail_xy else (W / 2, H / 2)

    # Stats / overlays
    lo_ft = min_e * 3.28084
    hi_ft = max_e * 3.28084
    gain_ft = hi_ft - lo_ft

    grad_x, grad_y, grad_w, grad_h = W - 185, 14, 165, 12
    grad_cells = "".join(
        f'<rect x="{grad_x + i * grad_w // 20}" y="{grad_y}" width="{grad_w // 20 + 1}" height="{grad_h}" '
        f'fill="#{_ele_color(i / 19)[0]:02x}{_ele_color(i / 19)[1]:02x}{_ele_color(i / 19)[2]:02x}"/>'
        for i in range(20)
    )
    comp = _compass_rose(W - 75, H - 78)

    NL = "\n"
    ele_cells_s = NL.join(ele_cells)
    nlcd_cells_s = NL.join(nlcd_cells)
    parcel_svgs_s = NL.join(parcel_svgs)
    water_svgs_s = NL.join(water_svgs)
    water_labels_s = NL.join(water_labels)
    tree_svgs_s = NL.join(tree_svgs)
    building_svgs_s = NL.join(building_svgs)
    peak_svgs_s = NL.join(peak_svgs)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>
  <filter id="blur-ele" x="-8%" y="-8%" width="116%" height="116%">
    <feGaussianBlur stdDeviation="14"/>
  </filter>
  <filter id="lc-tex" x="-2%" y="-2%" width="104%" height="104%">
    <feTurbulence type="fractalNoise" baseFrequency="0.7" numOctaves="2" seed="7" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="1.8"/>
  </filter>
  <filter id="shadow">
    <feDropShadow dx="1" dy="2" stdDeviation="2.5" flood-opacity="0.45"/>
  </filter>
  <clipPath id="mapclip"><rect x="0" y="0" width="{W}" height="{H}"/></clipPath>
</defs>

<g filter="url(#blur-ele)" clip-path="url(#mapclip)">
{ele_cells_s}
</g>

<g filter="url(#lc-tex)" clip-path="url(#mapclip)">
{nlcd_cells_s}
</g>

<g clip-path="url(#mapclip)">
{parcel_svgs_s}
</g>

{water_svgs_s}
{water_labels_s}

{tree_svgs_s}

{building_svgs_s}

{peak_svgs_s}

<path d="{trail_path}" fill="none" stroke="white" stroke-width="9" stroke-linecap="round" opacity="0.35"/>
<path d="{trail_path}" fill="none" stroke="#e05010" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" filter="url(#shadow)"/>
<path d="{trail_path}" fill="none" stroke="#ff8840" stroke-width="1.8" stroke-dasharray="1,14" stroke-linecap="round" opacity="0.8"/>

<circle cx="{sx:.0f}" cy="{sy:.0f}" r="12" fill="#27ae60" stroke="white" stroke-width="2.8" filter="url(#shadow)"/>
<text x="{sx:.0f}" y="{sy+4:.0f}" text-anchor="middle" font-size="12" fill="white" font-weight="bold">S</text>
<text x="{sx:.0f}" y="{sy+26:.0f}" text-anchor="middle" font-size="10" fill="#1a4020" font-weight="bold" stroke="white" stroke-width="3" paint-order="stroke">Start</text>

<circle cx="{ex:.0f}" cy="{ey:.0f}" r="12" fill="#e74c3c" stroke="white" stroke-width="2.8" filter="url(#shadow)"/>
<text x="{ex:.0f}" y="{ey+4:.0f}" text-anchor="middle" font-size="14" fill="white">×</text>
<text x="{ex:.0f}" y="{ey+26:.0f}" text-anchor="middle" font-size="10" fill="#4a0a08" font-weight="bold" stroke="white" stroke-width="3" paint-order="stroke">End</text>

<rect x="0" y="0" width="{W}" height="36" fill="rgba(40,25,10,0.72)"/>
<text x="{W/2:.0f}" y="22" text-anchor="middle" font-size="16" fill="white"
  font-family="Georgia,serif" letter-spacing="2" font-weight="bold">{project.name}</text>

<rect x="{grad_x-8}" y="{grad_y-2}" width="{grad_w+16}" height="44" rx="5"
  fill="rgba(255,255,255,0.82)" stroke="#ccc" stroke-width="1"/>
{grad_cells}
<text x="{grad_x}" y="{grad_y+25}" font-size="9" fill="#555" font-family="monospace">{lo_ft:.0f} ft</text>
<text x="{grad_x+grad_w}" y="{grad_y+25}" font-size="9" fill="#555" font-family="monospace" text-anchor="end">{hi_ft:.0f} ft</text>
<text x="{grad_x+grad_w//2}" y="{grad_y+38}" font-size="9" fill="#666" font-family="monospace" text-anchor="middle">▲ {gain_ft:.0f} ft gain</text>

{comp}

<rect x="2" y="2" width="{W-4}" height="{H-4}" fill="none" stroke="#7a5030" stroke-width="2.5" rx="5"/>
</svg>"""


# Suppress unused-import warning when type-checking; Path is used implicitly via settings.
_ = Path

"""Geodata fetchers for the base map renderer.

Each fetcher hits a free public API, caches the raw response under
settings.cache_dir keyed by bbox+resolution, and returns parsed Python
data structures the renderer can consume.

Sources:
- Elevation: OpenTopoData NED 10m
- Land cover: NLCD 2021 via MRLC GeoServer WMS
- OSM features: Overpass API
- Parcels: NYS Tax Parcels FeatureServer (only useful inside NY State)

Ported from trail-maps/generate_illustrated.py.
"""

from __future__ import annotations

import math
import struct
import time
import zlib
from typing import Any

import requests

from app.core import cache

UA = {"User-Agent": "TrailCartographer/0.1"}

# NLCD 2021 RGB → category lookup
NLCD_CLASSES: dict[int, tuple[str, tuple[int, int, int]]] = {
    11: ("water", (70, 107, 159)),
    21: ("developed", (222, 197, 197)),
    22: ("developed", (217, 146, 130)),
    23: ("developed", (235, 0, 0)),
    24: ("developed", (171, 0, 0)),
    31: ("barren", (179, 172, 159)),
    41: ("forest", (104, 171, 95)),
    42: ("forest", (28, 99, 48)),
    43: ("forest", (181, 197, 143)),
    52: ("shrub", (204, 186, 136)),
    71: ("meadow", (223, 223, 194)),
    81: ("pasture", (220, 217, 57)),
    82: ("crops", (171, 113, 104)),
    90: ("wetland", (184, 217, 235)),
    95: ("wetland", (108, 159, 184)),
}


def nlcd_class_from_rgb(r: int, g: int, b: int) -> str:
    best, best_d = "unknown", 1e9
    for _, (cat, col) in NLCD_CLASSES.items():
        d = (r - col[0]) ** 2 + (g - col[1]) ** 2 + (b - col[2]) ** 2
        if d < best_d:
            best, best_d = cat, d
    return best if best_d < 6000 else "unknown"


# ─── PNG decoder (paletted + RGB, stdlib only) ─────────────────────────────
def decode_png(data: bytes) -> tuple[int, int, list[list[tuple[int, int, int]]]]:
    """Decode a PNG byte string → (width, height, rows of (r,g,b) tuples)."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a PNG")

    pos = 8
    width = height = 0
    palette: list[tuple[int, int, int]] = []
    idat = b""
    color_type = 0

    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        ctype = data[pos + 4 : pos + 8]
        cdata = data[pos + 8 : pos + 8 + length]
        pos += 12 + length

        if ctype == b"IHDR":
            width, height = struct.unpack(">II", cdata[:8])
            color_type = cdata[9]
        elif ctype == b"PLTE":
            palette = [(cdata[i], cdata[i + 1], cdata[i + 2]) for i in range(0, len(cdata), 3)]
        elif ctype == b"IDAT":
            idat += cdata
        elif ctype == b"IEND":
            break

    raw = bytearray(zlib.decompress(idat))
    bpp = 1 if color_type == 3 else (3 if color_type == 2 else (4 if color_type == 6 else 1))
    stride = width * bpp + 1

    def paeth(a: int, b: int, c: int) -> int:
        p = a + b - c
        pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
        return a if pa <= pb and pa <= pc else (b if pb <= pc else c)

    prev_row = bytearray(width * bpp)
    rows_rgb: list[list[tuple[int, int, int]]] = []

    for row in range(height):
        filt = raw[row * stride]
        cur = bytearray(raw[row * stride + 1 : row * stride + 1 + width * bpp])

        if filt == 1:
            for i in range(bpp, len(cur)):
                cur[i] = (cur[i] + cur[i - bpp]) & 0xFF
        elif filt == 2:
            for i in range(len(cur)):
                cur[i] = (cur[i] + prev_row[i]) & 0xFF
        elif filt == 3:
            for i in range(len(cur)):
                a = cur[i - bpp] if i >= bpp else 0
                cur[i] = (cur[i] + (a + prev_row[i]) // 2) & 0xFF
        elif filt == 4:
            for i in range(len(cur)):
                a = cur[i - bpp] if i >= bpp else 0
                b_ = prev_row[i]
                c = prev_row[i - bpp] if i >= bpp else 0
                cur[i] = (cur[i] + paeth(a, b_, c)) & 0xFF

        row_rgb: list[tuple[int, int, int]] = []
        if color_type == 3:
            for v in cur:
                row_rgb.append(palette[v] if v < len(palette) else (0, 0, 0))
        elif color_type == 2:
            for i in range(0, len(cur), 3):
                row_rgb.append((cur[i], cur[i + 1], cur[i + 2]))
        elif color_type == 6:
            for i in range(0, len(cur), 4):
                row_rgb.append((cur[i], cur[i + 1], cur[i + 2]))
        else:
            for v in cur:
                row_rgb.append((v, v, v))

        rows_rgb.append(row_rgb)
        prev_row = cur

    return width, height, rows_rgb


# ─── Elevation grid ─────────────────────────────────────────────────────────
def fetch_elevation_grid(
    bbox: tuple[float, float, float, float], cols: int = 36, rows: int = 28
) -> dict[str, Any]:
    """Returns {'pts', 'elevations', 'cols', 'rows'}.

    bbox is (lon_min, lat_min, lon_max, lat_max).
    """
    key = cache.cache_key("elev", bbox, cols, rows)
    cached = cache.get(key)
    if cached is not None:
        return cached

    lon_min, lat_min, lon_max, lat_max = bbox
    pts = [
        [lat_min + (lat_max - lat_min) * r / (rows - 1), lon_min + (lon_max - lon_min) * c / (cols - 1)]
        for r in range(rows)
        for c in range(cols)
    ]

    elevations: list[float] = []
    for i in range(0, len(pts), 100):
        batch = pts[i : i + 100]
        locs = "|".join(f"{p[0]:.6f},{p[1]:.6f}" for p in batch)
        url = f"https://api.opentopodata.org/v1/ned10m?locations={locs}"
        r = requests.get(url, headers=UA, timeout=30)
        r.raise_for_status()
        for res in r.json()["results"]:
            elevations.append(res["elevation"] if res["elevation"] is not None else 0)
        if i + 100 < len(pts):
            time.sleep(1.1)  # OpenTopoData public rate limit

    result = {"pts": pts, "elevations": elevations, "cols": cols, "rows": rows}
    cache.put(key, result)
    return result


# ─── NLCD land cover ────────────────────────────────────────────────────────
def fetch_nlcd(bbox: tuple[float, float, float, float], px_w: int = 70) -> dict[str, Any]:
    """Returns {'cols', 'rows', 'grid' (rows × cols of category strings), 'bbox'}."""
    key = cache.cache_key("nlcd", bbox, px_w)
    cached = cache.get(key)
    if cached is not None:
        return cached

    lon_min, lat_min, lon_max, lat_max = bbox
    aspect = (lon_max - lon_min) / (lat_max - lat_min) * math.cos(
        math.radians((lat_min + lat_max) / 2)
    )
    px_h = max(1, int(px_w / aspect))

    url = (
        "https://www.mrlc.gov/geoserver/mrlc_display/NLCD_2021_Land_Cover_L48/ows"
        "?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1"
        "&LAYERS=NLCD_2021_Land_Cover_L48&STYLES="
        "&FORMAT=image/png&TRANSPARENT=false"
        f"&WIDTH={px_w}&HEIGHT={px_h}"
        "&SRS=EPSG:4326"
        f"&BBOX={lon_min:.6f},{lat_min:.6f},{lon_max:.6f},{lat_max:.6f}"
    )
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    w, h, pixels = decode_png(r.content)

    grid = [[nlcd_class_from_rgb(*pixel) for pixel in row] for row in pixels]
    result = {"cols": w, "rows": h, "grid": grid, "bbox": list(bbox)}
    cache.put(key, result)
    return result


# ─── OSM features ──────────────────────────────────────────────────────────
def fetch_osm(bbox: tuple[float, float, float, float]) -> dict[str, Any]:
    """Returns the raw Overpass JSON response (with 'elements')."""
    key = cache.cache_key("osm", bbox)
    cached = cache.get(key)
    if cached is not None:
        return cached

    lon_min, lat_min, lon_max, lat_max = bbox
    bs = f"{lat_min:.6f},{lon_min:.6f},{lat_max:.6f},{lon_max:.6f}"
    q = (
        f"[out:json][timeout:30];"
        f"(way[natural=wood]({bs});way[landuse=forest]({bs});"
        f"way[natural=grassland]({bs});way[landuse=meadow]({bs});"
        f"way[landuse=grass]({bs});way[building]({bs});"
        f"node[natural=peak]({bs});way[natural=water]({bs});"
        f"way[waterway]({bs});way[natural=scrub]({bs});"
        f"relation[natural=wood]({bs}););out geom;"
    )

    last_err: Exception | None = None
    for attempt in range(4):
        try:
            r = requests.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": q},
                headers=UA,
                timeout=90,
            )
            r.raise_for_status()
            result = r.json()
            cache.put(key, result)
            return result
        except Exception as e:
            last_err = e
            time.sleep(8 * (attempt + 1))
    raise RuntimeError(f"Overpass API failed after 4 attempts: {last_err}")


# ─── NYS Tax Parcels (graceful failure outside NY) ─────────────────────────
def fetch_parcels(bbox: tuple[float, float, float, float]) -> dict[str, Any]:
    """Returns {'rings': [[(lon, lat), ...], ...]}.

    Empty rings list if outside NY State or the service is unreachable.
    """
    key = cache.cache_key("parcels", bbox)
    cached = cache.get(key)
    if cached is not None:
        return cached

    lon_min, lat_min, lon_max, lat_max = bbox
    params = {
        "geometry": f"{lon_min:.6f},{lat_min:.6f},{lon_max:.6f},{lat_max:.6f}",
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "inSR": "4326",
        "outSR": "4326",
        "outFields": "OBJECTID",
        "returnGeometry": "true",
        "f": "geojson",
    }
    url = (
        "https://gisservices.its.ny.gov/arcgis/rest/services/NYS_Tax_Parcels_Public/"
        "FeatureServer/1/query"
    )
    try:
        r = requests.get(url, params=params, headers=UA, timeout=30)
        r.raise_for_status()
        resp = r.json()
        rings: list[list[list[float]]] = []
        for feat in resp.get("features", []):
            geom = feat.get("geometry", {})
            gtype = geom.get("type", "")
            if gtype == "Polygon":
                rings.extend(geom.get("coordinates", []))
            elif gtype == "MultiPolygon":
                for poly in geom.get("coordinates", []):
                    rings.extend(poly)
        result: dict[str, Any] = {"rings": rings}
    except Exception:
        result = {"rings": []}

    cache.put(key, result)
    return result

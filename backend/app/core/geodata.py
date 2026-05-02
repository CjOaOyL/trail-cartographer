"""Fetchers for elevation, land cover (NLCD), OSM features, and parcels.

Stubs to be filled in by porting from trail-maps/generate_illustrated.py +
trail-maps/generate_inset.py. Each fetcher should:
  - Take a bbox (or list of points)
  - Hit a free public API (OpenTopoData, NLCD WMS, OSM Overpass, NYS parcel WFS)
  - Cache the raw response under settings.cache_dir keyed by bbox+resolution
  - Return parsed Python data structures
"""

from typing import Any


def fetch_elevation_grid(bbox: tuple[float, float, float, float], cols: int, rows: int) -> list[list[float]]:
    raise NotImplementedError


def fetch_nlcd(bbox: tuple[float, float, float, float], px: int) -> list[list[int]]:
    raise NotImplementedError


def fetch_osm_features(bbox: tuple[float, float, float, float]) -> dict[str, Any]:
    raise NotImplementedError


def fetch_parcels(bbox: tuple[float, float, float, float]) -> list[list[tuple[float, float]]]:
    raise NotImplementedError

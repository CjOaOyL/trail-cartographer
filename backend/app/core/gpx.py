from dataclasses import dataclass
from pathlib import Path

import gpxpy


@dataclass
class ParsedTrack:
    points: list[tuple[float, float, float | None]]
    bbox: tuple[float, float, float, float]
    elevation_profile: list[float]


def parse_gpx(path: Path) -> ParsedTrack:
    with path.open(encoding="utf-8") as f:
        gpx = gpxpy.parse(f)

    points: list[tuple[float, float, float | None]] = []
    for track in gpx.tracks:
        for segment in track.segments:
            for p in segment.points:
                points.append((p.latitude, p.longitude, p.elevation))

    if not points:
        raise ValueError("GPX contains no track points")

    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    bbox = (min(lons), min(lats), max(lons), max(lats))
    elevations = [p[2] for p in points if p[2] is not None]
    return ParsedTrack(points=points, bbox=bbox, elevation_profile=elevations)

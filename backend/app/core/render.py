from app.models.project import Project


def render_base_map(project: Project) -> str:
    """Render a base SVG map for a project.

    TODO: port the full renderer from the existing trail-maps/generate_illustrated.py.
    For now, emit a placeholder SVG so the frontend pipeline works end-to-end.
    """
    minx, miny, maxx, maxy = project.bbox
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 700" width="1000" height="700">
  <rect width="1000" height="700" fill="#f3eedd"/>
  <text x="500" y="340" font-family="serif" font-size="22" text-anchor="middle" fill="#3a2f22">
    {project.name}
  </text>
  <text x="500" y="370" font-family="monospace" font-size="12" text-anchor="middle" fill="#7a6e5a">
    bbox: {minx:.4f}, {miny:.4f} → {maxx:.4f}, {maxy:.4f}
  </text>
  <text x="500" y="400" font-family="monospace" font-size="12" text-anchor="middle" fill="#7a6e5a">
    base render placeholder — full pipeline ported in next iteration
  </text>
</svg>
"""

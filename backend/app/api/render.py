import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.api.projects import _manifest_path, _project_dir
from app.core.render import render_base_map
from app.models.project import Project

router = APIRouter()


@router.post("/{project_id}", response_model=Project)
def render_project(project_id: str) -> Project:
    m = _manifest_path(project_id)
    if not m.exists():
        raise HTTPException(404, "Project not found")
    project = Project(**json.loads(m.read_text()))

    svg, geo_bbox = render_base_map(project)
    svg_path = _project_dir(project_id) / "base.svg"
    svg_path.write_text(svg, encoding="utf-8")

    project.geo_bbox = geo_bbox
    m.write_text(project.model_dump_json(indent=2))
    return project


@router.get("/{project_id}/svg")
def get_svg(project_id: str) -> Response:
    svg_path = _project_dir(project_id) / "base.svg"
    if not svg_path.exists():
        raise HTTPException(404, "Base map not yet rendered")
    return Response(content=svg_path.read_bytes(), media_type="image/svg+xml")

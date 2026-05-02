import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.core.gpx import parse_gpx
from app.models.project import Project, ProjectSummary

router = APIRouter()


def _project_dir(project_id: str) -> Path:
    return settings.projects_dir / project_id


def _manifest_path(project_id: str) -> Path:
    return _project_dir(project_id) / "manifest.json"


@router.post("", response_model=Project)
async def create_project(file: UploadFile = File(...)) -> Project:
    if not file.filename or not file.filename.lower().endswith((".gpx", ".kml", ".geojson")):
        raise HTTPException(400, "Upload must be .gpx, .kml, or .geojson")

    project_id = uuid.uuid4().hex[:12]
    pdir = _project_dir(project_id)
    pdir.mkdir(parents=True, exist_ok=True)

    raw_path = pdir / f"source{Path(file.filename).suffix.lower()}"
    raw_path.write_bytes(await file.read())

    if raw_path.suffix == ".gpx":
        track = parse_gpx(raw_path)
    else:
        raise HTTPException(501, f"Parser for {raw_path.suffix} not implemented yet")

    project = Project(
        id=project_id,
        name=file.filename,
        source_file=raw_path.name,
        bbox=track.bbox,
        elevation_profile=track.elevation_profile,
        symbols=[],
    )
    _manifest_path(project_id).write_text(project.model_dump_json(indent=2))
    return project


@router.get("", response_model=list[ProjectSummary])
def list_projects() -> list[ProjectSummary]:
    out: list[ProjectSummary] = []
    for pdir in sorted(settings.projects_dir.iterdir()):
        m = pdir / "manifest.json"
        if m.exists():
            data = json.loads(m.read_text())
            out.append(ProjectSummary(id=data["id"], name=data["name"]))
    return out


@router.get("/{project_id}", response_model=Project)
def get_project(project_id: str) -> Project:
    m = _manifest_path(project_id)
    if not m.exists():
        raise HTTPException(404, "Project not found")
    return Project(**json.loads(m.read_text()))


@router.put("/{project_id}", response_model=Project)
def save_project(project_id: str, project: Project) -> Project:
    if project.id != project_id:
        raise HTTPException(400, "Project id mismatch")
    _manifest_path(project_id).write_text(project.model_dump_json(indent=2))
    return project


@router.delete("/{project_id}")
def delete_project(project_id: str) -> dict[str, str]:
    pdir = _project_dir(project_id)
    if not pdir.exists():
        raise HTTPException(404, "Project not found")
    for child in pdir.rglob("*"):
        if child.is_file():
            child.unlink()
    for child in sorted(pdir.rglob("*"), reverse=True):
        if child.is_dir():
            child.rmdir()
    pdir.rmdir()
    return {"status": "deleted"}

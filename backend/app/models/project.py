from typing import Any, Literal

from pydantic import BaseModel, Field


class Symbol(BaseModel):
    id: str
    name: str
    svg: str
    generated: bool = False


class PlacedSymbol(BaseModel):
    instance_id: str
    symbol_id: str
    x: float
    y: float
    rotation: float = 0.0
    scale: float = 1.0
    label: str | None = None


class ProjectSummary(BaseModel):
    id: str
    name: str


class Project(BaseModel):
    id: str
    name: str
    source_file: str
    bbox: tuple[float, float, float, float]
    elevation_profile: list[float] = Field(default_factory=list)
    symbols: list[PlacedSymbol] = Field(default_factory=list)
    custom_symbols: list[Symbol] = Field(default_factory=list)


class SymbolGenRequest(BaseModel):
    description: str
    name: str | None = None


class EditOp(BaseModel):
    op: Literal["move", "remove", "replace", "add", "recolor"]
    symbol_id: str | None = None
    instance_id: str | None = None
    dx: float | None = None
    dy: float | None = None
    x: float | None = None
    y: float | None = None
    svg: str | None = None
    new_symbol_svg: str | None = None
    fill: str | None = None
    stroke: str | None = None
    name: str | None = None


class MarkupRequest(BaseModel):
    project_id: str
    description: str
    polygon: list[tuple[float, float]]
    symbols_in_region: list[dict[str, Any]] = Field(default_factory=list)


class MarkupResponse(BaseModel):
    ops: list[EditOp]

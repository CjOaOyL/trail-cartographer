const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface Project {
  id: string;
  name: string;
  source_file: string;
  bbox: [number, number, number, number];
  geo_bbox?: [number, number, number, number] | null;
  elevation_profile: number[];
  symbols: PlacedSymbol[];
  custom_symbols: Symbol[];
}

export interface Symbol {
  id: string;
  name: string;
  svg: string;
  generated?: boolean;
}

export interface PlacedSymbol {
  instance_id: string;
  symbol_id: string;
  x: number;
  y: number;
  rotation?: number;
  scale?: number;
  label?: string | null;
}

export async function fetchHealth(): Promise<{ status: string }> {
  const r = await fetch(`${BASE}/api/health`);
  if (!r.ok) throw new Error("backend offline");
  return r.json();
}

export async function uploadGpx(file: File): Promise<Project> {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${BASE}/api/projects`, { method: "POST", body: fd });
  if (!r.ok) throw new Error(`upload failed: ${r.status}`);
  return r.json();
}

export async function renderProject(projectId: string): Promise<Project> {
  const r = await fetch(`${BASE}/api/render/${projectId}`, { method: "POST" });
  if (!r.ok) throw new Error(`render failed: ${r.status}`);
  return r.json();
}

export function svgUrl(projectId: string): string {
  return `${BASE}/api/render/${projectId}/svg`;
}

export async function listBuiltinSymbols(): Promise<Symbol[]> {
  const r = await fetch(`${BASE}/api/symbols/builtin`);
  if (!r.ok) throw new Error("symbol list failed");
  return r.json();
}

export async function generateSymbol(description: string, name?: string): Promise<Symbol> {
  const r = await fetch(`${BASE}/api/symbols/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description, name }),
  });
  if (!r.ok) throw new Error(`symbol gen failed: ${r.status}`);
  return r.json();
}

export async function saveProject(project: Project): Promise<Project> {
  const r = await fetch(`${BASE}/api/projects/${project.id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(project),
  });
  if (!r.ok) throw new Error(`save failed: ${r.status}`);
  return r.json();
}

export interface EditOp {
  op: "move" | "remove" | "replace" | "add" | "recolor";
  symbol_id?: string | null;
  instance_id?: string | null;
  dx?: number | null;
  dy?: number | null;
  x?: number | null;
  y?: number | null;
  svg?: string | null;
  new_symbol_svg?: string | null;
  fill?: string | null;
  stroke?: string | null;
  name?: string | null;
}

export interface MarkupRequest {
  project_id: string;
  description: string;
  polygon: [number, number][];
  symbols_in_region: { instance_id: string; symbol_id: string; x: number; y: number }[];
}

export async function interpretMarkup(req: MarkupRequest): Promise<{ ops: EditOp[] }> {
  const r = await fetch(`${BASE}/api/markup/interpret`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!r.ok) throw new Error(`markup interpret failed: ${r.status}`);
  return r.json();
}

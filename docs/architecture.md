# Architecture

## Overview

Trail Cartographer is a two-tier app:

- **Backend** (`backend/`) — Python FastAPI service. Owns GPX parsing, geodata fetching, base SVG rendering, and Claude integrations.
- **Frontend** (`frontend/`) — Vite + React + TypeScript SPA. Owns the editor canvas, drag-and-drop, drawing layer, and AI chat panel.

The two communicate over JSON+REST. The frontend never talks to Anthropic directly — all Claude calls are server-side so the API key stays on the backend.

## Project lifecycle

1. **Upload** — user POSTs a `.gpx` to `/api/projects`. Backend parses it (`core/gpx.py`), saves the raw file under `data/projects/<id>/`, writes a `manifest.json`, and returns the `Project` model.
2. **Render** — frontend hits `/api/render/<id>`. Backend fetches/caches geodata for the project bbox (`core/geodata.py` → `cache/`) and writes `base.svg`. The current scaffold returns a placeholder; full port from `trail-maps/generate_illustrated.py` is pending.
3. **Edit** — frontend loads the SVG into `<MapCanvas>`. Symbols from the palette can be placed, dragged, deleted. Edits live in Zustand state (`store/editor.ts`); persistence on Save → `PUT /api/projects/<id>`.
4. **AI symbol** — user describes a symbol → `POST /api/symbols/generate` → Claude returns inline `<g>` markup → added to palette as a custom symbol.
5. **AI markup** *(Phase 2)* — user lassos a region + types a description → `POST /api/markup/interpret` → Claude returns a list of edit ops → frontend previews and applies them.
6. **Export** — frontend serializes the live SVG (base + placed symbols) and downloads as SVG (PNG export wired later via `<canvas>.toBlob`).

## Why these choices

- **Inline SVG everywhere** — no raster basemap, no tile licensing, native click-and-drag, AI can read/write SVG directly.
- **File-system storage for MVP** — one folder per project keeps it portable and debuggable. Promote to Postgres + S3 only once it matters.
- **Prompt caching** — the style guide (`ai/client.py`) and base SVG context are cached on every Claude call; only the user description is fresh tokens.
- **Reuse of existing trail-maps code** — the four generator scripts in `trail-maps/` already implement geodata fetching, NLCD-driven tree scatter, peak finding, parcel rendering. The plan is to port them into `app/core/render.py` rather than rewrite.

## Module map

| Layer    | Module                          | Responsibility |
|----------|---------------------------------|----------------|
| API      | `api/projects.py`               | Upload, list, get, save, delete |
| API      | `api/render.py`                 | Trigger render, serve SVG |
| API      | `api/symbols.py`                | Builtin palette + AI generation |
| API      | `api/markup.py`                 | Interpret drawn-edit requests |
| Core     | `core/gpx.py`                   | GPX → bbox + elevation profile |
| Core     | `core/render.py`                | Compose base SVG (placeholder; port pending) |
| Core     | `core/geodata.py`               | Elevation / NLCD / OSM / parcels (stubs) |
| Core     | `core/cache.py`                 | Disk cache for geodata responses |
| AI       | `ai/client.py`                  | Anthropic SDK + style guide + caching |
| AI       | `ai/symbol_gen.py`              | Description → SVG `<g>` |
| AI       | `ai/markup.py`                  | Drawn region + description → edit ops |
| Frontend | `components/MapCanvas.tsx`      | SVG editor surface, drag-and-drop |
| Frontend | `components/SymbolPalette.tsx`  | Builtin + custom symbol picker |
| Frontend | `components/AIChat.tsx`         | Symbol generation UI |
| Frontend | `components/DrawingLayer.tsx`   | Lasso/freehand markup capture |
| Frontend | `store/editor.ts`               | Zustand: project, symbols, tool, selection |
| Frontend | `api/client.ts`                 | Backend HTTP client |

## Open work (Phase 1)

- [ ] Port the full base-map renderer from `trail-maps/generate_illustrated.py` into `core/render.py`.
- [ ] Implement geodata fetchers in `core/geodata.py` (elevation, NLCD, OSM, parcels).
- [ ] PNG export (canvas-based rasterization).
- [ ] Per-instance rotate/scale handles on the canvas.

## Open work (Phase 2)

- [ ] Wire `DrawingLayer` into `MapCanvas` and submit captured paths to `/api/markup/interpret`.
- [ ] Edit-op preview/accept/reject UI.
- [ ] Vision-mode Claude call (screenshot of region + SVG context).

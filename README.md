# Trail Cartographer

Turn GPX trails into customer-ready cartoon maps — auto-render terrain, land cover, and trail paths from real GIS data, then drag-and-drop custom features (fire pits, blueberry patches, signage) onto the map. AI generates new symbols on demand and applies edits described by drawing on the map.

## Features

**Phase 1 (MVP)**
- Upload GPX (KML/GeoJSON support coming) → auto-rendered base map
- Real elevation (NED), land cover (NLCD), and OSM features baked into the cartoon style
- Built-in symbol palette: trees, houses, fire pits, peaks, water, signs
- Drag-and-drop placement, reposition, delete
- Export as PNG/SVG

**Phase 2 (AI)**
- Generate custom SVG symbols by description ("blueberry patch with 5 bushes")
- Lasso a region + describe an edit → AI returns SVG patches you can preview/accept

## Stack

- **Backend** — Python 3.11, FastAPI, Anthropic SDK
- **Frontend** — React + Vite + TypeScript, Tailwind, Zustand
- **AI** — Claude (Sonnet 4.6 default, Opus for hard markup interpretation), with prompt caching
- **Geodata** — OpenTopoData (NED), NLCD WMS, OSM Overpass, NYS parcel data

## Quickstart

### Prerequisites
- Python 3.11+
- Node 20+
- An Anthropic API key (see `.env.example`)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e .
cp ../.env.example ../.env   # then fill in ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

## Repository layout

```
backend/
  app/
    api/          # FastAPI routers
    core/         # GPX parsing, rendering, geodata fetching
    ai/           # Claude integrations (symbol gen, markup interpretation)
    models/       # Pydantic models
frontend/
  src/
    components/   # MapCanvas, SymbolPalette, DrawingLayer, AIChat, ...
    hooks/        # useDraggable, useMarkup
    store/        # Zustand editor state
    api/          # Backend client
docs/             # Architecture notes
```

## Status

Early scaffold. Core modules exist as stubs that will be filled in as features land.

## License

MIT

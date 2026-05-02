from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import markup, projects, render, symbols

app = FastAPI(
    title="Trail Cartographer",
    description="Turn GPX uploads into editable cartoon maps.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(render.router, prefix="/api/render", tags=["render"])
app.include_router(symbols.router, prefix="/api/symbols", tags=["symbols"])
app.include_router(markup.router, prefix="/api/markup", tags=["markup"])


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

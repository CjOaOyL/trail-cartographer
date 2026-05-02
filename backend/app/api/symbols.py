from fastapi import APIRouter

from app.ai.symbol_gen import generate_symbol
from app.models.project import Symbol, SymbolGenRequest

router = APIRouter()


BUILTIN_SYMBOLS: list[Symbol] = [
    Symbol(id="tree", name="Tree", svg='<g><circle cx="0" cy="-8" r="10" fill="#5b8c3e"/><rect x="-2" y="0" width="4" height="8" fill="#6b3e1f"/></g>'),
    Symbol(id="pine", name="Pine", svg='<g><polygon points="0,-14 -8,4 8,4" fill="#3f7a3a"/><rect x="-2" y="4" width="4" height="6" fill="#6b3e1f"/></g>'),
    Symbol(id="house", name="House", svg='<g><polygon points="-10,0 0,-10 10,0" fill="#8a4b3a"/><rect x="-8" y="0" width="16" height="10" fill="#d8c39a"/><rect x="-2" y="3" width="4" height="7" fill="#5b3a22"/></g>'),
    Symbol(id="firepit", name="Fire pit", svg='<g><ellipse cx="0" cy="2" rx="10" ry="3" fill="#444"/><polygon points="-4,2 0,-8 4,2" fill="#e08a2a"/><polygon points="-2,2 0,-4 2,2" fill="#f4c542"/></g>'),
    Symbol(id="blueberry", name="Blueberry bush", svg='<g><circle cx="-3" cy="-2" r="2" fill="#3b5fa5"/><circle cx="2" cy="-3" r="2" fill="#3b5fa5"/><circle cx="0" cy="0" r="2" fill="#3b5fa5"/><circle cx="4" cy="1" r="2" fill="#3b5fa5"/></g>'),
    Symbol(id="peak", name="Peak", svg='<g><polygon points="-12,4 0,-12 12,4" fill="#7a6e5a" stroke="#3a2f22" stroke-width="0.8"/><polygon points="-4,-4 0,-12 4,-4" fill="#f5f5f5"/></g>'),
    Symbol(id="water", name="Water", svg='<g><ellipse cx="0" cy="0" rx="14" ry="6" fill="#7fb6d3"/></g>'),
    Symbol(id="sign", name="Sign", svg='<g><rect x="-1" y="-4" width="2" height="14" fill="#5b3a22"/><rect x="-10" y="-10" width="20" height="8" fill="#d8c39a" stroke="#5b3a22" stroke-width="0.8"/></g>'),
    Symbol(id="parking", name="Parking", svg='<g><rect x="-8" y="-8" width="16" height="16" fill="#3a6fb0" rx="2"/><text x="0" y="4" font-family="sans-serif" font-size="12" font-weight="700" fill="white" text-anchor="middle">P</text></g>'),
]


@router.get("/builtin", response_model=list[Symbol])
def list_builtin_symbols() -> list[Symbol]:
    return BUILTIN_SYMBOLS


@router.post("/generate", response_model=Symbol)
async def generate(req: SymbolGenRequest) -> Symbol:
    return await generate_symbol(req)

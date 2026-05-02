import re

from app.ai.client import STYLE_GUIDE, get_client
from app.config import settings
from app.models.project import Symbol, SymbolGenRequest

PROMPT = """Create a single SVG symbol for a cartoon trail map.

User description: {description}

Return ONLY the inline <g>...</g> markup, nothing else."""


def _extract_g(text: str) -> str:
    match = re.search(r"<g\b[\s\S]*?</g>", text)
    if not match:
        raise ValueError(f"Claude response did not contain a <g> element: {text[:200]}")
    return match.group(0)


async def generate_symbol(req: SymbolGenRequest) -> Symbol:
    client = get_client()
    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=2048,
        system=[
            {
                "type": "text",
                "text": STYLE_GUIDE,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": PROMPT.format(description=req.description),
            }
        ],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    svg = _extract_g(text)
    return Symbol(
        id=f"gen_{abs(hash(req.description)) % 10**8}",
        name=req.name or req.description[:40],
        svg=svg,
        generated=True,
    )

"""Interpret a user's drawn markup + text description into SVG edit operations.

The frontend captures:
  - The current base SVG (or a screenshot rendered to a data URL)
  - A polygon describing the region the user drew on
  - A natural-language description of what they want changed

Claude returns a JSON list of edit operations the frontend applies.
Operations supported (initial set):
  - {"op": "move",     "symbol_id": str, "dx": float, "dy": float}
  - {"op": "remove",   "symbol_id": str}
  - {"op": "replace",  "symbol_id": str, "new_symbol_svg": str}
  - {"op": "add",      "x": float, "y": float, "svg": str, "name": str}
  - {"op": "recolor",  "symbol_id": str, "fill": str | null, "stroke": str | null}

This module is intentionally a lean stub — the full prompt + JSON-mode wiring
lands as part of Phase 2 implementation.
"""

import json

from app.ai.client import get_client
from app.config import settings
from app.models.project import EditOp, MarkupRequest, MarkupResponse

PROMPT_TEMPLATE = """A user has drawn an annotation on a cartoon trail map and described what
they want changed. Return a JSON object with shape {{"ops": [...]}} where each op
follows the schema described in the system prompt. Only return valid JSON.

User description: {description}

Annotation polygon (SVG coordinates):
{polygon}

Symbols currently in the region:
{symbols}
"""

SYSTEM = """You translate user markup + descriptions into structured SVG edit operations.

Allowed ops (return strict JSON, no prose):
- move(symbol_id, dx, dy)
- remove(symbol_id)
- replace(symbol_id, new_symbol_svg)
- add(x, y, svg, name)
- recolor(symbol_id, fill, stroke)
"""


async def interpret_markup(req: MarkupRequest) -> MarkupResponse:
    client = get_client()
    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=2048,
        system=[
            {"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}
        ],
        messages=[
            {
                "role": "user",
                "content": PROMPT_TEMPLATE.format(
                    description=req.description,
                    polygon=req.polygon,
                    symbols=req.symbols_in_region,
                ),
            }
        ],
    )
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if text.startswith("```"):
        text = text.strip("`").lstrip("json").strip()
    parsed = json.loads(text)
    return MarkupResponse(ops=[EditOp(**op) for op in parsed.get("ops", [])])

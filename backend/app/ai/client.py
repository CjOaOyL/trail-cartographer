"""Anthropic SDK client wrapper.

Centralizes:
- API key loading
- Default model selection
- Prompt-cache breakpoints (system prompt + style guide are cached;
  per-request user content is fresh)

See: https://docs.claude.com/en/docs/build-with-claude/prompt-caching
"""

from anthropic import AsyncAnthropic

from app.config import settings


def get_client() -> AsyncAnthropic:
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in."
        )
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


STYLE_GUIDE = """You are designing inline SVG symbols for a hand-drawn cartoon trail map.

Style constraints:
- Output ONE inline <g>...</g> group, no wrapping <svg>, no XML declaration.
- Centered around (0, 0); intended display size ~24×24 px (target viewBox -16..16).
- Stroke weights 0.6–1.2 px; rounded line caps and joins.
- Earthy palette: forest #3f7a3a / #5b8c3e, wood #6b3e1f / #8a4b3a, parchment #d8c39a,
  water #7fb6d3, peak #7a6e5a, accents #e08a2a #f4c542 #3b5fa5.
- No raster images, no external fonts. Plain shapes, paths, polygons, text only.
- Friendly, slightly whimsical, not photorealistic.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

from app.config import settings


def cache_key(label: str, *parts: Any) -> str:
    h = hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:12]
    return f"{label}_{h}"


def cache_path(key: str) -> Path:
    return settings.cache_dir / f"{key}.json"


def get(key: str) -> Any | None:
    p = cache_path(key)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def put(key: str, value: Any) -> None:
    cache_path(key).write_text(json.dumps(value), encoding="utf-8")

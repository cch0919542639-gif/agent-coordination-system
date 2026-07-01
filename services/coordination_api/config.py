from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class Settings:
    host: str = field(default_factory=lambda: os.environ.get("HOST", "127.0.0.1"))
    port: int = field(
        default_factory=lambda: int(os.environ.get("PORT", "8000"))
    )
    log_level: str = field(
        default_factory=lambda: os.environ.get("LOG_LEVEL", "info")
    )
    api_keys: List[str] = field(default_factory=lambda: _parse_api_keys())

    @property
    def is_api_key_required(self) -> bool:
        return len(self.api_keys) > 0


def _parse_api_keys() -> List[str]:
    raw = os.environ.get("COORDINATION_API_KEYS", "")
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]

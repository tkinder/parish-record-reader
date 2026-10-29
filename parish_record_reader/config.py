"""Environment-backed settings. No key is required for the Day 1 mock path."""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dotenv is a declared dependency
    pass

# Single source of truth for the default model. Every other module and
# .env.example must reference this value instead of repeating the string.
DEFAULT_FIREWORKS_MODEL = "accounts/fireworks/models/llama-v3p2-11b-vision-instruct"


@dataclass(frozen=True)
class Settings:
    fireworks_api_key: str = ""
    fireworks_model: str = DEFAULT_FIREWORKS_MODEL
    baseten_api_key: str = ""

    @property
    def has_fireworks(self) -> bool:
        return bool(self.fireworks_api_key)

    @property
    def has_baseten(self) -> bool:
        return bool(self.baseten_api_key)


def get_settings() -> Settings:
    return Settings(
        fireworks_api_key=os.environ.get("FIREWORKS_API_KEY", ""),
        fireworks_model=os.environ.get("FIREWORKS_MODEL", DEFAULT_FIREWORKS_MODEL),
        baseten_api_key=os.environ.get("BASETEN_API_KEY", ""),
    )

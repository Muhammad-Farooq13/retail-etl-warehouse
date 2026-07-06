"""Configuration loading utilities."""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, Dict

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "config.yaml"


class ConfigBox(dict):
    """Dict that also supports attribute access, recursively."""

    def __getattr__(self, item: str) -> Any:
        try:
            value = self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc
        if isinstance(value, dict):
            return ConfigBox(value)
        return value

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


@functools.lru_cache(maxsize=None)
def load_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> ConfigBox:
    """Load and cache the YAML configuration file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as handle:
        raw: Dict[str, Any] = yaml.safe_load(handle)
    return ConfigBox(raw)


def resolve_path(relative_path: str) -> Path:
    """Resolve a path relative to the project root."""
    return PROJECT_ROOT / relative_path

"""Backend selection."""
from __future__ import annotations

import pathlib
from typing import Any, Dict

from renderers.base import Renderer


def get_renderer(name: str, config: Dict[str, Any], output_dir: pathlib.Path) -> Renderer:
    name = (name or "mock").lower()
    if name == "mock":
        from renderers.mock import MockRenderer
        return MockRenderer(config, output_dir)
    if name == "comfyui":
        from renderers.comfyui import ComfyUIRenderer
        return ComfyUIRenderer(config, output_dir)
    if name == "api":
        from renderers.api import APIRenderer
        return APIRenderer(config, output_dir)
    raise ValueError(f"unknown renderer backend: {name!r} (expected mock|comfyui|api)")


def available_backends() -> Dict[str, str]:
    return {
        "mock": "Deterministic placeholder images — pipeline testing, zero cost",
        "comfyui": "Local or remote ComfyUI server via its HTTP API",
        "api": "Generic hosted HTTP image-generation endpoint",
    }

"""Renderer interface.

Everything above this line in the stack — sampler, composer, QC, contact
sheets — only ever calls ``generate_image(spec)``. Swapping renderers must
not require touching the studio.
"""
from __future__ import annotations

import abc
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pipeline.spec import FrameSpec


class RendererUnavailable(RuntimeError):
    """Raised by ``preflight()`` when the backend cannot service requests."""


@dataclass
class RenderResult:
    ok: bool
    image_path: Optional[pathlib.Path] = None
    backend: str = ""
    duration_seconds: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Head-pose estimate, when the backend can supply one. The mock renderer
    # echoes the requested pose; a real backend should measure the output.
    measured_head_pose: Optional[Dict[str, float]] = None


class Renderer(abc.ABC):
    """Base class for all render backends."""

    name: str = "base"
    #: Capabilities the studio may query before building a request.
    capabilities: List[str] = []

    def __init__(self, config: Dict[str, Any], output_dir: pathlib.Path) -> None:
        self.config = config
        self.output_dir = pathlib.Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    @abc.abstractmethod
    def preflight(self) -> Dict[str, Any]:
        """Check the backend is reachable and correctly configured.

        Returns a dict describing backend state. Raises ``RendererUnavailable``
        if generation cannot proceed.
        """

    @abc.abstractmethod
    def generate_image(self, spec: FrameSpec) -> RenderResult:
        """Render one frame. Must never raise for ordinary failures — return
        ``RenderResult(ok=False, error=...)`` so the run can continue."""

    # ------------------------------------------------------------------
    def supports(self, capability: str) -> bool:
        return capability in self.capabilities

    def close(self) -> None:
        """Release any held resources."""

    def __enter__(self) -> "Renderer":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

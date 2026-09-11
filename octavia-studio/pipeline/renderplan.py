"""Multi-pass render planning for a single high-quality frame.

A campaign frame is one pass. A hero frame should not be: the quality
ceiling of a single base sample is well below what the same model reaches
with a refinement chain.

    base          low-res sample establishing composition and identity
    hires_fix     latent upscale + low-denoise resample, adding real detail
                  rather than interpolated pixels
    face_detail   crop the face, resample at full resolution, composite back
                  — the single largest quality gain for portraiture, because
                  the face occupies few pixels in the base sample
    upscale       final model-based upscale for print resolution

Each pass is DECLARED here and EXECUTED by the backend. A renderer reports
which passes it supports via `Renderer.capabilities`; unsupported passes are
skipped with a recorded reason rather than silently ignored, so a hero frame
never claims a refinement that did not happen.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

PASS_CAPABILITY = {
    "base": None,                       # always available
    "hires_fix": "hires_fix",
    "face_detail": "face_restore",
    "upscale": "upscale",
}


@dataclass
class RenderPass:
    name: str
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)
    requires_capability: Optional[str] = None
    skipped_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RenderPlan:
    passes: List[RenderPass] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"passes": [p.to_dict() for p in self.passes]}

    @property
    def active(self) -> List[RenderPass]:
        return [p for p in self.passes if p.enabled and not p.skipped_reason]

    def resolve(self, capabilities: List[str]) -> "RenderPlan":
        """Disable passes the backend cannot perform, recording why."""
        for p in self.passes:
            if not p.enabled:
                # Disabled by configuration, not by backend limitation.
                # Conflating the two misreports why a pass did not run.
                continue
            if p.requires_capability and p.requires_capability not in capabilities:
                p.skipped_reason = (
                    f"backend does not report capability {p.requires_capability!r}")
        return self

    def summary(self) -> str:
        bits = []
        for p in self.passes:
            if p.skipped_reason:
                bits.append(f"{p.name}(skipped)")
            elif p.enabled:
                bits.append(p.name)
        return " -> ".join(bits) if bits else "base only"


def default_plan(cfg: Dict[str, Any], width: int, height: int) -> RenderPlan:
    hero = cfg.get("hero", {})
    passes_cfg = hero.get("passes", {})

    base = passes_cfg.get("base", {})
    hires = passes_cfg.get("hires_fix", {})
    face = passes_cfg.get("face_detail", {})
    up = passes_cfg.get("upscale", {})

    return RenderPlan(passes=[
        RenderPass("base", True, {
            "width": width,
            "height": height,
            "steps": int(base.get("steps", 40)),
            "cfg_scale": float(base.get("cfg_scale", 5.0)),
            "sampler": base.get("sampler", "dpmpp_2m_sde"),
            "scheduler": base.get("scheduler", "karras"),
        }),
        RenderPass("hires_fix", bool(hires.get("enabled", True)), {
            "scale": float(hires.get("scale", 1.5)),
            # Denoise is the critical knob. Too high and the identity shifts
            # between passes — the refinement resamples the face and can
            # walk it off-model. 0.35-0.45 adds detail while holding likeness.
            "denoise": float(hires.get("denoise", 0.40)),
            "steps": int(hires.get("steps", 20)),
            "upscaler": hires.get("upscaler", "latent"),
        }, requires_capability=PASS_CAPABILITY["hires_fix"]),
        RenderPass("face_detail", bool(face.get("enabled", True)), {
            "denoise": float(face.get("denoise", 0.30)),
            "steps": int(face.get("steps", 20)),
            "padding": int(face.get("padding", 32)),
            "feather": int(face.get("feather", 8)),
        }, requires_capability=PASS_CAPABILITY["face_detail"]),
        RenderPass("upscale", bool(up.get("enabled", False)), {
            "scale": float(up.get("scale", 2.0)),
            "model": up.get("model", "4x-UltraSharp"),
        }, requires_capability=PASS_CAPABILITY["upscale"]),
    ])

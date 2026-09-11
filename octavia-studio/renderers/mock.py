"""Mock renderer — exercises the whole pipeline at zero generation cost.

It draws a legible placeholder card showing exactly what would have been
rendered, so contact sheets, QC bookkeeping and diversity statistics can all
be validated before a single GPU-second is spent.

Determinism: the same FrameSpec always produces the same placeholder and the
same synthetic QC-relevant signals, so tests are stable.
"""
from __future__ import annotations

import colorsys
import hashlib
import pathlib
import random
import time
from typing import Any, Dict, Tuple

from pipeline.spec import FrameSpec
from renderers.base import Renderer, RenderResult

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL = True
except ImportError:  # pragma: no cover
    _PIL = False


# Rough visual identity for each environment palette, so mock contact sheets
# still make palette diversity obvious at a glance.
PALETTE_HINT: Dict[str, Tuple[int, int, int]] = {
    "dark_walnut_brass_amber": (64, 42, 28),
    "white_stone_cobalt": (228, 230, 236),
    "sage_natural_timber": (156, 168, 140),
    "burgundy_black": (58, 20, 28),
    "concrete_chrome": (150, 152, 155),
    "cream_lavender": (226, 218, 232),
    "navy_warm_oak": (36, 48, 78),
    "terracotta_linen": (196, 126, 96),
    "forest_green_gold": (32, 62, 48),
    "monochrome_charcoal": (62, 62, 64),
    "white_industrial": (238, 238, 234),
    "white_marble_brass": (240, 238, 232),
    "warm_oak_cream": (214, 190, 158),
    "warm_bulb_cream": (232, 210, 176),
    "dusk_concrete_amber": (78, 74, 92),
    "white_rail_greenery": (214, 226, 208),
    "green_stone_moss": (96, 116, 88),
    "sandstone_shadow": (196, 168, 126),
    "green_teak_gravel": (132, 142, 108),
    "warm_wood_green_tile": (112, 92, 66),
    "pale_stone_steel": (208, 208, 206),
    "dark_stone_bronze": (52, 46, 42),
    "seamless_neutral": (186, 186, 186),
    "night_glass_amber": (26, 30, 42),
}


def _font(size: int):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


class MockRenderer(Renderer):
    name = "mock"
    capabilities = ["deterministic", "no_cost", "head_pose_echo"]

    def preflight(self) -> Dict[str, Any]:
        return {
            "backend": "mock",
            "available": True,
            "pillow": _PIL,
            "note": "Placeholder renderer. Produces no photographic output.",
        }

    # ------------------------------------------------------------------
    def generate_image(self, spec: FrameSpec) -> RenderResult:
        start = time.time()
        path = self.output_dir / f"{spec.frame_id}.png"
        try:
            if _PIL:
                self._draw_card(spec, path)
            else:
                path = path.with_suffix(".txt")
                path.write_text(spec.prompt, encoding="utf-8")
        except Exception as exc:  # pragma: no cover
            return RenderResult(ok=False, backend=self.name, error=f"{type(exc).__name__}: {exc}",
                                duration_seconds=time.time() - start)

        return RenderResult(
            ok=True,
            image_path=path,
            backend=self.name,
            duration_seconds=time.time() - start,
            metadata={"placeholder": True},
            # The mock echoes the requested head pose. A real backend must
            # MEASURE the rendered face instead — see qc/headpose.py.
            measured_head_pose={"yaw": spec.head.yaw, "pitch": spec.head.pitch,
                                "roll": spec.head.roll},
        )

    # ------------------------------------------------------------------
    def _draw_card(self, spec: FrameSpec, path: pathlib.Path) -> None:
        w, h = spec.width, spec.height
        base = PALETTE_HINT.get(spec.scene.get("env_palette", ""), (140, 140, 140))
        img = Image.new("RGB", (w, h), base)
        d = ImageDraw.Draw(img)

        # Vertical gradient so the card reads as a lit space, not a flat swatch.
        for y in range(h):
            t = y / h
            shade = tuple(int(c * (1.0 - 0.35 * t) + 18 * t) for c in base)
            d.line([(0, y), (w, y)], fill=shade)

        # Silhouette block whose width tracks the shot type — makes crop
        # diversity visible at contact-sheet size.
        shot = spec.camera.get("shot", {}).get("id", "waist_up")
        span = {"close_portrait": 0.42, "head_and_shoulders": 0.50, "waist_up": 0.58,
                "three_quarter": 0.52, "full_body": 0.40, "environmental_full_body": 0.26,
                "seated_full": 0.50, "mirror_selfie": 0.46, "candid_detail": 0.62}.get(shot, 0.5)
        sw = int(w * span)
        sx = (w - sw) // 2 + int(spec.head.yaw * 0.8)
        top = int(h * 0.18)
        sil = tuple(max(0, c - 46) for c in base)
        d.rounded_rectangle([sx, top, sx + sw, h - int(h * 0.06)], radius=int(sw * 0.18), fill=sil)

        # Head disc, offset by roll so left/right tilt is visually apparent.
        hr = int(sw * 0.30)
        hx = sx + sw // 2 + int(spec.head.roll * 1.6)
        hy = top - int(hr * 0.55)
        d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr],
                  fill=tuple(min(255, c + 34) for c in sil))

        # Caption block
        f_big, f_sm = _font(int(h * 0.026)), _font(int(h * 0.019))
        lines = [
            f"#{spec.index:03d}  {spec.frame_id}",
            f"scene   {spec.scene.get('id','')}  [{spec.scene.get('env_palette','')}]",
            f"pose    {spec.pose.get('id','')}  ({spec.pose.get('family','')})",
            f"head    {spec.head.position_id}  yaw {spec.head.yaw:+.0f} pitch {spec.head.pitch:+.0f} roll {spec.head.roll:+.0f} [{spec.head.tilt_class}]",
            f"wardrobe {'+'.join(spec.wardrobe.families)[:58]}",
            f"colours {','.join(spec.wardrobe.colours.values())}  ({(spec.wardrobe.harmony or {}).get('id','')})",
            f"camera  {spec.camera.get('focal',{}).get('id','')} {shot} {spec.camera.get('height',{}).get('id','')}",
            f"light   {spec.lighting.get('id','')}   expr {spec.expression.get('id','')}",
        ]
        pad = int(h * 0.018)
        box_h = pad * 2 + int(h * 0.024) + len(lines) * int(h * 0.024)
        d.rectangle([0, 0, w, box_h], fill=(10, 10, 12))
        y = pad
        for i, line in enumerate(lines):
            d.text((pad, y), line, font=(f_big if i == 0 else f_sm), fill=(238, 238, 240))
            y += int(h * 0.024)

        d.rectangle([0, 0, w - 1, h - 1], outline=(0, 0, 0), width=2)
        img.save(path, "PNG")

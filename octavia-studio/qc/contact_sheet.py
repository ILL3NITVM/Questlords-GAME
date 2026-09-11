"""Contact sheets for human review (section 13).

One sheet per batch of 8. Each cell shows the frame number, headline QC
score, wardrobe/scene/pose family, and head-roll class, plus a row of tick
boxes for the seven review verdicts so a sheet can be marked on paper or on
screen and transcribed back via ``studio.py review``.
"""
from __future__ import annotations

import pathlib
from typing import Any, Dict, List, Optional

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL = True
except ImportError:  # pragma: no cover
    _PIL = False

MARKS = ["KEEP", "REJECT", "IDENTITY_DRIFT", "BODY_DRIFT",
         "POSE_DUPLICATE", "WARDROBE_BAD", "SCENE_BAD"]

CELL_W, CELL_H = 420, 660
COLS, ROWS = 4, 2
MARGIN, GUTTER = 28, 16
CAPTION_H = 132
HEADER_H = 70


def _font(size: int, bold: bool = False):
    names = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for n in names:
        for base in ("/usr/share/fonts/truetype/dejavu/",):
            try:
                return ImageFont.truetype(base + n, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _fit(draw, text: str, font, max_w: int) -> str:
    if draw.textlength(text, font=font) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=font) > max_w:
        text = text[:-1]
    return text + "…"


def build_contact_sheet(frames: List[Dict[str, Any]], out_path: pathlib.Path,
                        sheet_index: int, run_id: str) -> Optional[pathlib.Path]:
    """``frames`` are manifest records (dicts) for up to 8 images."""
    if not _PIL:
        raise RuntimeError("Pillow is required for contact sheets (pip install Pillow)")

    sheet_w = MARGIN * 2 + COLS * CELL_W + (COLS - 1) * GUTTER
    sheet_h = HEADER_H + MARGIN * 2 + ROWS * (CELL_H + CAPTION_H) + (ROWS - 1) * GUTTER
    sheet = Image.new("RGB", (sheet_w, sheet_h), (22, 22, 25))
    d = ImageDraw.Draw(sheet)

    f_title = _font(28, bold=True)
    f_num = _font(22, bold=True)
    f_body = _font(17)
    f_small = _font(14)
    f_mark = _font(13)

    d.text((MARGIN, 22), f"OCTAVIA STUDIO — {run_id} — contact sheet {sheet_index:02d}",
           font=f_title, fill=(240, 240, 244))
    d.text((sheet_w - MARGIN - 330, 28),
           "mark each frame:  KEEP / REJECT / IDENTITY_DRIFT / BODY_DRIFT",
           font=f_small, fill=(150, 150, 158))

    for i, rec in enumerate(frames[:COLS * ROWS]):
        col, row = i % COLS, i // COLS
        x = MARGIN + col * (CELL_W + GUTTER)
        y = HEADER_H + MARGIN + row * (CELL_H + CAPTION_H + GUTTER)

        # --- image -----------------------------------------------------
        img_path = rec.get("image_path")
        placed = False
        if img_path and pathlib.Path(img_path).is_file():
            try:
                im = Image.open(img_path).convert("RGB")
                im.thumbnail((CELL_W, CELL_H))
                ox = x + (CELL_W - im.width) // 2
                oy = y + (CELL_H - im.height) // 2
                d.rectangle([x, y, x + CELL_W, y + CELL_H], fill=(12, 12, 14))
                sheet.paste(im, (ox, oy))
                placed = True
            except Exception:
                placed = False
        if not placed:
            d.rectangle([x, y, x + CELL_W, y + CELL_H], fill=(46, 46, 50))
            d.text((x + 16, y + CELL_H // 2), "missing image", font=f_body, fill=(160, 160, 165))

        # --- status stripe ---------------------------------------------
        verdict = rec.get("verdict", {})
        accepted = verdict.get("accepted", True)
        stripe = (58, 150, 92) if accepted else (176, 62, 62)
        d.rectangle([x, y, x + CELL_W, y + 6], fill=stripe)

        # --- caption ----------------------------------------------------
        cy = y + CELL_H + 6
        d.rectangle([x, cy, x + CELL_W, cy + CAPTION_H - 6], fill=(32, 32, 36))
        keys = rec.get("category_keys", {})
        score = rec.get("overall_score", 0.0)
        head = rec.get("head_pose", {})
        tilt = head.get("tilt_class", "?")
        tilt_col = (226, 138, 96) if tilt == "left" else (150, 150, 158)

        d.text((x + 10, cy + 7), f"#{rec.get('index', 0):03d}", font=f_num, fill=(240, 240, 244))
        d.text((x + 96, cy + 9), f"QC {score:.0f}", font=f_num,
               fill=(120, 214, 150) if score >= 85 else (232, 180, 96))
        d.text((x + 196, cy + 11), f"roll {head.get('roll', 0):+.0f}  {tilt}",
               font=f_small, fill=tilt_col)
        if not accepted:
            d.text((x + 330, cy + 11), "REJECTED", font=f_small, fill=(232, 120, 120))

        rows = [
            ("wardrobe", keys.get("wardrobe_family", "")),
            ("scene", f"{keys.get('scene_family','')} / {keys.get('scene_id','')}"),
            ("pose", f"{keys.get('pose_family','')} / {keys.get('head_position','')}"),
        ]
        ry = cy + 34
        for label, value in rows:
            d.text((x + 10, ry), f"{label:9s}", font=f_small, fill=(132, 132, 140))
            d.text((x + 82, ry), _fit(d, value, f_body, CELL_W - 96), font=f_body,
                   fill=(222, 222, 228))
            ry += 21

        # --- review tick boxes -------------------------------------------
        bx = x + 10
        by = cy + CAPTION_H - 30
        for m in MARKS:
            label = {"KEEP": "K", "REJECT": "R", "IDENTITY_DRIFT": "ID", "BODY_DRIFT": "BD",
                     "POSE_DUPLICATE": "PD", "WARDROBE_BAD": "WB", "SCENE_BAD": "SB"}[m]
            d.rectangle([bx, by, bx + 15, by + 15], outline=(120, 120, 128), width=1)
            d.text((bx + 20, by + 1), label, font=f_mark, fill=(168, 168, 176))
            bx += 20 + int(d.textlength(label, font=f_mark)) + 12

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, "JPEG", quality=90)
    return out_path

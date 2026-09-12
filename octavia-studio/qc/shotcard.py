"""Render a shot card: the hero frame as a photographer would plan it.

This is not the photograph — it is the plan for it. A framing diagram with
the subject placed in the actual output aspect ratio, the lighting direction,
the wardrobe and environment palettes as real swatches, the camera
parameters, and the identity anchors that must survive the render.

It exists because a FrameSpec is a hundred lines of JSON, and a hundred lines
of JSON does not tell you whether the composition is any good. This does, at
a glance, before any GPU time is spent.
"""
from __future__ import annotations

import math
import pathlib
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1680, 1040
BG = (18, 18, 21)
PANEL = (27, 27, 31)
LINE = (58, 58, 64)
TEXT = (232, 232, 238)
DIM = (140, 140, 150)
ACCENT = (176, 214, 120)          # Octavia's signature lime-green
WARN = (232, 176, 96)

FONTS = "/usr/share/fonts/truetype/dejavu/"


def _f(size: int, bold: bool = False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(FONTS + name, size)
    except OSError:
        return ImageFont.load_default()


def _hex(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _fit(d: ImageDraw.ImageDraw, text: str, font, max_w: int) -> str:
    if d.textlength(text, font=font) <= max_w:
        return text
    while text and d.textlength(text + "…", font=font) > max_w:
        text = text[:-1]
    return text + "…"


def _panel(d: ImageDraw.ImageDraw, box, title: str, font) -> Tuple[int, int]:
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=10, fill=PANEL, outline=LINE, width=1)
    d.text((x0 + 18, y0 + 14), title.upper(), font=font, fill=DIM)
    return x0 + 18, y0 + 44


# ----------------------------------------------------------------------
def _draw_framing(d: ImageDraw.ImageDraw, img: Image.Image, box,
                  spec: Dict[str, Any], fonts: Dict[str, Any]) -> None:
    """The output frame at true aspect ratio, with the subject placed by
    shot type and the crop that framing implies."""
    x0, y0 = _panel(d, box, "framing", fonts["label"])
    x1, y1 = box[2], box[3]

    avail_w, avail_h = (x1 - x0) - 18, (y1 - y0) - 30
    out_w = spec.get("width", 896)
    out_h = spec.get("height", 1152)
    aspect = out_w / out_h
    fh = avail_h
    fw = fh * aspect
    if fw > avail_w:
        fw = avail_w
        fh = fw / aspect
    fx = x0 + (avail_w - fw) / 2
    fy = y0 + (avail_h - fh) / 2

    frame = [fx, fy, fx + fw, fy + fh]
    d.rectangle(frame, fill=(10, 10, 12), outline=(90, 90, 98), width=2)

    # Rule-of-thirds guides
    for i in (1, 2):
        gx = fx + fw * i / 3
        gy = fy + fh * i / 3
        d.line([(gx, fy), (gx, fy + fh)], fill=(48, 48, 54), width=1)
        d.line([(fx, gy), (fx + fw, gy)], fill=(48, 48, 54), width=1)

    shot = spec.get("camera", {}).get("shot", {})
    emphasis = shot.get("emphasis", "body")
    head = spec.get("head", {})
    yaw = float(head.get("yaw", 0) or 0)
    roll = float(head.get("roll", 0) or 0)

    # How much of a standing figure the crop shows.
    span = {"face": 0.30, "detail": 0.55, "upper_body": 0.52,
            "body": 1.0, "environment": 1.0}.get(emphasis, 0.7)
    figure_scale = {"face": 3.1, "upper_body": 1.9, "body": 1.0,
                    "environment": 0.55, "detail": 1.6}.get(emphasis, 1.0)

    fig_h = fh * 0.92 * figure_scale
    fig_w = fig_h * 0.26
    cx = fx + fw * 0.5 - (yaw / 90.0) * fw * 0.06
    top = fy + fh * (0.10 if emphasis in ("face", "upper_body", "detail") else 0.06)

    body = Image.new("RGBA", (int(fw), int(fh)), (0, 0, 0, 0))
    bd = ImageDraw.Draw(body)
    bx = cx - fx
    head_r = fig_w * 0.42
    # Torso
    bd.rounded_rectangle(
        [bx - fig_w / 2, (top - fy) + head_r * 1.5,
         bx + fig_w / 2, (top - fy) + fig_h],
        radius=fig_w * 0.3, fill=(74, 78, 88, 255))
    # Head, offset by roll so the tilt is visible
    hx = bx + math.sin(math.radians(roll)) * head_r * 1.1
    hy = (top - fy) + head_r
    bd.ellipse([hx - head_r, hy - head_r, hx + head_r, hy + head_r],
               fill=(112, 118, 132, 255))
    # Signature highlight flash, so identity is present even in the plan
    bd.arc([hx - head_r, hy - head_r, hx + head_r, hy + head_r],
           start=200, end=340, fill=ACCENT + (255,), width=max(2, int(head_r * 0.18)))

    frame_img = Image.new("RGBA", (int(fw), int(fh)), (0, 0, 0, 0))
    frame_img.alpha_composite(body)
    img.paste(Image.alpha_composite(
        Image.new("RGBA", frame_img.size, (10, 10, 12, 255)), frame_img).convert("RGB"),
        (int(fx), int(fy)))

    # Redraw guides above the figure
    d2 = ImageDraw.Draw(img)
    for i in (1, 2):
        gx = fx + fw * i / 3
        gy = fy + fh * i / 3
        d2.line([(gx, fy), (gx, fy + fh)], fill=(60, 60, 68), width=1)
        d2.line([(fx, gy), (fx + fw, gy)], fill=(60, 60, 68), width=1)
    d2.rectangle(frame, outline=(105, 105, 115), width=2)

    cap = fonts["small"]
    d2.text((fx, fy + fh + 10), f"{out_w} x {out_h}", font=cap, fill=DIM)
    label = shot.get("label", "")
    d2.text((fx + fw, fy + fh + 10), label, font=cap, fill=TEXT,
            anchor="ra")


def _draw_lighting(d: ImageDraw.ImageDraw, box, spec: Dict[str, Any],
                   fonts: Dict[str, Any]) -> None:
    """Overhead diagram: where the key light sits relative to the subject."""
    x0, y0 = _panel(d, box, "lighting", fonts["label"])
    x1, y1 = box[2], box[3]
    cx = (x0 + x1 - 18) / 2
    cy = y0 + (y1 - y0 - 44) / 2 + 6
    r = min((x1 - x0) * 0.30, (y1 - y0) * 0.30)

    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=LINE, width=1)
    # Subject
    d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], fill=(112, 118, 132))
    # Camera, always at the bottom of the diagram
    d.polygon([(cx - 13, cy + r + 6), (cx + 13, cy + r + 6), (cx, cy + r - 8)],
              fill=(96, 100, 112))
    d.text((cx, cy + r + 26), "camera", font=fonts["small"], fill=DIM, anchor="ma")

    lighting = spec.get("lighting", {})
    lid = lighting.get("id", "")
    # Key-light bearing in degrees, measured from camera axis.
    bearing = {
        "beauty_dish": 0, "broad_flat_studio": 0, "bulb_mirror": 0,
        "softbox_key": -40, "rim_and_fill": 150, "low_key_pooled": -70,
        "soft_window_daylight": -55, "hard_window_shaft": -70,
        "open_shade": 180, "overcast_soft": 180, "golden_hour": 130,
        "blue_hour": 160, "dappled_canopy": -100, "city_practicals": 120,
        "warm_lamplight": -120,
    }.get(lid, -45)
    ang = math.radians(bearing - 90)
    lx = cx + math.cos(ang) * r
    ly = cy + math.sin(ang) * r
    warm = lighting.get("temperature", "")
    col = (240, 206, 140) if "warm" in warm else (
        (176, 200, 232) if "cool" in warm else (234, 234, 240))
    d.line([(lx, ly), (cx, cy)], fill=col, width=2)
    d.ellipse([lx - 14, ly - 14, lx + 14, ly + 14], fill=col)
    d.text((cx, y1 - 30), lighting.get("label", ""), font=fonts["small"],
           fill=TEXT, anchor="ma")


def _swatches(d: ImageDraw.ImageDraw, x: int, y: int, colours: List[Tuple[str, str]],
              fonts: Dict[str, Any], size: int = 52, gap: int = 30) -> int:
    """Swatch labels are centred under their swatch, so the cell width — not
    the label length — decides how much text fits. Without that, adjacent
    labels run together into one unreadable string."""
    cell = size + gap
    for i, (label, hexv) in enumerate(colours):
        sx = x + i * cell
        d.rounded_rectangle([sx, y, sx + size, y + size], radius=6,
                            fill=_hex(hexv), outline=LINE, width=1)
        d.text((sx + size / 2, y + size + 8),
               _fit(d, label, fonts["tiny"], cell - 6),
               font=fonts["tiny"], fill=DIM, anchor="ma")
    return y + size + 28


# ----------------------------------------------------------------------
def build_shot_card(recipe: Dict[str, Any], out_path: pathlib.Path,
                    colours_by_id: Optional[Dict[str, Any]] = None,
                    env_swatch: Optional[Tuple[int, int, int]] = None
                    ) -> pathlib.Path:
    spec = recipe.get("spec", recipe)
    fonts = {
        "h1": _f(30, True), "h2": _f(19, True), "label": _f(13, True),
        "body": _f(16), "small": _f(13), "tiny": _f(11), "mono": _f(13),
    }

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # ---- header ------------------------------------------------------
    d.text((44, 36), "OCTAVIA — HERO FRAME", font=fonts["h1"], fill=TEXT)
    score = recipe.get("hero_score", {}).get("total")
    if score is not None:
        d.text((44, 76), f"shot plan · hero score {score}/100", font=fonts["body"], fill=DIM)
    seed = recipe.get("master_seed")
    if seed is not None:
        d.text((W - 44, 44), f"seed {seed}", font=fonts["body"], fill=DIM, anchor="ra")
        d.text((W - 44, 70), f"{recipe.get('candidates_searched', '?')} candidates searched",
               font=fonts["small"], fill=DIM, anchor="ra")
    d.line([(44, 112), (W - 44, 112)], fill=LINE, width=1)

    # ---- framing + lighting -----------------------------------------
    _draw_framing(d, img, (44, 136, 470, 800), spec, fonts)
    d = ImageDraw.Draw(img)
    _draw_lighting(d, (492, 136, 800, 470), spec, fonts)

    # ---- camera ------------------------------------------------------
    x0, y = _panel(d, (492, 492, 800, 800), "camera", fonts["label"])
    cam = spec.get("camera", {})
    rows = [
        ("lens", cam.get("focal", {}).get("label", "")),
        ("aperture", cam.get("aperture", {}).get("label", "").split(" ")[0]),
        ("height", cam.get("height", {}).get("id", "").replace("_", " ")),
        ("angle", cam.get("angle", {}).get("id", "").replace("_", " ")),
    ]
    head = spec.get("head", {})
    rows += [
        ("head yaw", f"{head.get('yaw', 0):+.0f}°"),
        ("head roll", f"{head.get('roll', 0):+.0f}°  ({head.get('tilt_class', '')})"),
        ("gaze", str(head.get("eye_direction", "")).replace("_", " ")),
    ]
    for label, value in rows:
        d.text((x0, y), label, font=fonts["small"], fill=DIM)
        d.text((x0 + 108, y - 2), _fit(d, str(value), fonts["body"], 170),
               font=fonts["body"], fill=TEXT)
        y += 32

    # ---- identity ----------------------------------------------------
    x0, y = _panel(d, (822, 136, W - 44, 400), "identity anchors — must survive the render",
                   fonts["label"])
    anchors = ["green-hazel eyes", "natural freckles", "long dark brunette hair",
               "lime-green face-framing highlights"]
    for a in anchors:
        d.ellipse([x0, y + 5, x0 + 9, y + 14], fill=ACCENT)
        d.text((x0 + 20, y), a, font=fonts["body"], fill=TEXT)
        y += 30
    y += 6
    d.text((x0, y), "physique lock", font=fonts["small"], fill=DIM)
    y += 22
    d.text((x0, y), "shoulder:waist 1.55   ·   hip:waist 1.50", font=fonts["body"], fill=TEXT)
    y += 30
    d.text((x0, y), "adult woman, late twenties · no tattoos", font=fonts["small"], fill=DIM)

    # ---- wardrobe + palette -----------------------------------------
    x0, y = _panel(d, (822, 422, W - 44, 690), "wardrobe & palette", fonts["label"])
    w = spec.get("wardrobe", {})
    pieces: List[str] = []
    for key in ("top", "bottom", "dress", "outer_layer", "footwear"):
        item = w.get(key)
        if item:
            pieces.append(item.get("label", ""))
    d.text((x0, y), _fit(d, " · ".join(pieces), fonts["body"], W - 44 - x0 - 20),
           font=fonts["body"], fill=TEXT)
    y += 30
    acc = [a.get("label", "") for a in (w.get("accessories") or [])]
    if acc:
        d.text((x0, y), _fit(d, "+ " + ", ".join(acc), fonts["small"], W - 44 - x0 - 20),
               font=fonts["small"], fill=DIM)
    y += 28

    sw: List[Tuple[str, str]] = []
    cb = colours_by_id or {}
    for slot, cid in (w.get("colours") or {}).items():
        entry = cb.get(cid, {})
        if entry.get("hex"):
            sw.append((cid.replace("_", " "), entry["hex"]))
    if env_swatch:
        sw.append(("environment", "#%02X%02X%02X" % env_swatch))
    if sw:
        y = _swatches(d, x0, y, sw, fonts)
    harmony = (w.get("harmony") or {}).get("label", "")
    if harmony:
        d.text((x0, y), f"harmony: {harmony}", font=fonts["small"], fill=DIM)

    # ---- scene + pose ------------------------------------------------
    x0, y = _panel(d, (822, 712, W - 44, 800), "scene & pose", fonts["label"])
    scene = spec.get("scene", {})
    pose = spec.get("pose", {})
    d.text((x0, y), _fit(d, scene.get("label", ""), fonts["body"], W - 44 - x0 - 20),
           font=fonts["body"], fill=TEXT)
    y += 26
    d.text((x0, y), _fit(d, f"{pose.get('label', '')} · {spec.get('hands', {}).get('label', '')}",
                         fonts["small"], W - 44 - x0 - 20), font=fonts["small"], fill=DIM)

    # ---- prompt ------------------------------------------------------
    x0, y = _panel(d, (44, 822, W - 44, H - 36), "positive prompt", fonts["label"])
    prompt = recipe.get("prompt", "")
    meta = recipe.get("prompt_meta", {}).get("positive", {}).get("budget", {})
    if meta:
        d.text((W - 62, 836), f"{meta.get('tokens', '?')} tokens · "
                              f"{meta.get('chunks', '?')} CLIP chunk(s)",
               font=fonts["small"], fill=DIM, anchor="ra")
    words = prompt.split(" ")
    line, lines = "", []
    maxw = W - 44 - x0 - 24
    for word in words:
        trial = (line + " " + word).strip()
        if d.textlength(trial, font=fonts["mono"]) > maxw:
            lines.append(line)
            line = word
        else:
            line = trial
    lines.append(line)
    for ln in lines[:5]:
        d.text((x0, y), ln, font=fonts["mono"], fill=(206, 210, 216))
        y += 21

    # ---- footer ------------------------------------------------------
    d.text((44, H - 26), "This is the shot plan, not the photograph — "
                         "rendering requires a model backend.",
           font=fonts["tiny"], fill=WARN)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    return out_path

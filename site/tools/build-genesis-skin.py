#!/usr/bin/env python3
"""Builds the GENESIS skin: QuadCOM's master skin, engraved from the system's own geometry.

    python3 site/tools/build-genesis-skin.py

Every motif is derived from QuadCOM itself rather than borrowed ornament:
  seal        The Genesis Seal. A four-fold guilloche rosette (four quadrants, one per diamond of the
              mark) engraved around the quad-diamond mark, inside a ring of exactly 2000 ticks: one
              per PicoProcessor in the fleet, with a longer tick every 100 (20 sectors) and a diamond
              every 500 (the four quadrants).
  intaglio    Panel material: banknote-style engraved hairlines whose weight swells in four waves
              across each tile. Line art, not noise, so it stays crisp at every pixel density.
  corner-*    Quarter-diamond corners: each panel corner is cut with one quarter of the mark's diamond,
              echoed by an engraved bracket.
  band        A guilloche band (two interlaced waves crossing four times per repeat) for header edges;
              band-quiet is the desk's lower-contrast cut.
  pip         The bare quarter-diamond, for the desk's small data cells.
  node        One diamond of the quad rule. CSS draws the rule as a hairline with four nodes at its
              quarter points, so the diamonds never stretch with the rule's width.
  bezel       A reeded coin bezel (a struck coin's edge) that frames every coin mark.
All files are deterministic SVG line art: re-running this script produces identical bytes.
The skin is ornament only. It never touches data ink, and the chart field stays black.
"""
import math, os

OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "textures", "genesis")
GOLD, HI, STEEL = "#d9b45f", "#f2d98f", "#8e968f"

def f(v):
    s = f"{v:.1f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s

def lead(v):
    """Number for relative path data: 0.1 precision, leading zero dropped (-0.4 -> -.4, 0.4 -> .4)."""
    t = f(v)
    return "." + t[2:] if t.startswith("0.") else "-." + t[3:] if t.startswith("-0.") else t

def poly(points, close=True):
    """Polyline as compact path data: absolute start, then relative steps on a 0.1 grid. Steps are
    taken between grid-rounded positions, so rounding never accumulates along a long curve."""
    head, *rest = points
    px, py = round(head[0], 1), round(head[1], 1)
    out = ["M" + f(px) + " " + f(py) + "l"]
    for x, y in rest:
        nx, ny = round(x, 1), round(y, 1)
        for i, v in enumerate((lead(nx - px), lead(ny - py))):
            out.append(v if v.startswith("-") or (i == 0 and len(out) == 1) else " " + v)
        px, py = nx, ny
    return "".join(out) + ("z" if close else "")

def svg(w, h, body, extra=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}"{extra}>'
            + body + "</svg>\n")

def polar_curve(rfn, n, cx=500, cy=500, turns=1.0):
    return [(cx + rfn(t) * math.cos(t), cy + rfn(t) * math.sin(t))
            for t in (2 * math.pi * turns * i / n for i in range(n))]

def quad_mark(cx, cy, s):
    """The official QuadCOM mark, measured from assets/quadcom-official-logo.png on its 640px grid:
    a cluster of four small diamonds (half-diagonal 48) above three large ones (half-diagonal 115),
    placed about the logo centre (320, 320) and scaled by s."""
    small = [(319.5, 136.5), (265.5, 191.5), (374.5, 191.5), (319.5, 245.5)]
    large = [(192, 319.5), (448, 319.5), (320, 448)]
    shapes = [(x, y, 48) for x, y in small] + [(x, y, 115) for x, y in large]
    return [[(cx + (x - 320 + dx) * s, cy + (y - 320 + dy) * s) for dx, dy in ((0, -h), (h, 0), (0, h), (-h, 0))]
            for x, y, h in shapes]

def seal(stroke, opacity):
    g = []
    a = f' fill="none" stroke="{stroke}" stroke-opacity="{opacity}" stroke-linejoin="round"'
    # Fleet ring: 2000 ticks, one per PicoProcessor.
    minor, major = [], []
    for i in range(2000):
        t = 2 * math.pi * i / 2000 - math.pi / 2
        r0, r1 = (462, 490) if i % 100 == 0 else (470, 480)
        seg = poly([(500 + r0 * math.cos(t), 500 + r0 * math.sin(t)), (500 + r1 * math.cos(t), 500 + r1 * math.sin(t))], False)
        (major if i % 100 == 0 else minor).append(seg)
    g.append(f'<path d="{"".join(minor)}"{a} stroke-width=".6"/>')
    g.append(f'<path d="{"".join(major)}"{a} stroke-width="1.4"/>')
    for r in (458, 494):
        g.append(f'<circle cx="500" cy="500" r="{r}"{a} stroke-width="1"/>')
    # Quadrant diamonds at ticks 0, 500, 1000, 1500.
    for k in range(4):
        t = k * math.pi / 2 - math.pi / 2
        x, y = 500 + 476 * math.cos(t), 500 + 476 * math.sin(t)
        g.append(f'<path d="{poly([(x, y - 14), (x + 10, y), (x, y + 14), (x - 10, y)] if k % 2 == 0 else [(x - 14, y), (x, y - 10), (x + 14, y), (x, y + 10)])}" fill="{stroke}" fill-opacity="{opacity}"/>')
    # Outer guilloche: 16 lobes (4 x 4). Twelve strands with phases spread over a full lobe period cross
    # one another and weave a lattice; the amplitude breathes four times per turn (the quadrants).
    for k in range(12):
        ph = 2 * math.pi * k / 12
        pts = polar_curve(lambda t, ph=ph: 404 + 34 * math.sin(16 * t + ph) * (0.78 + 0.22 * math.cos(4 * t)), 576)
        g.append(f'<path d="{poly(pts)}"{a} stroke-width=".7"/>')
    for r in (356, 448):
        g.append(f'<circle cx="500" cy="500" r="{r}"{a} stroke-width=".8"/>')
    # Middle band: ten strands of a 24-lobe wave whose amplitude is gathered at the four quadrant axes.
    for k in range(10):
        ph = 2 * math.pi * k / 10
        pts = polar_curve(lambda t, ph=ph: 282 + (14 + 30 * math.cos(2 * t) ** 2) * math.sin(24 * t + ph), 720)
        g.append(f'<path d="{poly(pts)}"{a} stroke-width=".7"/>')
    # Inner rosette: epitrochoids with four cusps (R = 4r), several pen offsets.
    # Two families, the second turned by 45 degrees, so the cusps interleave into an eight-point star.
    for rot in (0.0, math.pi / 4):
        for d in (0.4, 0.7, 1.0, 1.3):
            R, r = 116.0, 29.0
            pts = []
            for i in range(480):
                t = 2 * math.pi * i / 480
                x = (R + r) * math.cos(t) - d * r * math.cos((R + r) / r * t)
                y = (R + r) * math.sin(t) - d * r * math.sin((R + r) / r * t)
                pts.append((500 + x * math.cos(rot) - y * math.sin(rot), 500 + x * math.sin(rot) + y * math.cos(rot)))
            g.append(f'<path d="{poly(pts)}"{a} stroke-width=".7"/>')
    g.append(f'<circle cx="500" cy="500" r="206"{a} stroke-width="1"/>')
    if opacity >= 1:  # the specimen seal gets a struck centre; the watermark stays open (no dark smudge)
        g.append('<circle cx="500" cy="500" r="96" fill="#040504"/>')
    # The mark, engraved: filled diamonds with a hairline echo.
    for d in quad_mark(500, 500, .34):
        g.append(f'<path d="{poly(d)}" fill="{stroke}" fill-opacity="{opacity}"/>')
    for d in quad_mark(500, 500, .34):  # hairline echo: each diamond enlarged about its own centre
        mx = sum(x for x, _ in d) / 4; my = sum(y for _, y in d) / 4
        g.append(f'<path d="{poly([(mx + (x - mx) * 1.22, my + (y - my) * 1.22) for x, y in d])}"{a} stroke-width=".8"/>')
    return svg(1000, 1000, "".join(g))

def intaglio(opacity):
    # 96x24 tile: eight engraved lines, each a closed sliver whose width swells four times per repeat
    # (period 24px, so the tile wraps seamlessly on both axes).
    body = []
    for k in range(8):
        y0 = 1.5 + k * 3
        top, bot = [], []
        for i in range(0, 97, 4):
            w = 0.18 + 0.32 * (0.5 + 0.5 * math.sin(2 * math.pi * (i / 24) + k * math.pi / 4))
            top.append((i, y0 - w)); bot.append((i, y0 + w))
        body.append(f'<path d="{poly(top + bot[::-1])}" fill="{GOLD}" fill-opacity="{opacity}"/>')
    return svg(96, 24, "".join(body))

def corner(rot):
    # 24x24, drawn for the top-left corner and rotated for the others: the corner is cut with one quarter
    # of the mark's diamond, echoed by an engraved bracket set clear of the panel border.
    d = (f'<path d="M0 0L9 0L0 9Z" fill="{GOLD}" fill-opacity=".78"/>'
         f'<path d="M5 17V5h12" fill="none" stroke="{GOLD}" stroke-opacity=".5" stroke-width=".75"/>')
    return svg(24, 24, f'<g transform="rotate({rot} 12 12)">{d}</g>')

def pip():
    # 10x10: the bare quarter-diamond for small cells, where a bracket would read as speckle.
    return svg(10, 10, f'<path d="M0 0L6 0L0 6Z" fill="{GOLD}" fill-opacity=".8"/>')

def band(o1=.55, o2=.3):
    # 48x10 guilloche band: two waves in counter-phase, crossing four times per repeat.
    a = [(x / 2, 5 + 3.2 * math.sin(2 * math.pi * x / 48)) for x in range(0, 97)]
    b = [(x / 2, 5 - 3.2 * math.sin(2 * math.pi * x / 48)) for x in range(0, 97)]
    c = [(x / 2, 5 + 1.6 * math.sin(4 * math.pi * x / 48 + math.pi / 2)) for x in range(0, 97)]
    s = f' fill="none" stroke="{GOLD}" stroke-width=".6"'
    return svg(48, 10, f'<path d="{poly(a, False)}"{s} stroke-opacity="{o1}"/><path d="{poly(b, False)}"{s} stroke-opacity="{o1}"/>'
                       f'<path d="{poly(c, False)}"{s} stroke-opacity="{o2}"/>', ' preserveAspectRatio="none"')

def node():
    # 10x10 diamond node of the quad rule (kept square; the rule itself is a CSS hairline).
    return svg(10, 10, f'<path d="M5 .5L9.5 5 5 9.5 .5 5Z" fill="{GOLD}" fill-opacity=".8"/>')

def bezel():
    # 64x64 reeded bezel: an engraved ring with 120 reeds, drawn outside a 56px coin window.
    reeds = "".join(
        f"M{f(32 + 29 * math.cos(t))} {f(32 + 29 * math.sin(t))}L{f(32 + 31.5 * math.cos(t))} {f(32 + 31.5 * math.sin(t))}"
        for t in (2 * math.pi * i / 120 for i in range(120)))
    return svg(64, 64, f'<circle cx="32" cy="32" r="30.25" fill="none" stroke="#1a150a" stroke-width="3.5"/>'
                       f'<path d="{reeds}" stroke="{GOLD}" stroke-opacity=".8" stroke-width=".7"/>'
                       f'<circle cx="32" cy="32" r="28.6" fill="none" stroke="{HI}" stroke-opacity=".75" stroke-width=".7"/>'
                       f'<circle cx="32" cy="32" r="31.7" fill="none" stroke="{GOLD}" stroke-opacity=".6" stroke-width=".5"/>')

FILES = {
    "seal.svg": seal(GOLD, 1),                 # specimen / identity use
    "seal-watermark.svg": seal(GOLD, .085),    # page backdrop: engraved, never glowing
    "intaglio.svg": intaglio(.075),
    "intaglio-dense.svg": intaglio(.16),
    "corner-tl.svg": corner(0), "corner-tr.svg": corner(90),
    "corner-br.svg": corner(180), "corner-bl.svg": corner(270),
    "band.svg": band(), "band-quiet.svg": band(.3, .14), "pip.svg": pip(),
    "node.svg": node(), "bezel.svg": bezel(),
}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, text in FILES.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print(f"textures/genesis/{name:20} {len(text.encode()):7} bytes")

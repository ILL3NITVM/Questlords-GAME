#!/usr/bin/env python3
"""Masters every coin mark onto the same geometry, and audits it.

    python3 site/tools/coin-master.py           # master, then audit
    python3 site/tools/coin-master.py --check   # audit only (fails on any drift)

Every coin becomes a 256x256 RGBA image whose disc is centred exactly on the canvas centre
with a 127px radius and an anti-aliased, fully transparent outside. The coin's own artwork (the glyph
and its official placement and tilt, e.g. the Bitcoin mark's 14 degree lean) is never moved: only the
disc is found, re-centred and re-cut. Mastering an already-mastered coin is a no-op within 0.5px.
"""
import math, os, sys
from PIL import Image, ImageChops, ImageDraw

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
COINS = ["bitcoin", "dogecoin", "xrp", "litecoin"]
SIZE, R = 256, 127.0  # output canvas and disc radius; 1px clear margin all round
SS = 8                # mask supersampling for the anti-aliased edge

def disc_geometry(im):
    """Centre and inscribed radius of the coloured disc.

    The disc is every opaque pixel brighter than a dark matte or shadow. Its outer edge is sampled at
    720 angles and fitted with a least-squares circle; the radius returned is the fit minus the deepest
    inward deviation, so the cut circle lies wholly inside the artwork even when a source disc is
    slightly out of round (the supplied Bitcoin disc deviates by about 4px on a 213px radius)."""
    px, (w, h) = im.load(), im.size
    inside = [[px[x, y][3] >= 128 and max(px[x, y][:3]) > 90 for x in range(w)] for y in range(h)]
    edge = [(x, y) for y in range(1, h - 1) for x in range(1, w - 1) if inside[y][x] and not (
        inside[y - 1][x] and inside[y + 1][x] and inside[y][x - 1] and inside[y][x + 1])]
    cx0 = sum(x for x, _ in edge) / len(edge); cy0 = sum(y for _, y in edge) / len(edge)
    outer = {}
    for x, y in edge:  # keep the outermost edge point per half-degree: the rim, not the glyph
        k = int((math.atan2(y - cy0, x - cx0) + math.pi) / (2 * math.pi) * 720) % 720
        r = math.hypot(x - cx0, y - cy0)
        if r > outer.get(k, (0,))[0]:
            outer[k] = (r, x + .5, y + .5)
    pts = [(x, y) for _, x, y in outer.values()]
    # Kasa fit: x^2 + y^2 = a*x + b*y + c
    n = len(pts); z = [x * x + y * y for x, y in pts]
    A = [[sum(x * x for x, _ in pts), sum(x * y for x, y in pts), sum(x for x, _ in pts)],
         [sum(x * y for x, y in pts), sum(y * y for _, y in pts), sum(y for _, y in pts)],
         [sum(x for x, _ in pts), sum(y for _, y in pts), n]]
    rhs = [sum(x * q for (x, _), q in zip(pts, z)), sum(y * q for (_, y), q in zip(pts, z)), sum(z)]
    M = [row[:] + [v] for row, v in zip(A, rhs)]
    for i in range(3):
        piv = max(range(i, 3), key=lambda k: abs(M[k][i])); M[i], M[piv] = M[piv], M[i]
        for k in range(3):
            if k != i:
                f = M[k][i] / M[i][i]; M[k] = [a - f * c for a, c in zip(M[k], M[i])]
    a, b, c = (M[i][3] / M[i][i] for i in range(3))
    cx, cy = a / 2, b / 2
    r = math.sqrt(c + cx * cx + cy * cy)
    return cx, cy, r + min(math.hypot(x - cx, y - cy) - r for x, y in pts)

def mask():
    m = Image.new("L", (SIZE * SS, SIZE * SS), 0)
    c, r = SIZE * SS / 2, R * SS
    ImageDraw.Draw(m).ellipse((c - r, c - r, c + r - 1, c + r - 1), fill=255)  # PIL boxes include the end pixel
    return m.resize((SIZE, SIZE), Image.LANCZOS)

def master(name):
    path = os.path.join(ASSETS, name + ".png")
    im = Image.open(path).convert("RGBA")
    cx, cy, rad = disc_geometry(im)
    # Map the source disc, inset by a hairline so its dark anti-aliasing fringe is never carried over,
    # onto radius R; `half` is the source distance that lands on the canvas edge.
    half = (rad - 0.75) * (SIZE / 2) / R
    out = im.transform((SIZE, SIZE), Image.EXTENT, (cx - half, cy - half, cx + half, cy + half), Image.BICUBIC)
    out.putalpha(ImageChops.multiply(out.getchannel("A").point(lambda v: 255), mask()))
    out.save(path, optimize=True)

def audit(name):
    im = Image.open(os.path.join(ASSETS, name + ".png")).convert("RGBA")
    a = im.getchannel("A")
    assert im.size == (SIZE, SIZE), (name, im.size)
    for corner in [(0, 0), (SIZE - 1, 0), (0, SIZE - 1), (SIZE - 1, SIZE - 1), (2, 2), (SIZE - 3, SIZE - 3)]:
        assert a.getpixel(corner) == 0, (name, "corner not transparent", corner)
    # alpha-weighted centroid and area of the disc
    px, sx, sy, s = a.load(), 0.0, 0.0, 0.0
    for y in range(SIZE):
        for x in range(SIZE):
            v = px[x, y] / 255
            if v:
                sx += v * (x + .5); sy += v * (y + .5); s += v
    cx, cy, r = sx / s, sy / s, math.sqrt(s / math.pi)
    ok = abs(cx - SIZE / 2) < .05 and abs(cy - SIZE / 2) < .05 and abs(r - R) < .25
    print(f"{name:9} centre ({cx:.3f}, {cy:.3f})  radius {r:.3f}  {'OK' if ok else 'DRIFT'}")
    return ok

if __name__ == "__main__":
    if "--check" not in sys.argv:
        for n in COINS:
            master(n)
    if not all([audit(n) for n in COINS]):
        raise SystemExit("coin geometry drift")

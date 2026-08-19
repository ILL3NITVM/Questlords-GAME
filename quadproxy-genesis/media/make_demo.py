#!/usr/bin/env python3
"""
Generate the doctor demo GIF: silent failure -> diagnosis -> fix -> verified.

Honesty constraints, deliberately enforced:
  * every output line matches what qwebengine-proxy-doctor actually prints
  * all addresses are RFC5737/RFC2606 documentation placeholders, never a real proxy
  * nothing is claimed that the tool does not do
"""
from PIL import Image, ImageDraw, ImageFont

W, H = 860, 470
BG, FG, DIM = "#0d1117", "#c9d1d9", "#7d8590"
GREEN, RED, CYAN, YELLOW = "#3fb950", "#f85149", "#58a6ff", "#d29922"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
F = ImageFont.truetype(MONO, 14)
FB = ImageFont.truetype(BOLD, 14)
LH, PAD, TOP = 20, 18, 44

PROXY = "http://user:pass@proxy.example.com:8080"

# (text, colour, bold, frames_to_hold_after)
SCRIPT = [
    (f"$ python browser.py --proxy {PROXY}", CYAN, True, 8),
    ("  window opens. page renders. no errors.", DIM, False, 10),
    ("  ...but is it actually using the proxy?", DIM, False, 12),
    ("", FG, False, 2),
    (f"$ qwebengine-proxy-doctor --proxy {PROXY}", CYAN, True, 6),
    (" [ok]  proxy reachable      CONNECT example.com:443 -> 200 (186ms)", GREEN, False, 4),
    (" [ok]  credentials sent     anonymous rejected (407), auth accepted", GREEN, False, 4),
    (" [!!]  egress routing       proxied IP == direct IP (203.0.113.7).", RED, True, 3),
    ("                            Traffic is LEAKING past the proxy.", RED, False, 4),
    (" [!!]  qt applicationProxy  applicationProxy() is NoProxy.", RED, True, 3),
    ("                            QWebEngineView will go DIRECT.", RED, False, 6),
    (" VERDICT: 2 FAILURE(S) - your proxy is NOT working.", RED, True, 16),
    ("", FG, False, 2),
    ("$ # two lines fix it:", CYAN, True, 6),
    ("+ QNetworkProxy.setApplicationProxy(p)   # BEFORE QApplication", YELLOW, False, 6),
    ("+ page.proxyAuthenticationRequired.connect(on_auth)", YELLOW, False, 10),
    ("", FG, False, 2),
    (f"$ qwebengine-proxy-doctor --proxy {PROXY}", CYAN, True, 6),
    (" [ok]  proxy reachable      CONNECT example.com:443 -> 200 (191ms)", GREEN, False, 3),
    (" [ok]  credentials sent     anonymous rejected (407), auth accepted", GREEN, False, 3),
    (" [ok]  egress routing       direct=203.0.113.7 -> proxied=198.51.100.42", GREEN, True, 4),
    (" [ok]  qt applicationProxy  proxy.example.com:8080 user=set", GREEN, False, 5),
    (" VERDICT: proxy verified. Traffic is authenticated and routed.", GREEN, True, 40),
]


def chrome(d):
    """Window frame: title bar, traffic lights, caption."""
    d.rectangle([0, 0, W, H], fill=BG)
    d.rectangle([0, 0, W, 30], fill="#161b22")
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        d.ellipse([PAD + i * 20, 11, PAD + i * 20 + 10, 21], fill=c)
    d.text((W // 2 - 96, 8), "qwebengine-proxy-doctor", font=F, fill=DIM)


MAX_LINES = (H - TOP - LH) // LH


def frame(visible, pending=None, chars=0):
    """Render one frame from the visible window, optionally mid-typing `pending`."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    chrome(d)
    y = TOP
    for text, col, bold, _ in visible:
        d.text((PAD, y), text, font=FB if bold else F, fill=col)
        y += LH
    if pending is not None:
        text, col, bold, _ = pending
        shown = text[:chars]
        d.text((PAD, y), shown, font=FB if bold else F, fill=col)
        cx = PAD + int(d.textlength(shown, font=FB if bold else F))
        d.rectangle([cx + 1, y + 2, cx + 8, y + 16], fill=DIM)
    return img


def build(path="doctor-demo.gif"):
    frames, visible = [], []
    for entry in SCRIPT:
        text, _, _, hold = entry
        # Type out command lines character-wise; other lines simply appear.
        if text.startswith("$") and len(text) > 4:
            step = max(1, len(text) // 14)
            for c in range(0, len(text) + 1, step):
                frames.append(frame(visible, pending=entry, chars=c))
        visible.append(entry)
        # Scroll once the pane is full.
        while len(visible) > MAX_LINES:
            visible.pop(0)
        frames.extend([frame(visible)] * (hold + 1))
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=90, loop=0, optimize=True)
    return path, len(frames)


if __name__ == "__main__":
    p, n = build()
    print(f"wrote {p} ({n} frames)")

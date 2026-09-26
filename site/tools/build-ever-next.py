#!/usr/bin/env python3
"""Builds EVER NEXT, QuadCOM's everlasting improvement feed.

    python3 site/tools/build-ever-next.py        (then build-domain.py, which stamps metadata last)

Items are composed, never hand-listed:  surface x aspect x move x depth x cycle.
  * An aspect applies to a surface only when they share a tag (tools/ever_next_axes.py), so every
    combination is meaningful.
  * Every move has five depths (OBSERVE, REFINE, SYSTEMATISE, PROVE, SUSTAIN): there is always a
    better version of the same improvement.
  * Every aspect has escalating bars, one per cycle. After the last cycle the feed begins the next
    PASS with every measurement re-taken, so the feed never ends.
Self-feedback: this script measures the repository itself (asset weights, sub-legible desk type,
!important counts, infinite animations, QA coverage, open review findings) and writes each finding
as evidence on the surface and aspect it concerns. Measured items rank first in the feed.

Outputs: ever-next/axes.json (the data the page composes items from), ever-next/index.html, and
EVER_NEXT_SUMMARY.txt. The page script ever-next/core.js composes items; tools/qa/ever-next.mjs
checks that its count matches the total computed here.
"""
import html, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from ever_next_axes import LAYERS, SURFACES, ASPECTS, DEPTHS

ROOT = os.path.join(os.path.dirname(__file__), "..")
TAGS = {"route", "text", "touch", "data", "visual", "motion", "asset", "system"}

# ── validation ─────────────────────────────────────────────────────────────────────────────────
sid = [s[0] for s in SURFACES]; aid = [a[0] for a in ASPECTS]
assert len(set(sid)) == len(sid) and len(set(aid)) == len(aid), "duplicate ids"
for s in SURFACES:
    assert set(s[3].split()) <= TAGS and 0 <= s[2] < len(LAYERS), s
for a in ASPECTS:
    assert set(a[2].split()) <= TAGS, a
    assert len(a[3]) == 6 and all("{s}" in m for m in a[3]), (a[0], "needs six moves, each naming {s}")
    assert 1 <= len(a[4]) <= 4, (a[0], "bars")
assert len(DEPTHS) == 5

def applies(surface, aspect):
    return bool(set(surface[3].split()) & set(aspect[2].split()))

pairs = [(i, j) for i, s in enumerate(SURFACES) for j, a in enumerate(ASPECTS) if applies(s, a)]
per_pass = sum(6 * len(DEPTHS) * len(ASPECTS[j][4]) for _, j in pairs)

# ── self-feedback: measure the repository ─────────────────────────────────────────────────────
def rd(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()

def size(p):
    return os.path.getsize(os.path.join(ROOT, p))

evidence = []
def ev(surface, aspect, severity, text, source):
    assert surface in sid and aspect in aid, (surface, aspect)
    s, a = SURFACES[sid.index(surface)], ASPECTS[aid.index(aspect)]
    assert applies(s, a), f"evidence on a pair that does not apply: {surface}/{aspect}"
    evidence.append({"s": surface, "a": aspect, "sev": severity, "text": text, "src": source})

KB = lambda b: f"{b / 1024:.0f} KB"
# Asset weights against a budget per kind.
budgets = [("seal", ["assets/textures/genesis/seal.svg"], 120 * 1024),
           ("regalia", ["assets/textures/regalia/mandala.png", "assets/textures/regalia/kaleido-tile.png", "assets/textures/regalia/starburst.png"], 100 * 1024),
           ("aurum", ["assets/textures/aurum-brushed.png", "assets/textures/obsidian-grain.png"], 60 * 1024),
           ("logo", ["assets/quadcom-official-logo.png", "assets/quadcom-logo-640.png", "assets/quadcom-logo-96.png"], 300 * 1024),
           ("coins", ["assets/bitcoin.png", "assets/dogecoin.png", "assets/xrp.png", "assets/litecoin.png"], 120 * 1024),
           ("splash", ["assets/splash-iphone13-portrait.png", "assets/splash-iphone13-landscape.png"], 400 * 1024),
           ("ogcard", ["assets/og-card.jpg"], 120 * 1024)]
for surf, files, budget in budgets:
    have = [f for f in files if os.path.exists(os.path.join(ROOT, f))]
    total = sum(size(f) for f in have)
    if total > budget:
        big = max(have, key=size)
        ev(surf, "weight", 2 if total > 2 * budget else 1,
           f"{KB(total)} across {len(have)} file(s), over the {KB(budget)} budget; largest is {big.split('/')[-1]} at {KB(size(big))}.",
           "file sizes")

desk = rd("desk/bitcoin/index.html")
m = re.search(r'<style id="quadcom-v51-iphone13-polish">(.*?)</style>', desk, re.S)
if m:
    tiny = sorted({float(v) for v in re.findall(r"font-size:([0-9.]+)px", m.group(1)) if float(v) < 7})
    if tiny:
        ev("deskport", "type", 2, f"The iPhone portrait rules set {len(tiny)} font sizes below 7px ({', '.join(f'{v:g}' for v in tiny)}px).",
           "desk CSS, iPhone 13 rules")
imp = desk.count("!important")
ev("deskport", "consistency", 1, f"The desk source carries {imp} !important declarations across {desk.count('<style')} style blocks.", "desk source")
inf = sorted(set(re.findall(r"animation:([a-zA-Z0-9_-]+)[^;}]*infinite", desk)))
if inf:
    ev("cmdbar", "motion", 2, f"Infinite animations still run under REGALIA and AURUM: {', '.join(inf)}. GENESIS holds them still.", "desk CSS")
css = rd("qc-site.css")
glyph_rules = len(re.findall(r"\.qc-glyph\{", css))
ev("panel", "consistency", 1 if css.count("!important") < 40 else 2,
   f"qc-site.css has {css.count('!important')} !important declarations and {glyph_rules} separate .qc-glyph rules that override one another.", "site CSS")
w = len(desk.encode()) + size("desk/bitcoin/glimmer.js") + size("desk/bitcoin/glimmer-vision.js")
ev("deskport", "weight", 2, f"A desk costs {KB(w)} of HTML and scripts before textures (the page itself is {KB(len(desk.encode()))}).", "file sizes")

# QA coverage: which surfaces a QA script exercises (tools/qa).
covered = {
    "crawl.mjs": ["home", "hub", "learn", "how", "identity", "datapage", "glossary", "catalogpage", "notfound", "offline", "evernext"],
    "components.mjs": ["tabbar", "more", "segment", "toast", "progress", "totop", "header"],
    "glossary.mjs": ["glossary", "search", "azindex", "anchors"],
    "desks.mjs": ["deskbar", "deskport", "deskland", "storage", "quote", "chart", "singular"],
    "live-feed.mjs": ["feeds", "quote", "pricefmt"],
    "ever-next.mjs": ["evernext"],
    "offline.mjs": ["offline", "sw"],
}
qa_dir = os.path.join(ROOT, "tools", "qa")
have_qa = {f for f in os.listdir(qa_dir)} if os.path.isdir(qa_dir) else set()
cov = {s for f, ss in covered.items() if f in have_qa for s in ss}
for s in SURFACES:
    if s[0] not in cov and set(s[3].split()) & {"touch", "data"}:
        ev(s[0], "tests", 1, "No QA script exercises it yet.", "tools/qa coverage map")

# Open findings from the release reviews (sourced, still true in this build).
ev("storagecard", "prov", 1, "Counts localStorage keys only; IndexedDB and OPFS usage per desk is not included.", "review, build 56")
ev("pricefmt", "precision", 1, "The worker control view stores price in whole cents, too coarse for DOGE (nothing reads it yet).", "review, build 56")
ev("fleetbal", "empty", 1, "A fresh desk shows starting balances as if they were results; there is no 'no trades yet' state.", "desk screenshots, build 57")
ev("fundcells", "precision", 1, "Zero money values mix formats ($0 beside $0.0).", "desk screenshots, build 57")
ev("loss", "precision", 1, "GEOMETRIC GROWTH shows 0.000%/tick for small real moves: fixed decimals round them away.", "desk screenshots, build 57")
ev("chart", "empty", 1, "Before history arrives the chart field is blank rather than saying it is waiting for observed data.", "desk screenshots, build 57")

evidence.sort(key=lambda e: (-e["sev"], sid.index(e["s"]), aid.index(e["a"])))

# ── outputs ────────────────────────────────────────────────────────────────────────────────────
axes = {"layers": LAYERS,
        "surfaces": [{"id": s[0], "name": s[1], "layer": s[2], "tags": s[3].split()} for s in SURFACES],
        "aspects": [{"id": a[0], "name": a[1], "needs": a[2].split(), "moves": a[3], "bars": a[4]} for a in ASPECTS],
        "depths": [{"name": d[0], "text": d[1]} for d in DEPTHS],
        "perPass": per_pass, "pairs": len(pairs), "evidence": evidence}
os.makedirs(os.path.join(ROOT, "ever-next"), exist_ok=True)
with open(os.path.join(ROOT, "ever-next", "axes.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(axes, fh, ensure_ascii=False, separators=(",", ":"))

def item_text(si, ai, move, depth):
    return ASPECTS[ai][3][move].replace("{s}", SURFACES[si][1]) + " " + DEPTHS[depth][1]

# Static fallback: the measured items at their first depth, so the page reads without JavaScript.
static = []
for e in evidence:
    si, ai = sid.index(e["s"]), aid.index(e["a"])
    static.append(f'<li class="qc-en-item" data-measured><div class="qc-en-meta"><span class="qc-en-id">P1 · {e["s"]}.{e["a"]}.m1.d1.c1</span>'
                  f'<span class="qc-en-depth">OBSERVE</span><span class="qc-en-sev s{e["sev"]}">MEASURED</span></div>'
                  f'<p class="qc-en-text">{html.escape(item_text(si, ai, 0, 0))}</p>'
                  f'<p class="qc-en-ev"><b>{html.escape(ASPECTS[ai][1])} · {html.escape(SURFACES[si][1])}:</b> {html.escape(e["text"])} <small>({html.escape(e["src"])})</small></p></li>')

src = rd("data/index.html")
head, rest = src.split('<main class="qc-main" id="main" data-glossary-links>', 1)
tail = rest.split("</main>", 1)[1]
title, desc = "EVER NEXT", "QuadCOM's everlasting improvement feed: every surface, every quality, always a better version."
head = re.sub(r"<!--qc-meta-->.*?<!--/qc-meta-->", "", head, flags=re.S)
head = head.replace("<title>ABOUT THE DATA · QuadCOM</title>", f"<title>{title} · QuadCOM</title>")
head = re.sub(r'(<meta name="description" content=")[^"]*', lambda m: m.group(1) + desc, head)
head = head.replace('<a href="/data/" aria-current="page">DATA</a>', '<a href="/data/" >DATA</a>')
tail = tail.replace(' aria-current="page"', "").replace(" is-active", "")
assert "aria-current" not in head + tail and "ABOUT THE DATA" not in head
head = head.replace("</head>", '<link rel="preload" href="/ever-next/axes.json?v=58" as="fetch" crossorigin></head>')
tail = tail.replace('<script src="/qc-site.js?v=58"></script>', '<script src="/qc-site.js?v=58"></script><script src="/ever-next/core.js?v=58"></script><script src="/ever-next/feed.js?v=58"></script>')
assert "/ever-next/feed.js" in tail, "site script tag not found (build version changed?)"

n_moves = sum(len(a[3]) for a in ASPECTS)
opt = lambda items: "".join(f'<option value="{v}">{html.escape(t)}</option>' for v, t in items)
main = f'''<main class="qc-main" id="main"><div class="qc-kicker">SELF-FEEDBACK FEED</div><h1 class="qc-title">{title}</h1>
<p class="qc-sub">Every surface of QuadCOM, every quality it can have, and always a better version. Items are composed from the axes below, measured against the site itself, and never run out.</p><div class="qc-rule"></div>
<div class="qc-grid">
<section class="qc-panel qc-span12" id="how-it-grows"><h2>HOW IT GROWS<a class="qc-anchor" href="#how-it-grows" aria-label="Link to HOW IT GROWS">#</a></h2>
<div class="qc-metric"><span>SURFACES</span><b>{len(SURFACES)} across {len(LAYERS)} layers</b></div>
<div class="qc-metric"><span>ASPECTS</span><b>{len(ASPECTS)}, each with 6 moves ({n_moves})</b></div>
<div class="qc-metric"><span>DEPTHS PER MOVE</span><b>{len(DEPTHS)}: {" → ".join(d[0] for d in DEPTHS)}</b></div>
<div class="qc-metric"><span>VALID PAIRINGS</span><b>{len(pairs)} surface × aspect</b></div>
<div class="qc-metric"><span>ITEMS PER PASS</span><b>{per_pass:,}</b></div>
<div class="qc-metric"><span>MEASURED SIGNALS</span><b>{len(evidence)} from this build</b></div>
<div class="qc-metric"><span>PASSES</span><b>ENDLESS: each pass re-measures and starts again</b></div>
<p>Items are generated candidates, not claims: an aspect pairs only with surfaces it can apply to, each move deepens through five stages, and each cycle raises the bar. Items marked MEASURED come from this build&#x27;s own files and reviews. Your DONE, LATER and SKIP marks stay in this browser.</p></section>
<section class="qc-panel qc-span12" id="feed"><h2>THE FEED<a class="qc-anchor" href="#feed" aria-label="Link to THE FEED">#</a></h2>
<div class="qc-en-controls" data-en-controls hidden>
<div class="qc-seg qc-en-modes" role="radiogroup" aria-label="Mode">{"".join(f'<button type="button" role="radio" aria-checked="{"true" if m == "feed" else "false"}" data-mode="{m}">{m.upper()}</button>' for m in ("feed", "today", "sweep", "polish", "compose"))}</div>
<p class="qc-en-help" aria-live="polite"></p>
<div class="qc-en-facets">
<label>LAYER<select data-f="layer"><option value="">ALL</option>{opt(enumerate(LAYERS))}</select></label>
<label>SURFACE<select data-f="surface"><option value="">ALL</option>{opt((s[0], s[1]) for s in SURFACES)}</select></label>
<label>ASPECT<select data-f="aspect"><option value="">ALL</option>{opt((a[0], a[1]) for a in ASPECTS)}</select></label>
<label>DEPTH<select data-f="depth"><option value="">ALL</option>{opt(enumerate(d[0] for d in DEPTHS))}</select></label>
<label>CYCLE<select data-f="cycle"><option value="">ALL</option>{opt((c, f"CYCLE {c + 1}") for c in range(max(len(a[4]) for a in ASPECTS)))}</select></label>
<label>STATUS<select data-f="status"><option value="">ALL</option><option value="measured">MEASURED</option><option value="open">NOT MARKED</option><option value="done">MY DONE</option><option value="later">MY LATER</option><option value="skip">MY SKIP</option></select></label>
</div>
<div class="qc-en-row"><input class="qc-search" type="search" data-f="q" placeholder="SEARCH ITEMS" aria-label="Search items">
<div class="qc-en-compose" hidden><label>SEED<input type="text" data-f="seed" inputmode="numeric" maxlength="9" aria-label="Compose seed"></label><label>SIZE<select data-f="size"><option>3</option><option selected>5</option><option>8</option><option>13</option></select></label><button type="button" class="qc-btn" data-shuffle>SHUFFLE</button></div>
<button type="button" class="qc-btn" data-reset>RESET</button><button type="button" class="qc-btn" data-export>EXPORT MY MARKS</button></div>
<p class="qc-en-count" aria-live="polite"></p></div>
<ol class="qc-en-list" data-en-list>{"".join(static)}</ol>
<button type="button" class="qc-btn qc-en-more" data-more hidden>SHOW MORE</button>
<noscript><p>The full feed composes its items in your browser. Without JavaScript, the measured items from this build are listed above.</p></noscript>
</section></div>
<nav class="qc-pager" aria-label="Pages"><a rel="prev" href="/catalog/">← CATALOG</a><a rel="next" href="/glossary/">GLOSSARY →</a></nav></main>'''
with open(os.path.join(ROOT, "ever-next", "index.html"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write(head + main + tail)

lines = ["QUADCOM ❖ EVER NEXT — THE EVERLASTING IMPROVEMENT FEED", "",
         f"{len(SURFACES)} surfaces · {len(ASPECTS)} aspects · {n_moves} moves · {len(DEPTHS)} depths · escalating bars per aspect",
         f"{len(pairs)} valid surface × aspect pairings · {per_pass:,} items per pass · passes never end", "",
         "Every item is: <move on a surface> + <depth>, judged against the aspect's bar for its cycle.",
         "Browse, filter, mix and mark them at /ever-next/. This file lists the axes and this build's measured signals.", "",
         "MEASURED SIGNALS (self-feedback from this build)", "────────────────────────────────────────────────"]
for e in evidence:
    lines.append(f"[{'HIGH' if e['sev'] == 2 else 'NOTE'}] {e['s']}.{e['a']}: {e['text']} ({e['src']})")
lines += ["", "ASPECTS, MOVES AND BARS", "───────────────────────"]
for a in ASPECTS:
    lines.append(f"{a[1]}  (applies to: {', '.join(a[2].split())})")
    lines += [f"  {i + 1}. {m.replace('{s}', '<surface>')}" for i, m in enumerate(a[3])]
    lines += [f"  bar, cycle {c + 1}: {b}" for c, b in enumerate(a[4])]
lines += ["", "DEPTHS", "──────"] + [f"{i + 1}. {d[0]}: {d[1]}" for i, d in enumerate(DEPTHS)]
lines += ["", "SURFACES", "────────"]
for li, layer in enumerate(LAYERS):
    lines.append(f"{layer}: " + "; ".join(s[1] for s in SURFACES if s[2] == li))
with open(os.path.join(ROOT, "EVER_NEXT_SUMMARY.txt"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines) + "\n")
print(f"{len(SURFACES)} surfaces · {len(ASPECTS)} aspects · {len(pairs)} pairings · {per_pass:,} items per pass · {len(evidence)} measured signals")

#!/usr/bin/env python3
"""Builds EVER NEXT, QuadCOM's everlasting improvement feed.

    node tools/qa/measure-runtime.mjs 8192     (optional, needs the site served: refreshes ever-next/runtime.json)
    python3 site/tools/build-ever-next.py      (then build-domain.py, which stamps metadata last)

Items are composed, never hand-listed:  surface x aspect x move x depth x cycle.
  * Applicability is explicit (tools/ever_next_axes.py): surface kinds and traits, plus per-aspect includes and
    excludes. The exact pairings are written to axes.json, so the page never re-derives them.
  * Every move is tagged by nature (audit, fix, test, human) and each nature has its own five depths, so the depth
    sentence always fits the move: there is always a better next version of the same improvement.
  * Every aspect has escalating bars, one per cycle. After the last item the feed walks the axes again as the next
    pass. Measurements are taken when this script runs, never in the browser.
Self-feedback: evidence comes from this repository (file sizes, source counts, the QA coverage map, sourced review
findings) and from the runtime audit tools/qa/measure-runtime.mjs (what actually animates and what actually renders
below 7px). Each finding names the specific moves it concerns; those items rank first in the feed.

Outputs: ever-next/axes.json, ever-next/index.html, EVER_NEXT_SUMMARY.txt. ever-next/core.js composes items;
tools/qa/ever-next.mjs checks that its count matches the total computed here.
"""
import html, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from ever_next_axes import LAYERS, KINDS, TRAITS, SURFACES, ASPECTS, DEPTHS, DEPTH_TEXT, applies, move_parts, move_mask

ROOT = os.path.join(os.path.dirname(__file__), "..")

# ── validation ─────────────────────────────────────────────────────────────────────────────────
sid = [s[0] for s in SURFACES]; aid = [a[0] for a in ASPECTS]
assert len(set(sid)) == len(sid) and len(set(aid)) == len(aid), "duplicate ids"
for s in SURFACES:
    assert s[3] in KINDS and set(s[4].split()) <= TRAITS and 0 <= s[2] < len(LAYERS), s
for a in ASPECTS:
    r = a[2]
    assert set(r["kinds"].split()) <= KINDS and set(r.get("traits", "").split()) <= TRAITS, a[0]
    assert set(r.get("include", "").split()) <= set(sid) and set(r.get("exclude", "").split()) <= set(sid), (a[0], "unknown surface")
    assert len(a[3]) == 6, (a[0], "six moves")
    for m in a[3]:
        nature, cond, text = move_parts(m)
        assert nature in "afthw" and text.count("{s}") == 1, (a[0], m)
        assert cond <= KINDS | TRAITS | set(sid), (a[0], m, "unknown condition word")
        # The surface is always the object: "{s}" never starts a clause, so no verb has to agree with it.
        assert not re.search(r"(^|[.:;] )\{s\}", text), (a[0], m)
        # ...and no pronoun after it refers back to it ("it", "its" would disagree with plural surface names).
        # These pronouns refer to another noun in the same move and are known to be correct:
        ok = ("what it is", "its label", "its duration", "its decimals", "that it reads", "record it with", "script that checks it")
        rest = text
        for phrase in ok:
            rest = rest.replace(phrase, "")
        assert not re.search(r"\{s\}.*\b(it|its|itself)\b", rest), (a[0], m, "pronoun may refer to the surface")
    assert 1 <= len(a[4]) <= 4, (a[0], "bars")
assert all(len(v) == len(DEPTHS) for v in DEPTH_TEXT.values())

pairs = [(i, j, move_mask(s, a)) for i, s in enumerate(SURFACES) for j, a in enumerate(ASPECTS) if applies(s, a)]
assert all(mask for _, _, mask in pairs), "a pairing with no applicable move"
per_pass = sum(bin(mask).count("1") * len(DEPTHS) * len(ASPECTS[j][4]) for _, j, mask in pairs)

# ── self-feedback: measure the repository ─────────────────────────────────────────────────────
def rd(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()

def size(p):
    return os.path.getsize(os.path.join(ROOT, p))

evidence = []
def ev(surface, aspect, moves, severity, text, source):
    """One finding on the given moves (0-based) of a surface x aspect pairing that applies."""
    s, a = SURFACES[sid.index(surface)], ASPECTS[aid.index(aspect)]
    assert applies(s, a), f"evidence on a pairing that does not apply: {surface}/{aspect}"
    assert moves and all(0 <= m < 6 and move_mask(s, a) >> m & 1 for m in moves), (surface, aspect, moves, "move does not apply")
    evidence.append({"s": surface, "a": aspect, "m": sorted(moves), "sev": severity, "text": text, "src": source})

KB = lambda b: f"{b / 1024:.0f} KB"
budgets = [("seal", ["assets/textures/genesis/seal.svg"], 120),
           ("regalia", ["assets/textures/regalia/mandala.png", "assets/textures/regalia/kaleido-tile.png", "assets/textures/regalia/starburst.png"], 100),
           ("aurum", ["assets/textures/aurum-brushed.png", "assets/textures/obsidian-grain.png"], 60),
           ("logo", ["assets/quadcom-official-logo.png", "assets/quadcom-logo-640.png", "assets/quadcom-logo-96.png"], 300),
           ("coins", ["assets/bitcoin.png", "assets/dogecoin.png", "assets/xrp.png", "assets/litecoin.png"], 120),
           ("splash", ["assets/splash-iphone13-portrait.png", "assets/splash-iphone13-landscape.png"], 400),
           ("ogcard", ["assets/og-card.jpg"], 120)]
for surf, files, budget_kb in budgets:
    have = [f for f in files if os.path.exists(os.path.join(ROOT, f))]
    total = sum(size(f) for f in have)
    if total > budget_kb * 1024:
        big = max(have, key=size)
        ev(surf, "weight", [1, 2], 2 if total > 2 * budget_kb * 1024 else 1,
           f"{KB(total)} across {len(have)} file(s), over its {budget_kb} KB budget; the largest is {big.split('/')[-1]} at {KB(size(big))}.",
           "file sizes")

desk = rd("desk/bitcoin/index.html")
ev("deskport", "consistency", [5], 1, f"The desk source carries {desk.count('!important')} !important declarations across {desk.count('<style')} style blocks.", "desk source")
css = rd("qc-site.css")
ev("panel", "consistency", [4, 5], 1,
   f"qc-site.css has {css.count('!important')} !important declarations and {len(re.findall(r'[.]qc-glyph[{]', css))} separate .qc-glyph rules that override one another.",
   "site CSS")
w = len(desk.encode()) + size("desk/bitcoin/glimmer.js") + size("desk/bitcoin/glimmer-vision.js")
ev("deskport", "weight", [0, 1], 2, f"A desk costs {KB(w)} of HTML and scripts before textures (the page itself is {KB(len(desk.encode()))}).", "file sizes")

# Runtime audit (tools/qa/measure-runtime.mjs): measured in a browser, not grepped from source.
rt_path = os.path.join(ROOT, "ever-next", "runtime.json")
if os.path.exists(rt_path):
    rt = json.load(open(rt_path, encoding="utf-8"))
    groups = {}
    for k, names in rt["animations"].items():
        skin, vp = k.split(" ")
        groups.setdefault(tuple(names), []).append((skin, vp))
    running = {k: v for k, v in groups.items() if k}
    if running:
        parts = []
        for names, where in sorted(running.items()):
            skins = sorted({s.upper() for s, _ in where}); vps = sorted({v for _, v in where})
            parts.append(f"{', '.join(names)} under {', '.join(skins)} at {' and '.join(vps)}")
        still = sorted({s.upper() for names, where in groups.items() if not names for s, _ in where})
        ev("cmdbar", "motion", [1], 2, "Infinite animations running, measured in a browser: " + "; ".join(parts) + "."
           + (f" None run under {', '.join(still)}." if still else ""), "runtime audit, tools/qa/measure-runtime.mjs")
    t = rt.get("tinyText", {})
    if t.get("390x844", {}).get("count"):
        m, d = t["390x844"], t.get("1280x800", {})
        ev("deskport", "type", [1], 2, f"{m['count']} visible text elements render below 7px at 390×844 (smallest {m['minPx']}px)"
           + (f"; {d['count']} at 1280×800" if d.get("count") else "") + ", measured under GENESIS.", "runtime audit, tools/qa/measure-runtime.mjs")

# QA coverage: what each script actually asserts. The build fails if a listed script does not exist.
ASSERTS = {  # behaviour asserted
    "crawl.mjs": ["home", "hub", "learn", "how", "identity", "datapage", "glossary", "catalogpage", "evernext", "notfound", "offline"],
    "components.mjs": ["header", "tabbar", "more", "segment", "toast", "progress"],
    "glossary.mjs": ["glossary", "search", "azindex", "anchors", "totop"],
    "desks.mjs": ["deskbar", "quote", "singular", "storage", "deskport", "deskland", "deskgen"],
    "live-feed.mjs": ["feeds", "quote", "pricefmt", "chart"],
    "ever-next.mjs": ["evernext", "evergen"],
    "offline.mjs": ["offline", "sw"],
}
LAYOUT = {"desk-views.mjs": ["cmdbar", "chart", "axis", "fleetbal", "bullbear", "toppico", "fundcells", "micro", "loss", "leader", "wall", "book", "horizons", "vision"]}
qa_dir = os.path.join(ROOT, "tools", "qa")
for f in list(ASSERTS) + list(LAYOUT):
    assert os.path.exists(os.path.join(qa_dir, f)), f"coverage map names a missing QA script: {f}"
asserted = {s for ss in ASSERTS.values() for s in ss}
layout_only = {s for ss in LAYOUT.values() for s in ss} - asserted
for s in SURFACES:
    if s[0] in asserted or not applies(s, ASPECTS[aid.index("tests")]):
        continue
    if s[0] in layout_only:
        text = "Only desk-views.mjs reaches it: it audits layout (overflow and collisions in four views, both orientations) but no script asserts its values."
    elif s[3] == "ui" and s[0] != "glimmersheet":
        text = "Only the crawl's page-wide checks reach it (errors, text size, contrast); no script asserts its behaviour."
    elif s[0] == "coingen":
        text = "Its own --check audits coin geometry, but no script in tools/qa runs it."
    else:
        text = "No script in tools/qa opens or asserts on it."
    ev(s[0], "tests", [1], 1, text, "tools/qa coverage map")

# Open findings from release reviews and screenshots (sourced; each still true in this build).
ev("storagecard", "copy", [4], 1, "It counts localStorage keys only; IndexedDB and OPFS usage per desk is not included.", "review, build 56")
ev("pricefmt", "precision", [3], 1, "The worker control view stores price in whole cents, too coarse for DOGE (nothing reads it yet).", "review, build 56")
ev("fleetbal", "empty", [4], 1, "A fresh desk shows starting balances as if they were results; there is no 'no trades yet' state.", "desk screenshots, build 57")
ev("fundcells", "precision", [4], 1, "Zero money values mix formats: $0 beside $0.0.", "desk screenshots, build 57")
ev("loss", "precision", [2], 1, "GEOMETRIC GROWTH shows 0.000%/tick for small real moves: fixed decimals round them away.", "desk screenshots, build 57")
ev("chart", "empty", [1], 1, "Before history arrives the chart field is blank rather than saying it is waiting for observed data.", "desk screenshots, build 57")

evidence.sort(key=lambda e: (-e["sev"], sid.index(e["s"]), aid.index(e["a"])))

# ── outputs ────────────────────────────────────────────────────────────────────────────────────
axes = {"layers": LAYERS,
        "surfaces": [{"id": s[0], "name": s[1], "layer": s[2], "kind": s[3], "traits": s[4].split()} for s in SURFACES],
        "aspects": [{"id": a[0], "name": a[1], "moves": [{"n": move_parts(m)[0], "t": move_parts(m)[2]} for m in a[3]], "bars": a[4]} for a in ASPECTS],
        "depths": DEPTHS, "depthText": DEPTH_TEXT, "pairs": pairs, "perPass": per_pass, "evidence": evidence}
os.makedirs(os.path.join(ROOT, "ever-next"), exist_ok=True)
with open(os.path.join(ROOT, "ever-next", "axes.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(axes, fh, ensure_ascii=False, separators=(",", ":"))

def item_text(si, ai, move, depth):
    nature, _, text = move_parts(ASPECTS[ai][3][move])
    return text.replace("{s}", SURFACES[si][1]) + " " + DEPTH_TEXT[nature][depth]

# Static fallback: each measured finding at its first move and first depth, so the page reads without JavaScript.
static = []
for e in evidence:
    si, ai, m = sid.index(e["s"]), aid.index(e["a"]), e["m"][0]
    static.append(f'<li class="qc-en-item" data-measured><div class="qc-en-meta"><span class="qc-en-id">P1 · {e["s"]}.{e["a"]}.m{m + 1}.d1.c1</span>'
                  f'<span class="qc-en-depth">OBSERVE</span><span class="qc-en-sev s{e["sev"]}">MEASURED</span></div>'
                  f'<p class="qc-en-text">{html.escape(item_text(si, ai, m, 0))}</p>'
                  f'<p class="qc-en-ev"><b>MEASURED:</b> {html.escape(e["text"])} <small>({html.escape(e["src"])})</small></p></li>')

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
<p class="qc-sub">Every surface of QuadCOM, every quality it can have, and always a better version. Items are composed from the axes below, ranked by what this build measured about itself, and never run out.</p><div class="qc-rule"></div>
<div class="qc-grid">
<section class="qc-panel qc-span12" id="how-it-grows"><h2>HOW IT GROWS<a class="qc-anchor" href="#how-it-grows" aria-label="Link to HOW IT GROWS">#</a></h2>
<div class="qc-metric"><span>SURFACES</span><b>{len(SURFACES)} across {len(LAYERS)} layers</b></div>
<div class="qc-metric"><span>ASPECTS</span><b>{len(ASPECTS)}, each with 6 moves ({n_moves})</b></div>
<div class="qc-metric"><span>DEPTHS PER MOVE</span><b>{len(DEPTHS)}: {" → ".join(DEPTHS)}</b></div>
<div class="qc-metric"><span>VALID PAIRINGS</span><b>{len(pairs)} surface × aspect</b></div>
<div class="qc-metric"><span>ITEMS PER PASS</span><b>{per_pass:,}</b></div>
<div class="qc-metric"><span>MEASURED FINDINGS</span><b>{len(evidence)} from this build</b></div>
<div class="qc-metric"><span>PASSES</span><b>ENDLESS: after the last item the axes are walked again</b></div>
<p>Items are generated candidates, not claims. An aspect pairs only with the kinds of surface it can improve, each move deepens through five stages suited to its nature (audit, fix, writing, test or human judgement), and each cycle raises the bar. Items marked MEASURED carry a finding from this build&#x27;s own files, a browser audit or a release review; measurements refresh when the site is rebuilt. Your DONE, LATER and SKIP marks stay in this browser.</p></section>
<section class="qc-panel qc-span12" id="feed"><h2>THE FEED<a class="qc-anchor" href="#feed" aria-label="Link to THE FEED">#</a></h2>
<div class="qc-en-controls" data-en-controls hidden>
<div class="qc-seg qc-en-modes" role="radiogroup" aria-label="Mode">{"".join(f'<button type="button" role="radio" aria-checked="{"true" if m == "feed" else "false"}" data-mode="{m}">{m.upper()}</button>' for m in ("feed", "today", "sweep", "polish", "compose"))}</div>
<p class="qc-en-help" aria-live="polite"></p>
<div class="qc-en-facets">
<label>LAYER<select data-f="layer"><option value="">ALL</option>{opt(enumerate(LAYERS))}</select></label>
<label>SURFACE<select data-f="surface"><option value="">ALL</option>{opt((s[0], s[1]) for s in SURFACES)}</select></label>
<label>ASPECT<select data-f="aspect"><option value="">ALL</option>{opt((a[0], a[1]) for a in ASPECTS)}</select></label>
<label>DEPTH<select data-f="depth"><option value="">ALL</option>{opt(enumerate(DEPTHS))}</select></label>
<label>CYCLE<select data-f="cycle"><option value="">ALL</option>{opt((c, f"CYCLE {c + 1}") for c in range(max(len(a[4]) for a in ASPECTS)))}</select></label>
<label>STATUS<select data-f="status"><option value="">ALL</option><option value="measured">MEASURED</option><option value="open">NOT MARKED</option><option value="done">MY DONE</option><option value="later">MY LATER</option><option value="skip">MY SKIP</option></select></label>
</div>
<div class="qc-en-row"><input class="qc-search" type="search" data-f="q" placeholder="SEARCH ITEMS" aria-label="Search items">
<div class="qc-en-compose" hidden><label>SEED<input type="text" data-f="seed" inputmode="numeric" maxlength="9" aria-label="Compose seed"></label><label>SIZE<select data-f="size"><option>3</option><option selected>5</option><option>8</option><option>13</option></select></label><button type="button" class="qc-btn" data-shuffle>SHUFFLE</button></div>
<button type="button" class="qc-btn" data-reset>RESET</button><button type="button" class="qc-btn" data-export>EXPORT MY MARKS</button></div>
<p class="qc-en-count" aria-live="polite"></p><p class="qc-sr-only" data-en-announce aria-live="polite"></p></div>
<ol class="qc-en-list" data-en-list>{"".join(static)}</ol>
<button type="button" class="qc-btn qc-en-more" data-more hidden>SHOW MORE</button>
<noscript><p>The full feed composes its items in your browser. Without JavaScript, the measured findings from this build are listed above.</p></noscript>
</section></div>
<nav class="qc-pager" aria-label="Pages"><a rel="prev" href="/catalog/">← CATALOG</a><a rel="next" href="/glossary/">GLOSSARY →</a></nav></main>'''
with open(os.path.join(ROOT, "ever-next", "index.html"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write(head + main + tail)

lines = ["QUADCOM ❖ EVER NEXT — THE EVERLASTING IMPROVEMENT FEED", "",
         f"{len(SURFACES)} surfaces · {len(ASPECTS)} aspects · {n_moves} moves · {len(DEPTHS)} depths · escalating bars per aspect",
         f"{len(pairs)} valid surface × aspect pairings · {per_pass:,} items per pass · after the last item the axes are walked again", "",
         "Every item is: <move on a surface> + <the depth sentence for that move's nature>, judged against the aspect's bar for its cycle.",
         "Browse, filter, mix and mark them at /ever-next/. This file lists the axes and this build's measured findings.", "",
         "MEASURED FINDINGS (self-feedback from this build)", "─────────────────────────────────────────────────"]
for e in evidence:
    lines.append(f"[{'HIGH' if e['sev'] == 2 else 'NOTE'}] {e['s']}.{e['a']} (moves {', '.join(str(m + 1) for m in e['m'])}): {e['text']} ({e['src']})")
lines += ["", "ASPECTS, MOVES AND BARS", "───────────────────────"]
NATURE = {"a": "audit", "f": "fix", "w": "writing", "t": "test", "h": "human"}
for a in ASPECTS:
    applies_to = [s[0] for s in SURFACES if applies(s, a)]
    lines.append(f"{a[1]}  ({len(applies_to)} surfaces)")
    lines += [f"  {i + 1}. [{NATURE[move_parts(m)[0]]}{(' · only ' + ', '.join(sorted(move_parts(m)[1]))) if move_parts(m)[1] else ''}] {move_parts(m)[2].replace('{s}', '<surface>')}" for i, m in enumerate(a[3])]
    lines += [f"  bar, cycle {c + 1}: {b}" for c, b in enumerate(a[4])]
lines += ["", "DEPTHS BY MOVE NATURE", "─────────────────────"]
for k, name in NATURE.items():
    lines.append(f"{name}: " + " → ".join(f"{d} ({t})" for d, t in zip(DEPTHS, DEPTH_TEXT[k])))
lines += ["", "SURFACES", "────────"]
for li, layer in enumerate(LAYERS):
    lines.append(f"{layer}: " + "; ".join(f"{s[1]} [{s[3]}{(' · ' + s[4]) if s[4] else ''}]" for s in SURFACES if s[2] == li))
with open(os.path.join(ROOT, "EVER_NEXT_SUMMARY.txt"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines) + "\n")
print(f"{len(SURFACES)} surfaces · {len(ASPECTS)} aspects · {len(pairs)} pairings · {per_pass:,} items per pass · {len(evidence)} measured findings")

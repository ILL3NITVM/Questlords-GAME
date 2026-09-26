#!/usr/bin/env python3
"""Generates the Dogecoin, XRP and Litecoin desks from the Bitcoin desk (the single source).

    python3 site/tools/build-desks.py

Every substitution states how many times its source text must occur; the build fails on any
mismatch, and each output is scanned for Bitcoin identifiers that should not survive.
Why each group exists:
  feeds      Coinbase product ids and the Kraken pair.
  scale      Bitcoin-sized dollar constants (seed price, ATR and spread floors, chart half-range,
             price sanity limits). Each asset gets the same constants scaled by price.
  storage    Every localStorage / IndexedDB / OPFS name gets an asset suffix, and legacy
             migration is switched off, so desks never read or overwrite each other's state.
  format     Price decimals and chart-axis labels for sub-dollar and low-dollar assets.
  identity   Titles, tape label, brand marks and the active item in the portrait desk bar.
Seed prices are placeholders shown only until the first live tick (the desk marks them 'warming').
"""
import os, re
ROOT = os.path.join(os.path.dirname(__file__), "..")
SRC = os.path.join(ROOT, "desk", "bitcoin", "index.html")

ASSETS = [
    # id    slug        name        sym    coinbase    kraken    icon            seed    pd  axis_pd
    ("doge", "dogecoin", "Dogecoin", "DOGE", "DOGE-USD", "XDGUSD", "dogecoin.png", 0.20, 5, 4),
    ("xrp", "xrp", "XRP", "XRP", "XRP-USD", "XRPUSD", "xrp.png", 2.50, 4, 3),
    ("ltc", "litecoin", "Litecoin", "LTC", "LTC-USD", "LTCUSD", "litecoin.png", 100.0, 2, 1),
]
BTC_SEED = 84000.0

def num(x):
    s = f"{x:.10f}".rstrip("0").rstrip(".")
    return s if s else "0"

def build(a):
    aid, slug, name, sym, cb, kr, icon, seed, pd, axis_pd = a
    k = seed / BTC_SEED  # scale factor for Bitcoin-sized dollar constants
    subs = [
        # feeds
        ('"BTC-USD"', f'"{cb}"', 5),
        ("/products/BTC-USD/", f"/products/{cb}/", 5),
        ("pair=XBTUSD", f"pair={kr}", 3),
        ('"BTC-USD-CFD"', f'"{sym}-USD-CFD"', 3),
        ("BTC-USD contract", f"{cb} contract", 1),
        # scale
        ("&&p>1000", f"&&p>{num(1000 * k)}", 3),
        # websocket feed integrity: ticks outside this band are rejected as corrupt. Unscaled, every
        # sub-1000 price (all three new assets) would be rejected and the desk would never go live.
        ("price<1000||price>10000000", f"price<{num(1000 * k)}||price>{num(10000000 * k)}", 1),
        # candle history filters (Coinbase candles, Kraken OHLC, recovered-candle append): unscaled,
        # every candle of a sub-1000 asset is dropped and the desk never loads market history.
        ("c.close>1000", f"c.close>{num(1000 * k)}", 2),
        ("c.close<1000", f"c.close<{num(1000 * k)}", 1),
        ("price:84000,open24:84000", f"price:{num(seed)},open24:{num(seed)}", 1),
        ("lastPrice:84000", f"lastPrice:{num(seed)}", 1),
        ("finite(st.price,84000)", f"finite(st.price,{num(seed)})", 1),
        ("atr:45,spread:2.5", f"atr:{num(45 * k)},spread:{num(2.5 * k)}", 1),
        ("st.atr=Math.max(.01,finite(st.atr,45))", f"st.atr=Math.max({num(max(.01 * k, 1e-9))},finite(st.atr,{num(45 * k)}))", 1),
        ("st.spread=Math.max(.01,asks[0][0]-bids[0][0])", f"st.spread=Math.max({num(max(.01 * k, 1e-9))},asks[0][0]-bids[0][0])", 1),
        (",st.price*.0018,10)", f",st.price*.0018,{num(10 * k)})", 1),
        ("Math.max(qcChartScale.half,10)", f"Math.max(qcChartScale.half,{num(10 * k)})", 1),
        ("(qcChartScale.half||10)", f"(qcChartScale.half||{num(10 * k)})", 1),
        (">Math.max(40,(qcChartScale", f">Math.max({num(40 * k)},(qcChartScale", 1),
        # price-denominator floors: Math.max(1,price) guards divide-by-zero for Bitcoin, but for a
        # US$0.20 coin it silently shrinks every return 5x. Scale each floor with the price.
        ("/Math.max(1,t.entry)", f"/Math.max({num(k)},t.entry)", 8),
        ("/Math.max(1,st.price)", f"/Math.max({num(k)},st.price)", 2),
        ("/Math.max(1,h[i-1].p)", f"/Math.max({num(k)},h[i-1].p)", 2),
        ("Math.max(1,t.entry||st.price)", f"Math.max({num(k)},t.entry||st.price)", 1),
        ("(st.atr/Math.max(1,price)", f"(st.atr/Math.max({num(k)},price)", 1),
        ("return(st.price-b.p)/Math.max(1,b.p)", f"return(st.price-b.p)/Math.max({num(k)},b.p)", 1),
        ("let vol=cl(st.atr/Math.max(1,p)", f"let vol=cl(st.atr/Math.max({num(k)},p)", 1),
        ("(st.price-p.entry)/Math.max(1,p.entry)", f"(st.price-p.entry)/Math.max({num(k)},p.entry)", 1),
        ("(st.price-q.entry)/Math.max(1,q.entry)", f"(st.price-q.entry)/Math.max({num(k)},q.entry)", 1),
        ("st.session.move=(st.price-old)/Math.max(1,old)", f"st.session.move=(st.price-old)/Math.max({num(k)},old)", 1),
        ("(st.price-st.open24)/Math.max(1,st.open24)", f"(st.price-st.open24)/Math.max({num(k)},st.open24)", 1),
        ("/Math.max(1,st.atr)", f"/Math.max({num(k)},st.atr)", 1),
        ("ATR ${st.atr.toFixed(1)}", f"ATR ${{st.atr.toFixed({pd + 1})}}", 2),
        # format
        ("const axisPrice=v=>Math.abs(v)>=10000?`$${(v/1000).toFixed(1)}K`:`$${v.toFixed(0)}`;",
         f"const axisPrice=v=>Math.abs(v)>=10000?`$${{(v/1000).toFixed(1)}}K`:`$${{v.toFixed({axis_pd})}}`;", 1),
        # prices shown with whole-dollar precision (order-book rows, top position) get the asset's decimals
        ("<span>${fmt(p,0)}</span>", f"<span>${{fmt(p,{pd})}}</span>", 1),
        ("fmt(topOpen.entry,0)", f"fmt(topOpen.entry,{pd})", 1),
        # storage
        ('KEY="quadcom-2000-tenfold-v43"', f'KEY="quadcom-2000-tenfold-v43-{aid}"', 1),
        ('"quadcom-durable-v43"', f'"quadcom-durable-v43-{aid}"', 1),
        ('"quadcom-install-shell-v43"', f'"quadcom-install-shell-v43-{aid}"', 1),
        ("'quadcom-v43-ui'", f"'quadcom-v43-ui-{aid}'", 1),
        ("'quadcom-v43-last-good-ui'", f"'quadcom-v43-last-good-ui-{aid}'", 1),
        ("'quadcom-v42-ui'", f"'quadcom-v42-ui-{aid}'", 1),
        ("'quadcom-v43-view'", f"'quadcom-v43-view-{aid}'", 1),
        ('"quadcom-evolution-learning-v9.json"', f'"quadcom-evolution-learning-v9-{aid}.json"', 1),
        ('"quadcom-v13-background-marker.json"', f'"quadcom-v13-background-marker-{aid}.json"', 1),
        ('"quadcom-v43-checkpoint.json"', f'"quadcom-v43-checkpoint-{aid}.json"', 2),  # written and read
        # the v42 checkpoint is a Bitcoin-desk legacy file; new desks must never fall back to it
        (',"quadcom-v42-checkpoint.json"]', "]", 1),
        # identity
        ('data-qc-asset="btc"', f'data-qc-asset="{aid}"', 1),
        ('src="/assets/bitcoin.png"', f'src="/assets/{icon}"', 2),
        ('img[src$="bitcoin.png"]', f'img[src$="{icon}"]', 1),
        (">BTC TAPE<", f">{sym} TAPE<", 1),
        ("<title>Bitcoin Desk · QuadCOM</title>", f"<title>{name} Desk · QuadCOM</title>", 1),
        ("The QuadCOM Bitcoin Desk: a live 2000-PicoProcessor trading cockpit.", f"The QuadCOM {name} Desk: a live 2000-PicoProcessor trading cockpit.", 1),
        ("QuadCOM Bitcoin Desk</h1>", f"QuadCOM {name} Desk</h1>", 1),
        ("The Bitcoin Desk needs JavaScript to run.", f"The {name} Desk needs JavaScript to run.", 1),
        ('data-asset="btc" aria-current="page"', 'data-asset="btc"', 1),
        (f'data-asset="{aid}">', f'data-asset="{aid}" aria-current="page">', 1),
    ]
    s = open(SRC, encoding="utf-8").read()
    # Domain metadata (canonical, Open Graph) is per page; tools/build-domain.py stamps it after generation.
    s = re.sub(r"<!--qc-meta-->.*?<!--/qc-meta-->", "", s, flags=re.S)
    for old, new, count in subs:
        n = s.count(old)
        if n != count:
            raise SystemExit(f"[{slug}] expected {count}× {old!r}, found {n}")
        s = s.replace(old, new)
    # Legacy key migration imports another desk's state; the new desks start clean.
    s, n = re.subn(r'LEGACY_KEYS=\[[^\]]*\]', 'LEGACY_KEYS=[]', s)
    if n != 1:
        raise SystemExit(f"[{slug}] LEGACY_KEYS not found exactly once ({n})")
    # Price decimals: 2-decimal amounts under US$10 get the asset's price precision.
    if pd > 2:
        old = 'fmt=(x,d=0)=>Number.isFinite(x)?x.toLocaleString(undefined,{style:"currency",currency:"USD",minimumFractionDigits:d,maximumFractionDigits:d}):"—"'
        if s.count(old) != 1:
            raise SystemExit(f"[{slug}] fmt definition not found")
        s = s.replace(old, f'fmt=(x,d=0)=>Number.isFinite(x)?x.toLocaleString(undefined,{{style:"currency",currency:"USD",minimumFractionDigits:(d===2&&Math.abs(x)<10)?{pd}:d,maximumFractionDigits:(d===2&&Math.abs(x)<10)?{pd}:d}}):"—"')
    # Nothing Bitcoin-specific may survive, except the desk bar's link back to the Bitcoin desk.
    probe = s.replace('href="/desk/bitcoin/" data-asset="btc"', "").replace("qcCoin-btc", "").replace("url(/assets/bitcoin.png)", "")
    probe = probe.replace("/desk/bitcoin/glimmer", "")  # shared GLIMMER modules live with the Bitcoin desk
    left = sorted(set(re.findall(r"BTC-USD|XBTUSD|bitcoin\.png|Bitcoin|BTC TAPE|price:84000|close[<>]1000\b|p>1000\b|price<1000|v42-checkpoint", probe)))
    if left:
        raise SystemExit(f"[{slug}] Bitcoin identifiers survived: {left}")
    out = os.path.join(ROOT, "desk", slug)
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(s)
    return slug, len(subs) + 2

if __name__ == "__main__":
    for a in ASSETS:
        slug, n = build(a)
        print(f"desk/{slug}/index.html  ({n} checked substitutions)")

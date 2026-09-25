#!/usr/bin/env python3
"""Builds /catalog/index.html from the two catalog sources (the same data as the .txt catalogs).

    python3 site/tools/build-catalog-page.py

The page reads fully without JavaScript; qc-site.js adds search and a status filter.
Chrome (head, header, footer, tab bar, MORE sheet) is copied from the Data page so it never drifts.
"""
import html, os, re, sys
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import catalog, components  # each also rewrites its .txt catalog, with the same validation
ROOT = os.path.join(HERE, "..")

def group(status):
    return {"S": "shipped", "N": "next", "D": "deferred", "R": "rejected"}[status[0]]

def items_html(prefix, code, items, label):
    out = []
    for i, (s, title, note) in enumerate(items, 1):
        out.append(f'<li data-status="{group(s)}"><span class="qc-cat-id">{code}{i:02d}</span>'
                   f'<span class="qc-cat-st st-{group(s)}">{label[s]}</span>'
                   f'<span class="qc-cat-t">{html.escape(title)}'
                   + (f'<small>{html.escape(note)}</small>' if note else "") + "</span></li>")
    return "".join(out)

def book(bid, heading, blurb, areas, label):
    counts = {v: 0 for v in label.values()}  # summary in the catalog's own status order
    for items in areas.values():
        for s, _, _ in items:
            counts[label[s]] += 1
    total = sum(counts.values())
    summary = " · ".join(f"{k} {v}" for k, v in counts.items())
    secs = []
    for area, items in areas.items():
        code = area.split(" ")[0]
        aid = f"{bid}-{code.lower()}"
        secs.append(f'<section class="qc-panel qc-span12 qc-cat-area" id="{aid}"><h3>{html.escape(area)}'
                    f'<a class="qc-anchor" href="#{aid}" aria-label="Link to {html.escape(area)}">#</a></h3>'
                    f'<ul class="qc-cat">{items_html(bid, code, items, label)}</ul></section>')
    return (f'<section class="qc-panel qc-span12" id="{bid}"><h2>{heading}'
            f'<a class="qc-anchor" href="#{bid}" aria-label="Link to {heading}">#</a></h2>'
            f'<p>{blurb}</p><div class="qc-metric"><span>{total} ITEMS</span><b>{summary}</b></div></section>'
            + "".join(secs))

src = open(os.path.join(ROOT, "data", "index.html"), encoding="utf-8").read()
head, rest = src.split('<main class="qc-main" id="main" data-glossary-links>', 1)
tail = rest.split("</main>", 1)[1]
title, desc = "CATALOG", "Every planned improvement to the site and desks, with an honest status."
head = head.replace("ABOUT THE DATA · QuadCOM", f"{title} · QuadCOM")
head = re.sub(r'(<meta (?:property="og:description"|name="description") content=")[^"]*', lambda m: m.group(1) + desc, head)
head = head.replace('<a href="/data/" aria-current="page">DATA</a>', '<a href="/data/" >DATA</a>')
tail = tail.replace(' aria-current="page"', "").replace(" is-active", "")
assert "aria-current" not in head + tail and "ABOUT THE DATA" not in head

main = ('<main class="qc-main" id="main"><div class="qc-kicker">BUILD LEDGER</div>'
        f'<h1 class="qc-title">{title}</h1><p class="qc-sub">{desc}</p><div class="qc-rule"></div>'
        '<div class="qc-catbar" data-catalog-filter hidden>'
        '<input id="catalogSearch" class="qc-search" type="search" placeholder="SEARCH THE CATALOG" aria-label="Search the catalog">'
        '<div class="qc-seg" role="radiogroup" aria-label="Status">'
        + "".join(f'<button type="button" role="radio" aria-checked="{"true" if v == "all" else "false"}" data-status="{v}">{v.upper()}</button>'
                  for v in ("all", "shipped", "next", "deferred", "rejected"))
        + '</div><p class="qc-cat-count" aria-live="polite"></p></div>'
        '<nav class="qc-footnav qc-cat-jump" aria-label="Catalogs"><a href="#upgrades">600 UPGRADES</a><a href="#components">200 COMPONENTS</a></nav>'
        '<div class="qc-grid">'
        + book("upgrades", "600 UPGRADES", "Improvements across the public site and the desks. SHIPPED means built and verified in that build; "
               "DEFERRED and REJECTED items give their reason.", catalog.AREAS, catalog.LABEL)
        + book("components", "200 APP COMPONENTS", "Reusable app components for the site and the desks, in ten families of twenty.",
               components.F, components.LABEL)
        + '</div><nav class="qc-pager" aria-label="Pages"><a rel="prev" href="/data/">← DATA</a><a rel="next" href="/glossary/">GLOSSARY →</a></nav></main>')

out = os.path.join(ROOT, "catalog")
os.makedirs(out, exist_ok=True)
open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(head + main + tail)
print("catalog/index.html", sum(len(v) for v in catalog.AREAS.values()) + sum(len(v) for v in components.F.values()), "items")

QUADCOM GENESIS PUBLIC SITE · BUILD 56

Routes:
/
 /desk/
 /desk/bitcoin/
 /desk/dogecoin/
 /desk/xrp/
 /desk/litecoin/
 /learn/
 /how-it-works/
 /quadcom/
 /data/
 /glossary/
 /catalog/

Source preservation:
- The supplied Bitcoin Desk HTML remains the engine source.
- Engine persistence keys and inline trading/processor logic are preserved.
- The compact Best Singular Trade presentation is SIDE / ENTRY / SL / TP; existing Integrity/Pivot IDs remain hidden so runtime writes do not break.
- No live public-page values are fabricated.
- GLIMMER is installed: desk/bitcoin/glimmer.js (compute governor) and desk/bitcoin/glimmer-vision.js (VISION view). They are the same modules as quadcom/ in the repo.
- REGALIA skin installed: every texture lives once, in assets/textures/ (the desk points there with data-qc-texture-base). The skin is ornament only; the texture button in the GLIMMER sheet cycles REGALIA → AURUM → OFF (site pages: REGALIA or OFF).
- Direct routes require a static host configured to serve each folder's index.html (standard directory-index behavior).
- Service worker build: quadcom-genesis-public-v56. Assets are stale-while-revalidate; unvisited routes offline get /offline.html. Navigation is network-first. Only good same-origin responses are cached, and one missing file cannot abort install. The desk registers the same root worker (/sw.js, scope /).

Build 53 fixes:
- Skin textures, favicons, splash images and the desk's service worker were referenced but missing (404); all now resolve.
- The VISION view was reachable but empty (GLIMMER modules missing); it now renders.
- Desktop: the desk's command bar clipped VIEW/PERF/SEED/HALT, and cockpit text rendered at 2.5-3px. The header now lays out all visible controls, and screens ≥900px wide scale the phone-tuned cockpit.
- Site type raised from 5-9px to 9-17px; inputs are 16px (no iOS auto-zoom); low-contrast grey (#5c5e54, ~3:1) raised to #8f8f83 (~6:1).
- Keyboard focus rings, a skip link, 44px buttons and 38px nav targets; the nav wraps instead of hiding in an invisible scroll strip; reduced motion is respected.
- The logo no longer sits in a black box on dark panels.
- Every page has a meta description and icons; the desk has a real title; the manifest separates any/maskable icons.

Run locally from the project root with a static HTTP server, not file://.
Example: python3 -m http.server 8080

Build 54:
- V54_UPGRADE_CATALOG.txt lists 600 improvements with honest statuses: 111 shipped (V53+V54), 325 next, 59 deferred, 105 rejected, each deferral and rejection with its reason.
  Regenerate with: python3 tools/catalog.py (it fails unless there are 15 areas of exactly 40 items).
- New: 404.html, offline.html, robots.txt, app shortcuts, prev/next page links, footer nav, back-to-top, print stylesheet.
- Learn: cards 13-15 (GLIMMER, VISION, "inferred") and a deep link on every card.
- Glossary: 8 new terms, A-Z order and index, a live result count, "/" to search, Esc to clear, ?q= in the URL, deep links.
- Data: a fifth provenance class for GLIMMER compute output.
- Desk: cell labels no longer clipped, a hidden h1, a noscript notice, reduced motion, and the visual audit ignores decorative overlays.

Build 55 (app components; catalog: V55_COMPONENT_CATALOG.txt, python3 tools/components.py):
- Phone tab bar: HOME · LEARN · DESK (raised brushed-gold orb) · GLOSSARY · MORE, safe-area aware, on every page. The header nav hands over to it at 760px and below.
- MORE bottom sheet with a focus trap, Esc/backdrop/drag to dismiss and a scroll lock; it holds the remaining routes and a REGALIA/OFF skin segmented control.
- Toast system: link copied, offline/online, new build ready (RELOAD), skin changes.
- Reading-progress strip; icon sprite /assets/icons.svg (15 symbols); back-to-top with an icon, above the tab bar.
- Without JavaScript, MORE jumps to the footer, which now lists every route.

Build 56 (four desks):
- Dogecoin, XRP and Litecoin desks at /desk/dogecoin/, /desk/xrp/ and /desk/litecoin/, generated from the Bitcoin desk by
  python3 tools/build-desks.py. Never edit the generated desks; edit desk/bitcoin/index.html and re-run the generator.
  Every substitution is counted and the build fails on any mismatch or any surviving Bitcoin identifier.
  - Feeds: Coinbase DOGE-USD / XRP-USD / LTC-USD and Kraken XDGUSD / XRPUSD / LTCUSD.
  - Bitcoin-sized dollar constants (seed, ATR and spread floors, chart range, sanity limits, return denominators) are scaled by price.
  - Each desk keeps its own localStorage keys, IndexedDB database and OPFS files (suffix -doge / -xrp / -ltc); no desk reads another's state.
  - A fresh desk's placeholder daily open is replaced by the first live tick (all desks).
- Portrait desk bar: BTC · DOGE · XRP · LTC · DESKS along the bottom of every desk, filling the space under the cockpit. Hidden in landscape.
- /desk/ hub with a card per desk; DESKS replaces BITCOIN DESK in the nav, footer, tab orb and MORE sheet.
- Glossary: 48 terms (adds BACKEND, BOOTSTRAP, CALIBRATION, CFD100, DESK BAR, RISK CONE, TIER, TRADE ODDS); search matches are highlighted.
- Glossary terms in Learn, How it works, QuadCOM and Data copy open a definition sheet in place.
- Data: desk market sources, per-desk storage on this device, and a link to the catalog. Home: term of the day. Offline page: saved routes.
- /catalog/ renders both catalogs (800 items) with search and a status filter: python3 tools/build-catalog-page.py.
- Site pages use resized logos (96px, 640px) instead of the 632KB source; 404 and offline are noindex; Home has its own title.

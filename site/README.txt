QUADCOM GENESIS PUBLIC SITE · BUILD 58

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
- Service worker build: quadcom-genesis-public-v58. Assets are stale-while-revalidate; unvisited routes offline get /offline.html. Navigation is network-first. Only good same-origin responses are cached, and one missing file cannot abort install. The desk registers the same root worker (/sw.js, scope /).

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
  - Candle-history filters are scaled too, and order-book and position prices use the asset's decimals.
  - Each desk keeps its own localStorage keys, IndexedDB database and OPFS files (suffix -doge / -xrp / -ltc); no desk reads another's state.
  - A fresh desk's placeholder daily open is replaced by the first live tick (all desks).
- Portrait desk bar: BTC · DOGE · XRP · LTC · DESKS along the bottom of every desk, filling the space under the cockpit. Hidden in landscape.
- /desk/ hub with a card per desk; DESKS replaces BITCOIN DESK in the nav, footer and MORE sheet, and the DESK tab orb opens the hub.
- Glossary: 48 terms (adds BACKEND, BOOTSTRAP, CALIBRATION, CFD100, DESK BAR, RISK CONE, TIER, TRADE ODDS); search matches are highlighted.
- Glossary terms in Learn, How it works, QuadCOM and Data copy open a definition sheet in place.
- Data: desk market sources, per-desk storage on this device, and a link to the catalog. Home: term of the day. Offline page: saved routes.
- /catalog/ renders both catalogs (800 items) with search and a status filter: python3 tools/build-catalog-page.py.
- Site pages use resized logos (96px, 640px) instead of the 632KB source; 404 and offline are noindex; Home has its own title.

Build 57 (GENESIS master skin, mastered coin marks):
- Coin marks: python3 tools/coin-master.py re-cuts every coin onto the same geometry (256px, disc centred exactly on the
  canvas centre, radius 127, transparent outside) using a least-squares circle fit of each disc's rim. The Bitcoin
  source had an opaque black matte and an off-centre, slightly out-of-round disc; all four now audit to 0.000px.
  The artwork inside each disc (glyph placement, the Bitcoin mark's official tilt) is untouched. --check audits only.
- GENESIS, the master skin and the new default: python3 tools/build-genesis-skin.py writes deterministic SVG line art
  to assets/textures/genesis/, every motif derived from QuadCOM:
  - Seal: the official mark inside a four-fold guilloche rosette, ringed by 2000 ticks (one per PicoProcessor,
    a longer tick every 100, a diamond at each quadrant). A quiet watermark on site pages and a specimen on the
    QuadCOM page. In the desks the breathing logo and header beacons are held still under GENESIS.
  - Intaglio panel field, quarter-diamond corners, guilloche header band, quad rule (a hairline with four square
    diamond nodes), reeded coin bezels, and a bare pip for the desk's small cells.
  - An explicit OFF saved under the old key is carried over; the standalone repo desk (quadcom/) keeps REGALIA,
    AURUM and OFF, since GENESIS lives in the site's asset tree.
  - Static: no glow and no animation. Ornament only: text, values and the black chart field are unchanged.
- Skin preference key is now quadcom-v57-skin (the old key was written automatically on every desk visit, so it
  could not tell a choice from a default). Site: GENESIS · REGALIA · OFF under MORE. Desk texture control cycles
  GENESIS → REGALIA → AURUM → OFF.
- Site logos (96px, 640px) now have a real alpha channel, so the mark no longer sits in a black square.
- QuadCOM page: GENESIS specimen. Learn: card 17, THE SKINS.

Build 58 (production domain: https://quadcom.live):
- Build order after any change: python3 tools/build-desks.py, python3 tools/build-catalog-page.py,
  (optionally node tools/qa/measure-runtime.mjs 8192 with the site served), python3 tools/build-ever-next.py, then
  python3 tools/build-domain.py (it stamps every page, so it runs last).
  All are idempotent.
- tools/build-domain.py: canonical URL, Open Graph and Twitter card tags on every page (from each page's own title and
  description; 404 and offline stay noindex with no canonical), sitemap.xml (every public route), robots.txt with the
  sitemap, _headers and CNAME.
- assets/og-card.jpg: the 1200x630 link-preview card, rendered by tools/build-og-card.mjs (Playwright) from the GENESIS
  seal and the official mark. No live values.
- _headers (read by Cloudflare Pages and Netlify; GitHub Pages ignores it and the site still works there):
  nosniff, Referrer-Policy, Permissions-Policy, X-Frame-Options and HSTS on every route; no-cache on sw.js and the
  manifest; COOP/COEP on each desk route (not the /desk/ hub) so the desks are cross-origin isolated and the engine's SharedArrayBuffer worker
  arena switches on (GLIMMER reports sab:true). Market data comes by CORS fetch and WebSocket, which isolation allows.
  Without these headers the engine falls back to copying, exactly as before.
- tools/qa/serve.py serves site/ with _headers applied, to test isolation locally: cd site && python3 tools/qa/serve.py 8193
- CNAME contains quadcom.live for GitHub Pages; other hosts ignore it.
- DNS for the host is set at the registrar and is not part of this repository.

EVER NEXT (/ever-next/, the everlasting improvement feed):
- Items are composed, not listed: surface x aspect x move x depth x cycle, from tools/ever_next_axes.py.
  Surfaces have one kind (page, ui, datapanel, layout, image, texture, runtime, tool, doc) and traits (interactive,
  motion, data, live). Each aspect names the kinds (and traits) it applies to, with explicit includes and excludes,
  and a move may add its own condition, e.g. "f[data]:" applies only to surfaces that show values.
- Every move has a nature (audit, fix, writing, test, human judgement) with its own five depths, OBSERVE → REFINE →
  SYSTEMATISE → PROVE → SUSTAIN, so each stage fits the move. Each aspect raises its bar per cycle.
  Counts are printed by the build (currently 957 pairings, 82,890 items per pass). After the last item the feed walks
  the axes again as the next pass; measurements refresh only when the site is rebuilt, never in the browser.
- The builder validates the axes: moves keep the surface as their object, and no pronoun may refer back to it, so
  sentences stay grammatical for singular and plural surfaces.
- Self-feedback: tools/build-ever-next.py measures the repository (asset budgets, !important counts, a three-level
  QA coverage map that fails if it names a missing script, sourced review findings) and reads ever-next/runtime.json,
  written by tools/qa/measure-runtime.mjs from a real browser (running infinite animations per skin and viewport;
  visible text rendered below 7px). Each finding targets the specific moves it concerns; those items lead the feed.
- The page (ever-next/core.js composes, feed.js drives): FEED, TODAY (five, the same for everyone on a UTC day),
  SWEEP (one aspect across surfaces), POLISH (one surface through aspects), COMPOSE (a seeded bundle); facets, search,
  mix-and-match chips, DONE / LATER / SKIP marks kept in this browser, and an export of those marks.
- To grow it: add a surface, aspect, move or bar to tools/ever_next_axes.py and rebuild. tools/qa/ever-next.mjs checks
  the composer against the builder (count, unique ids, no unfilled text, deterministic COMPOSE) and the page's modes.
- Its first measurement cut the link-preview card from 427 KB (PNG) to 108 KB (JPEG).
- The offline page lives at /offline/ (a directory route), because Cloudflare Pages and Netlify redirect /offline.html to
  /offline, and the service worker deliberately never caches redirected responses: the fallback would silently vanish.

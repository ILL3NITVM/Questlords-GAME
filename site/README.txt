QUADCOM GENESIS PUBLIC SITE · BUILD 53

Routes:
/
 /desk/bitcoin/
 /learn/
 /how-it-works/
 /quadcom/
 /data/
 /glossary/

Source preservation:
- The supplied Bitcoin Desk HTML remains the engine source.
- Engine persistence keys and inline trading/processor logic are preserved.
- The compact Best Singular Trade presentation is SIDE / ENTRY / SL / TP; existing Integrity/Pivot IDs remain hidden so runtime writes do not break.
- No live public-page values are fabricated.
- GLIMMER is installed: desk/bitcoin/glimmer.js (compute governor) and desk/bitcoin/glimmer-vision.js (VISION view). They are the same modules as quadcom/ in the repo.
- REGALIA skin installed: every texture lives once, in assets/textures/ (the desk points there with data-qc-texture-base). The skin is ornament only; the texture button in the GLIMMER sheet cycles REGALIA → AURUM → OFF (site pages: REGALIA or OFF).
- Direct routes require a static host configured to serve each folder's index.html (standard directory-index behavior).
- Service worker build: quadcom-genesis-public-v53. Navigation is network-first. Only good same-origin responses are cached, and one missing file cannot abort install. The desk registers the same root worker (/sw.js, scope /).

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

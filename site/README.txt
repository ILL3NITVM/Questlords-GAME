QUADCOM GENESIS PUBLIC SITE · BUILD 52

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
- GLIMMER external JS modules were referenced by the supplied HTML but were not included in the uploaded files. They are therefore not counterfeited in this package. The inline Desk engine remains present.
- Direct routes require a static host configured to serve each folder's index.html (standard directory-index behavior).
- Service worker build: quadcom-genesis-public-v52; navigation is network-first to reduce stale-desk risk.

Run locally from the project root with a static HTTP server, not file://.
Example: python3 -m http.server 8080

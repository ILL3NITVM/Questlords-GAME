# QuadCOM Desk Lite MAX — Front-End Stack

**Synthetic market lab · forward-printing tape · visible structure, visible restraint, visible audit.**
Ever Next Phase.

QuadCOM Desk Lite MAX is a business-facing synthetic market cockpit. A seeded
model feed prints a **live tape** for a synthetic instrument (default
`BTC/USD.SYN`), an **Oracle** reads structure and confidence, a five-voice
**Council** votes CALL / PUT / HOLD, and a **Governor** explains — in plain
language — why action is held or clear. Every tick and every action is written
to a hash-chained audit log. Nothing is rewritten after print.

> **Safety disclaimer** — This is an *educational build stream* on a
> *synthetic substrate*. There is **no real broker connection, no real money,
> no profit promises, and no financial advice**. Lab entries and lab capital
> are research constructs. Losses remain in the record.

## What is a synthetic substrate?

A model-generated price stream — a live tape printed forward in real time from
a seeded model feed. It is not a real market. It exists so structure,
discipline, and decision quality can be studied and streamed openly.

## Run locally

Native ES modules — serve over HTTP (not `file://`):

```sh
cd QuadCOM_Stack
python3 -m http.server 8137 --bind 127.0.0.1
# open http://127.0.0.1:8137/
```

No build step, no dependencies.

## Product layers

| Layer | Where | What |
|---|---|---|
| Live / Broadcast mode | LIVE pill (top bar) or More → Enter Live Mode | Big-card streaming cockpit: asset, action, confidence, gate, tape phase, council bars, last resolved outcome, session timer, next-print countdown, crowd vote prompt |
| Onboarding | More → What is this? | The format explained in 60 seconds |
| Fairness / Audit | More → Fairness | Forward-printing rules, session ID/seed/start, tick count, chained hash, event count, integrity status, recent audit entries |
| Session reports | More → Reports | Export JSON / CSV, copy text summary, Generate Session Recap (founder summary) |
| Business / Access | More → Business | Lite / Pro concept / research offers + local watchlist capture (name, contact, interest — localStorage only, no payments) |
| Share Kit | More → Share Kit | Copy-paste TikTok LIVE title, pinned comment, Telegram invite, bios, captions |
| Settings | More → Settings | Asset selector (BTC/USD.SYN · ETH/USD.SYN · SBCI.FX16), theme intensity, live mode, public wording mode, sound, tick speed, seed regenerate, session reset, export/import data |
| Doctrine | More → Doctrine | The seven laws of the desk |
| Self-Test | More → Self-Test | Built-in acceptance checks (also `await QUADCOM.selfTest()` in the console) |

## Public wording rules

The public UI never uses: *simulator, fake, game, gambling, casino, guaranteed*.
It uses: synthetic substrate, market lab, live tape, execution lab, model feed,
council, forward-printing tape, educational build stream, not financial advice.
The self-test scans the rendered UI for restricted terms.

## Audit model

`state = { app/session, asset, tape(ticks/book/market), oracle/council,
governor, execution(positions/history), wallet(transfers/metrics), reports,
waitlist, settings, auditLog }`

Every tick advances a rolling session hash. Typed events append to `auditLog`:
`TICK_PRINTED, ORACLE_UPDATED, COUNCIL_UPDATED, GOVERNOR_CLEAR, GOVERNOR_BLOCK,
LAB_ENTRY_OPENED, LAB_ENTRY_RESOLVED, SESSION_RESET, REPORT_EXPORTED,
WAITLIST_CAPTURED, SETTINGS_CHANGED`.

## How to use Live mode

Tap **LIVE** in the top bar (or More → Enter Live Mode). Frame the phone
vertically for TikTok. The two anchor lines for viewers:

> **Vote the tape: CALL, PUT, or HOLD.**
> QuadCOM reads structure. The crowd reads pressure. The tape decides.

Exit with the EXIT button. Live mode state persists in Settings.

## How to export reports

More → Reports → Export JSON / Export CSV / Copy Text Summary, or
**Generate Session Recap** for the founder/business one-liner. Reports include
the full event log, seed, and integrity hash. `Export Founder Pack` on the
Business page bundles the recap with product framing.

## Architecture

```
index.html            shell markup
styles/theme.css      tokens + accent themes (gold/ice/magma) — tap the logo
styles/app.css        layout + productization CSS
src/config.js         MODE.LIVE seam · assets · branding · safety copy
src/audit.js          hash-chained audit log
src/reports.js        JSON/CSV/recap builders
src/copykit.js        share kit + founder pack
src/core/store.js     central state
src/engines/          session(seeded rng) · council · governor · execution ·
                      autopilot · analytics · account
src/data/             feed selector (sim | live) · wallet adapters · faucet
src/ui/               render · router · gateway · chart · sparkline · toast ·
                      theme · pages (product pages) · live (broadcast) · views/
sw.js                 fault-tolerant offline cache (whole module graph)
```

`MODE.LIVE` in `src/config.js` remains the single seam that would swap the
synthetic feed/wallet for live adapters. It ships `false` and the product’s
public posture is lab-only.

## Known limitations

- Watchlist and settings are device-local (localStorage) — no backend.
- Crowd voting is a broadcast prompt, not a collected poll (next phase).
- The audit hash chain is integrity-evident, not cryptographically signed.
- Live-adapter seams (`liveFeed`, `liveWallet`) are wiring points, not enabled.

## Phase log (8–17) — shipped

Responsive shell (desktop left rail + two-column desk) · regime timeline ·
LIVE crowd voting with audit · replay lab · session archive shelf · doctrine
gate presets · session receipts + chain verification · sibling watch strip ·
hidden-tab paint pause + keyboard shortcuts (C/P/A/L/Esc) · 19-check
acceptance battery. See CHANGELOG.md.

## Next phase roadmap

1. Crowd vote feed as a council input (crowd pressure weight).
2. Shareable public session pages from archived receipts.
3. Two-asset split desk (simultaneous tapes).
4. Creator doctrine editor (custom laws + gate curves).

Ever Next Phase.

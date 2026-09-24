# SANDEVISTAN — handoff prompt

Paste everything below the line into a new agent that has this repo (or the zip). Do not rebuild the kitchen. Edit the desk in place.

---

You are continuing **SANDEVISTAN**, a demo Bitcoin desk run by a fruit-fly connectome inside a cyborg cockroach. The kitchen 3D world is retired and must stay unmounted. The fly trades. It is a paper account. It believes the tape is real. Reward is frass (poop): take-profit adds one, stop-loss removes one. Starting equity is $10,000. If equity falls under $800, refill the demo to $10,000 and drop open tickets. Never use real-money APIs, keys, or order placement. Never add user accounts or auth. Never add a joystick or WASD.

Tone stays happily jokey, not grim. Copy is short. No emoji icons. Tailwind v4 tokens already live in `src/styles.css` (`bg`, `surface`, `fg`, `muted`, `subtle`, `accent`, `danger`, `warn`, `border`). Do not invent a second palette or sprinkle raw hex in JSX. Fonts are Outfit + IBM Plex Mono. Mobile first, no horizontal overflow, tap targets at least 44px.

## Stack

TanStack Start + React 19 + Tailwind v4 + Vite. Home route is `src/routes/index.tsx` and it renders `DeskApp` only. Live price is Coinbase `BTC-USD` (ticker, 24h stats, 60s candles) via `getMarket` in `src/lib/market.ts` → `fetchMarket` in `src/lib/market.server.ts`. Kraken ticker is the fallback. Python Kenyon momentum is `python/fly_desk.py` (stdin JSON `{closes}` → stdout signal). If Python fails, `decide()` in `src/game/strategy.ts` is the same math. Client also has a direct Coinbase fallback inside `DeskApp` if the server function throws.

`MarketTick`: `{ price, change24, high, low, closes, signal, source }`.
`DeskSignal`: `{ side: "buy"|"sell"|"hold", confidence, note, fast, slow, momentum, engine: "python"|"ts" }`.

## What is live

`src/desk/book.ts` — `FlyBook` class, `useSyncExternalStore` snapshot, `localStorage` key `sandevistan-fly-book-v1`.

`src/desk/DeskApp.tsx` — the page. Polls every 4s. A `requestAnimationFrame` loop calls `book.senseStep` so the connectome canvas twitches between polls. **Halt entries** freezes new tickets only. An open ticket still runs to TP or SL.

`src/game/brain.ts` — 40 leaky-integrator neurons. Layers: antennal lobe 8, optic lobe 6, mushroom body 12, central complex 8, descending 6. `step(dt, { olf, visL, visR, threat, speed })` returns steer/throttle. The desk only uses firing, olfactory, visual, motorL/motorR.

`src/game/NeuralPanel.tsx` — canvas of those neurons. Keep it.

### How a ticket is born today (single position — this is the bug to fix)

Senses, each tick:

- smell ∈ [-1, 1] from Kenyon momentum, signal side, and 24h change
- glare ∈ [0, 1] from stdev of recent 1m returns
- hunger ∈ [0, 1] only while flat, rising over ~90s
- vote = 0.7 * (olfactory − 0.55*visual + 0.35*(motorR−motorL)) + 0.45 * kenyon (±confidence)

Those senses are mapped into the brain (`olf`, `visL`/`visR` from glare and smell sign, `threat` = glare) and stepped 10 × 0.06s before the vote.

Entry if armed, flat, and 20s since last entry: long if vote > 0.18, short if vote < −0.18.

Stops are from glare, not from the candle wick:

- `slPct = clamp(0.0007 + glare*0.0028, 0.00065, 0.004)`
- `tpPct = slPct * (1.45 + min(1, |vote|)*0.9)`
- long: TP above entry, SL below. short: mirrored.
- size = `cash * clamp(0.14 + firing*0.22 + hunger*0.08, 0.12, 0.38)`, qty = spend/entry
- cash is reduced by `spend` (locked margin). Equity = cash + spend + unrealized. Long pnl = qty*(px−entry). Short pnl = qty*(entry−px).

Exit uses **last price only**, not candle high/low (the 1m candle includes prices from before the fill and was wick-stopping instantly). Long: price ≤ SL else price ≥ TP. Short: price ≥ SL else price ≤ TP. Fill at the level, not the gap. Same-tick both sides: stop wins. TP banner `TAKE PROFIT · FRASS UP`. SL banner `STOP · DIMINISHING POOP`.

`armed` is **not** persisted. Cash, poop, the one open ticket, history (40), and `flatSince` are.

## Dead code — do not remount

`src/game/game.ts`, `world.ts`, `roach.ts`, `sim.ts`, `SimApp.tsx`, `Hud.tsx`, `TitleOverlay.tsx`, `TouchControls.tsx`, `input.ts`, `particles.ts`, `audio.ts` are the old kitchen sim (three.js r186, tripod gait, sucrose, stomps). Leave the files. Do not import them from the route. Do not bring back a joystick.

## Next task (done — see `src/desk/rules.ts`, `backtest.ts`, `book.ts`)

Shared entry/TP/SL rules now live in `src/desk/rules.ts` so the live book and the backtest replay cannot drift. Full `npm run build` + browser smoke still need the complete workspace (this zip lacks `scripts/`, `src/components/`, `src/lib/auth/`).

The last product ask, in the user's words: **"Multiple parallel trades, make the fly backtest if it wants, and non volatile when fly app tab closed."**

Do all three. Keep the same voice, tokens, and demo-only rule.

### 1. Parallel tickets

Replace `open: Ticket | null` with `open: Ticket[]`. Cap at **4** live tickets. Do not stack the identical side at the identical vote; a new ticket needs a fresh vote and its own TP/SL. Size each ticket off **free cash**, and keep at least ~15% cash unspent so a stop cannot pin the book. Cooldown between entries ~12s, not "must be flat". Hunger stays high while under the cap, not only when flat.

Resolve **every** open ticket against last price each poll. Aggregate unrealized. Equity = cash + sum(spend + pnl). Refill still drops all open tickets.

UI: the right column lists every live ticket (side, qty, entry, TP, SL, unrealized, a slim rail). Tape lists recent closes and shows how many are open. Empty state is not "one ticket".

Bump the storage key to `sandevistan-fly-book-v2`. If v1 data exists, migrate `open` from a single ticket into an array. Do not crash on bad JSON.

### 2. Backtest, only if the fly wants it

The fly may refuse. It backtests when glare is high **or** the last three closes are stops **or** it has been armed and flat-of-edge (vote near 0) for a while. Otherwise skip and say so in one line ("Mushroom body is full. No backtest.").

When it wants one: pull more Coinbase candles (granularity 60, as many as the API returns in one call, sorted oldest→newest). Replay the **same** entry/TP/SL rules on closes only, with a fresh paper cash of $10,000, no effect on the live book. Walk forward; do not peek. Show a small result card: trades, win rate, net pnl, max drawdown, and whether the fly keeps the current TP/SL widths or tightens them slightly (only if the backtest win rate is under ~40% — shrink `slPct`/`tpPct` multipliers a little, persist that bias on the book, cap the shrink so stops stay at least ~0.06%). A button is allowed: **Let the fly backtest**. It can also fire on its own at most once per few minutes. Never block the 4s tape poll; run the replay off the click or after the poll resolves. If the candle fetch fails, show the error, do not invent candles.

Python may score the replay, but the TypeScript path must work when `python3` is missing (Vercel). Do not spawn Python from the browser.

### 3. Non-volatile when the tab is closed

Meaning: closing or hiding the tab must not keep trading, and reopening must not invent a burst of fills for the time away.

- Persist cash, poop, open tickets, history, armed, backtest bias, and last price seen (`sandevistan-fly-book-v2`).
- On `visibilitychange` hidden or `pagehide`: stop the poll and the rAF. Save. Do not run TP/SL while hidden.
- On visible again: load the saved book **as it was**. Fetch one fresh tick. Mark open pnl to that price. Do **not** walk missed minutes and do **not** close tickets that would have hit TP/SL while the tab was shut. The fly was asleep. Say that once: `TAB WAS SHUT · BOOK UNCHANGED`.
- `beforeunload` is unnecessary if `pagehide` saves. No service worker, no background sync, no server cron.

## Verify

`npm run typecheck` must pass. Smoke `http://127.0.0.1:8080/` with `node scripts/browser-smoke.mjs` at desktop and mobile. The page must show SANDEVISTAN, a live BTC price, more than one ticket possible, a backtest result or an honest refusal, and zero console errors. Then `npm run build`, `npm run preview:restart`, smoke port 8081, `npm run preview:stop`.

## Do not

- Remount the 3D kitchen or three.js gameplay.
- Add auth, wallets, or live orders.
- Change the visual language.
- Close tickets using candle high/low from before the fill.

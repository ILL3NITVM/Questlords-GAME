# QuadCOM Desk Lite MAX — Phase 4

**Master Crypto Perpetuals & Account Faucet.** A single-file PWA cockpit for the
synthetic `BTC/USD.SYN` (Bitcoin Synthetic / Perpetual Core), delivered as three
assets: `index.html`, `manifest.json`, `sw.js` (plus `icon-512.png`).

## Substrate

- `BTC/USD.SYN` on a `62000–67000` band around a `64500` base, `tickSize 0.5`.
- Regime-driven engine (COMP / DRIFT UP / DRIFT DN / IMPULSE / PULLBACK) with
  volatility clustering, momentum, and mean-pull producing organic crypto swings.
- Live VWAP, POC, session high/low, ±2.1σ band, order book, and microprice.
- All prints and axis scales rendered with `.toFixed(2)`.

## 5-View Bottom-Nav SPA

| View | Contents |
|------|----------|
| **DESK** | Oracle ticker ribbon, `ResizeObserver`-robust canvas chart with red **HIGH ROLLING WALL** / green **LOW ROLLING WALL** zones, VWAP/POC/BID/ASK reference lines, momentum dots, live CALL/PUT commitment markers with dotted tracking rays and a hover crosshair tooltip; HIGH/LOW/VWAP/POC/REGIME/MICROPRICE foot; plus an order book + microprice panel. |
| **EXEC** | `ENABLE AUTOPILOT` switch with STATUS / FIRES / GATE / SIZE readouts, the execution rail ticket (expiry / stake / max-open / min-conf, CALL ask-entry, PUT bid-entry), and the lifecycle **Execution Tape**. |
| **COUNCIL** | `VOTES · CONSENSUS · CHAMBER` sub-nav — Macro/Flow/Gate/Structure vote weights, an aggregate `COUNCIL CONSENSUS` score with a `TENSION` meter, and Support/Resistance/Bull/Bear probability gauges. |
| **GOV** | `CAPITAL · PRESSURE · GUARD` sub-nav — `CLEAR`/`HALT` status typography, the simulated **testnet faucet rail** (deposit / balance-validated withdraw), the `+ IN` / `- OUT` transfer ledger, and drawdown / exposure / loss-streak pressure metrics. |
| **MORE** | Balance / Net / Turnover / Win-Rate / Edge / Governor overview plus a holistic module map. |

## Wallet & Gateway

- Boot is gated by the blurred **QUADCOM SECURE GATEWAY** modal until a wallet
  connects.
- `SIMULATE WALLET CONNECT` mints a random hex public address (optional operator
  ID is normalized to `0x…`), shown as an `OPR: 0x…` pill with a `LOGOUT` control.
- Storage is isolated per wallet under `quadcom_data_<ADDRESS>`; the active
  session key is `quadcom_active_account`. Logout preserves each account dataset.
- New wallets initialize at **$0.00** — the operator must use the GOV faucet
  before executions clear.

## Execution Math

- Opening a ticket debits the stake immediately and adds to turnover.
- Wins credit the stake back plus the 92% payout; sub-tick ties refund the exact
  stake; losses forfeit the stake.
- Settlement is directional versus entry (CALL exits on bid, PUT on ask), so
  concurrent same-strike hedging resolves to the spread loss — never risk-free.

## Fault-Tolerant PWA

`sw.js` caches each asset individually with per-asset `try/catch`, so a missing
asset (e.g. `icon-512.png` unavailable over a bare `python -m http.server`) never
breaks install; the fetch handler is cache-first with a navigation fallback to
the cached shell.

## Run locally

```sh
cd QuadCOM_Desk_Lite_MAX
python3 -m http.server 8137 --bind 127.0.0.1
# open http://127.0.0.1:8137/
```

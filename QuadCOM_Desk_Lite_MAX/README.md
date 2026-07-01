# QuadCOM Desk Lite MAX — Phase 4

**Master Crypto Perpetuals & Account Faucet.** A single-file PWA cockpit for the
synthetic `BTC/USD.SYN` (Synthetic Bitcoin Continuous Perpetual Index),
delivered as three assets: `index.html`, `manifest.json`, `sw.js`.

## Substrate

- Retired `SBCI.FX16`; instantiated `BTC/USD.SYN` initialized around `64500.00`.
- `tickSize = 1.0`; organic multi-frequency crypto swings ($10–$50 intervals)
  driven by macro drift + volatility clustering + rolling-wall reactions.
- All prints and axis scales rendered with `.toFixed(2)`.

## 5-View Bottom-Nav SPA

| View | Contents |
|------|----------|
| **DESK** | Oracle ticker ribbon, `ResizeObserver`-robust canvas chart with red **HIGH ROLLING WALL** / green **LOW ROLLING WALL** zones, trailing Parabolic SAR points, live CALL (blue up) / PUT (red down) commitment arrows with dotted tracking rays, VWAP/POC lines, and a HIGH/LOW/VWAP/POC/REGIME/MICROPRICE sub-ticker. Inline CALL/PUT trade ticket. |
| **EXEC** | `ENABLE AUTOPILOT` switch, STATUS / FIRES / GATE / SIZE metric grid, and the live **Execution Tape** lifecycle log. |
| **COUNCIL** | `VOTES · CONSENSUS · CHAMBER` sub-nav. Core engine weights (Macro/Flow/Gate/Structure), an aggregate `COUNCIL CONSENSUS` number, a `TENSION` meter, and a 4-band outcome-probability visualizer. |
| **GOV** | `CAPITAL · PRESSURE · GUARD` sub-nav. `CLEAR`/`HALT` status typography, the **Simulated Faucet Rail** (deposit / balance-validated withdraw), and the `+ IN` / `- OUT` **Transaction Ledger**. |
| **MORE** | 2-column holistic module map plus a Balance / Net P/L / Turnover / Win-Rate session overview. |

## Wallet & Gateway

- On boot with no session key, the layout blurs behind the mandatory
  **QUADCOM SECURE GATEWAY** modal.
- `[ SIMULATE WALLET CONNECT ]` mints a random 12-char hex public address
  (`0x…`, displayed short-form `0x8F2...4A1B`).
- Storage is isolated per wallet under `quadcom_data_<WALLET_ADDRESS>`; logout
  wipes the active views but preserves each account dataset.
- New wallets initialize at **$0.00** — the operator must use the GOV faucet
  to deposit synthetic liquidity before executions clear.

## Execution Math

- Opening a ticket debits the stake immediately.
- Wins credit the stake back plus the 92% payout margin; ties refund the exact
  stake; losses forfeit the stake.
- Settlement is directional versus entry price, so concurrent same-strike
  hedging always resolves to the institutional spread loss — never a risk-free
  premium.

## Fault-Tolerant PWA

`sw.js` caches each asset individually and traps every fetch, so a missing
asset (e.g. `icon-512.png` unavailable over a bare `python -m http.server`)
is bypassed without rejecting the install or blocking script execution.

## Run locally

```sh
cd QuadCOM_Desk_Lite_MAX
python3 -m http.server 8137 --bind 127.0.0.1
# open http://127.0.0.1:8137/
```

# QuadCOM Desk Lite MAX — Front-End Stack

A modular, native **ES-module** front-end for the BTC/USD.SYN synthetic crypto
perpetuals cockpit. Same product as the single-file build in
`../QuadCOM_Desk_Lite_MAX`, re-architected as a real front-end stack that is
**one boolean away from a tangible live venture**.

## The one boolean

```js
// src/config.js
export const MODE = Object.freeze({ LIVE: false });
```

- `LIVE: false` → fully synthetic simulation (paper venture, safe demo).
- `LIVE: true`  → the app swaps three adapters for their live counterparts and
  nothing else changes:

| Concern | Simulation | Live venture |
|---|---|---|
| Market data | `src/data/simFeed.js` | `src/data/liveFeed.js` (websocket → same snapshot shape) |
| Wallet | `src/data/simWallet.js` (mints local address) | `src/data/liveWallet.js` (injected EIP-1193 provider) |
| Execution | local binary settlement | `src/engines/execution.js` LIVE branch → `config.LIVE.executionApi` |

Every engine, view, the router, and the chart are **source-agnostic** — they
consume `state` and never know which world they run in. Wire the endpoints in
`config.LIVE` and flip the flag.

## Architecture

```
index.html                 shell markup + <link> css + <script type=module>
styles/theme.css           design tokens
styles/app.css             layout, panels, chart, views, gateway
src/
  config.js                THE boolean + constants + live endpoints
  util.js                  pure helpers
  main.js                  composition root: wires state→feed→engines→ui, loop
  core/store.js            central state shape + wallet-scoped reset
  data/
    feed.js                selector (sim | live)
    simFeed.js  liveFeed.js
    wallet.js              gateway connect + persistence + faucet
    simWallet.js  liveWallet.js
  engines/
    account.js  council.js  governor.js  execution.js  autopilot.js
  ui/
    chart.js               canvas price chart + depth curve
    components.js  render.js  router.js  gateway.js
    views/ desk.js  exec.js  council.js  gov.js  more.js
sw.js                      fault-tolerant cache of the whole module graph
manifest.json
```

## Behaviour (unchanged from the single-file build)

- 5-view SPA: Desk (order book / depth / microprice / structure), Exec
  (autopilot + rail + live position book + tape), Council (votes / consensus /
  chamber), Gov (capital / pressure / guard + faucet), More (session + map).
- Secure gateway with per-wallet isolated storage (`quadcom_data_<address>`),
  $0.00 init, faucet-gated execution.
- Execution math: immediate stake debit, 92% payout on win, exact refund on tie,
  directional settlement (same-strike hedging = spread loss).
- Governor never halts on losses/streak/drawdown (informational only).

## Run locally

Because it uses native ES modules, serve over HTTP (not `file://`):

```sh
cd QuadCOM_Stack
python3 -m http.server 8137 --bind 127.0.0.1
# open http://127.0.0.1:8137/
```

No build step, no dependencies — the browser loads the module graph directly.
Add a bundler later (esbuild/Vite) without changing the source layout.

# SANDEVISTAN

A demo Bitcoin desk run by a fruit-fly connectome. Paper account only: no keys, no orders, no auth.

## Run

```sh
npm install
npm run dev          # http://localhost:8080
```

Production:

```sh
npm run build
npm start            # http://127.0.0.1:8081  (node .output/server/index.mjs)
```

Deploy to Vercel with `NITRO_PRESET=vercel npm run build`. Python (`python/fly_desk.py`) is optional; the TypeScript path is used when `python3` is missing.

## Single HTML file

```sh
npm run build:single   # writes sandevistan.html
```

One self-contained file (React, the fly, CSS all inlined). Open it in any browser; it fetches Coinbase `BTC-USD` directly. No server, so no Python engine and no Kraken fallback.

## Check

```sh
npm run typecheck
npm run smoke                                   # real Coinbase tape, dev server on :8080
node scripts/browser-smoke.mjs http://127.0.0.1:8081/
SMOKE_FIXTURE=1 npm run smoke                   # synthetic tape when Coinbase is unreachable
```

Live price comes from Coinbase `BTC-USD` via a server function, with Kraken as a server fallback and a direct browser fetch to Coinbase when the server cannot reach either.

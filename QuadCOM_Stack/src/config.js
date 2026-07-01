/* ============================================================================
 * QuadCOM Desk Lite MAX — Front-End Stack Configuration
 *
 * THE ONE BOOLEAN.
 * ----------------
 * `MODE.LIVE = false`  → fully synthetic simulation (safe demo / paper venture).
 * `MODE.LIVE = true`   → tangible real venture: the app swaps its synthetic
 *                        price feed, wallet, and execution rails for the live
 *                        adapters in src/data/liveFeed.js, src/data/liveWallet.js,
 *                        and src/engines/execution.js (LIVE branch). Every other
 *                        module — engines, router, views, chart — is source
 *                        agnostic and does not change.
 *
 * Flip this single flag to move from paper to production. Nothing else in the
 * UI or analytics layer needs to know which world it is running in.
 * ==========================================================================*/
export const MODE = Object.freeze({
  LIVE: false
});

export const INSTRUMENT = MODE.LIVE ? "BTC/USD" : "BTC/USD.SYN";
export const INSTRUMENT_LONG = MODE.LIVE ? "Bitcoin / US Dollar Perpetual" : "Bitcoin Synthetic / Perpetual Core";

// Market scale (synthetic substrate defaults; live feed overrides at runtime).
export const TICK = 0.5;
export const MIN = 62000;
export const MAX = 67000;
export const BASE = 64500;
export const PAYOUT = 0.92;

// Runtime cadence.
export const CADENCE_MS = 650;
export const AUTO_MS = 1000;

// Wallet-scoped storage keys.
export const STORAGE = Object.freeze({
  active: "quadcom_active_account",
  prefix: "quadcom_data_"
});

/* Real-venture wiring points. Consumed only when MODE.LIVE === true.
 * Replace these with your production endpoints before going live. */
export const LIVE = Object.freeze({
  feedWs: "wss://REPLACE_ME.example/stream/btcusd",   // market data websocket
  feedRest: "https://REPLACE_ME.example/v1",           // snapshot / order book REST
  walletProvider: "injected",                          // "injected" (window.ethereum) | "walletconnect"
  faucetUrl: null,                                      // real testnet faucet (LIVE deposits)
  executionApi: "https://REPLACE_ME.example/v1/orders" // order placement endpoint
});

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

/* Selectable synthetic instruments (educational substrate — not real markets). */
export const ASSETS = {
  "BTC/USD.SYN": { symbol: "BTC/USD.SYN", long: "Bitcoin Synthetic / Perpetual Core", base: 64500, tick: 0.5, min: 62000, max: 67000, decimals: 2 },
  "ETH/USD.SYN": { symbol: "ETH/USD.SYN", long: "Ethereum Synthetic / Perpetual Core", base: 3400, tick: 0.1, min: 3100, max: 3700, decimals: 2 },
  "SBCI.FX16":   { symbol: "SBCI.FX16", long: "Synthetic Bundled Currency Index / 16-FX Basket", base: 1.08700, tick: 0.00001, min: 1.06000, max: 1.11000, decimals: 5 }
};
export const DEFAULT_ASSET = "BTC/USD.SYN";

/* Product branding + safety copy (public-facing, compliant wording). */
export const BRAND = Object.freeze({
  name: "QuadCOM Desk Lite MAX",
  tagline: "Synthetic market lab",
  phase: "Ever Next Phase",
  vote: "Vote the tape",
  hero: "Vote the tape: CALL, PUT, or HOLD.",
  hero2: "QuadCOM reads structure. The crowd reads pressure. The tape decides.",
  handle: "@quadcom",
  telegram: "t.me/quadcom",
  site: "quadcom.app"
});

export const SAFETY =
  "Educational build stream · synthetic substrate · not financial advice. " +
  "No real broker, no real money, no profit promises. All lab actions are forward-printing and logged.";

/* Words that must never appear in public UI copy (enforced by the self-test). */
export const BANNED = Object.freeze(["simulator", "fake", "game", "gambling", "casino", "guaranteed"]);

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

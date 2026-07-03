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

/* Selectable synthetic instruments (educational substrate — not real markets).
 * Built from the Phase 7C-harvested predecessor catalog (42 instruments across
 * FX / metals / crypto / indices / energy / agri / rates / volatility). */
import { INSTRUMENT_CATALOG } from "./data/instruments.js";

function decimalsForTick(tick) {
  const s = String(tick);
  const frac = s.includes(".") ? s.split(".")[1].length : 0;
  return Math.max(2, Math.min(6, frac));
}
export const ASSETS = {};
for (const it of INSTRUMENT_CATALOG) {
  ASSETS[it.id] = {
    symbol: it.id, long: `${it.name} · ${it.alias}`, family: it.family,
    base: it.base, tick: it.tick, min: it.min, max: it.max,
    spreadTicks: it.spreadTicks, decimals: decimalsForTick(it.tick)
  };
}
export const DEFAULT_ASSET = "BTCUSD.SYN";

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

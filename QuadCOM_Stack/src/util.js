/* Shared pure helpers — no side effects, no DOM ownership. */

// Asset-aware decimal precision (BTC/ETH = 2, SBCI.FX16 = 5).
let DECIMALS = 2;
export const setDecimals = n => { DECIMALS = (n == null ? 2 : n); };
export const getDecimals = () => DECIMALS;

export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
export const fmt = n => (Number.isFinite(n) ? n : 0).toFixed(DECIMALS);
export const money = n => "$" + (Number.isFinite(n) ? n : 0).toFixed(2);
export const signMoney = n => (n >= 0 ? "+" : "-") + money(Math.abs(n));
export const now = () => new Date().toLocaleTimeString([], { hour12: false });
export const sizeFmt = n => (n >= 1e6 ? (n / 1e6).toFixed(2) + "M" : Math.round(n / 1e3) + "K");
export const $ = id => document.getElementById(id);

// HTML-escape user-provided strings before injecting into innerHTML.
export const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// cyrb53 — fast non-cryptographic 53-bit hash for the audit chain.
export function cyrb53(str, seed = 0) {
  let h1 = 0xdeadbeef ^ seed, h2 = 0x41c6ce57 ^ seed;
  for (let i = 0, ch; i < str.length; i++) {
    ch = str.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return 4294967296 * (2097151 & h2) + (h1 >>> 0);
}
export const hashHex = (str, seed = 0) => cyrb53(str, seed).toString(16).padStart(12, "0");

// Deterministic RNG (mulberry32) so a session seed reproduces the tape.
export function mulberry32(a) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

// Browser file download + clipboard helpers.
export function download(filename, text, type = "text/plain") {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export async function copy(text) {
  try { await navigator.clipboard.writeText(text); return true; }
  catch (_) {
    try {
      const ta = document.createElement("textarea");
      ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove();
      return true;
    } catch (__) { return false; }
  }
}

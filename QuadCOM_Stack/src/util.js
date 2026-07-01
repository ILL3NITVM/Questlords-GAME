/* Shared pure helpers — no side effects, no DOM ownership. */
import { BASE } from "./config.js";

export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
export const fmt = (n, base = BASE) => (Number.isFinite(n) ? n : base).toFixed(2);
export const money = n => "$" + (Number.isFinite(n) ? n : 0).toFixed(2);
export const signMoney = n => (n >= 0 ? "+" : "-") + money(Math.abs(n));
export const now = () => new Date().toLocaleTimeString([], { hour12: false });
export const sizeFmt = n => (n >= 1e6 ? (n / 1e6).toFixed(2) + "M" : Math.round(n / 1e3) + "K");
export const $ = id => document.getElementById(id);
export const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
};

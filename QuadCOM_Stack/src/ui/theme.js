/* Accent theme system — recolors the cockpit's gold accent tokens.
 * Global (not wallet-scoped) and persisted. Tap the brand logo to cycle. */
export const THEMES = ["gold", "ice", "magma"];
const KEY = "quadcom_theme";
const LABEL = { gold: "GOLD", ice: "ICE", magma: "MAGMA" };

export function createTheme() {
  function get() { try { return localStorage.getItem(KEY) || "gold"; } catch (_) { return "gold"; } }
  function apply(t) {
    document.documentElement.setAttribute("data-theme", t);
    try { localStorage.setItem(KEY, t); } catch (_) {}
  }
  function cycle() {
    const i = (THEMES.indexOf(get()) + 1) % THEMES.length;
    apply(THEMES[i]);
    return LABEL[THEMES[i]];
  }
  function init() { apply(get()); }
  return { get, apply, cycle, init, label: t => LABEL[t || get()] };
}

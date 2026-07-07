/* Bottom-nav SPA router — swaps the active view and repaints. */
import { drawChart } from "./chart.js";

export function createRouter(ctx) {
  const { state } = ctx;
  function route(name) {
    state.route = name || "desk";
    document.querySelectorAll(".view").forEach(v => v.classList.toggle("active", v.dataset.view === state.route));
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.toggle("active", b.dataset.route === state.route));
    ctx.render();
    requestAnimationFrame(() => drawChart(state));
  }
  return { route };
}

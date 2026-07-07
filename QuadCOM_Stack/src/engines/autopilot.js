/* Autopilot — disciplined turnover. Fires the council's directional bias only
 * through the full gate stack (armed, gate confidence, spacing, slots, cash).
 * The governor no longer halts, so a cold streak keeps firing until cash or
 * slots run out — exactly as intended after the no-halt change. */
import { governorState } from "./governor.js";

export function createAutopilot(ctx, { execution }) {
  const { state, settings } = ctx;

  function tick() {
    settings(); // keep gate reads live
    const g = governorState(state);
    if (!state.autopilot) { state.autoStatus = "OFF"; return; }
    if (!state.armed) { state.autoStatus = "DISARMED"; return; }
    if (g.state === "HALT") { state.autoStatus = "HALT"; return; } // unreachable (no-halt)
    if (!state.council.allowed) { state.autoStatus = "WAIT"; return; }
    if (Date.now() - state.lastAuto < 4200) { state.autoStatus = "SPACING"; return; }
    const before = state.metrics.turnover;
    execution.open(state.council.action, "AUTO");
    if (state.metrics.turnover > before) { state.autoFires++; state.autoStatus = "ON"; }
  }

  return { tick };
}

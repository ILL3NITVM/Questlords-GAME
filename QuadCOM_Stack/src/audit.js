/* Audit log — forward-only, hash-chained record of the session.
 *
 * Every tick advances a rolling hash and the tick counter. Every meaningful
 * event (oracle/council/governor/lab/session/report/waitlist/settings) is
 * appended with its own chained hash. Nothing is rewritten after print; the
 * visible log is capped for readability while counts + hash cover the whole
 * run. This is what makes the lab auditable rather than random. */
import { hashHex } from "./util.js";

export const EVENTS = [
  "TICK_PRINTED", "ORACLE_UPDATED", "COUNCIL_UPDATED", "GOVERNOR_CLEAR", "GOVERNOR_BLOCK",
  "LAB_ENTRY_OPENED", "LAB_ENTRY_RESOLVED", "SESSION_RESET", "REPORT_EXPORTED",
  "WAITLIST_CAPTURED", "SETTINGS_CHANGED"
];

export function createAudit(state) {
  function advance(payload) {
    const s = state.session;
    s.lastHash = hashHex(s.lastHash + "|" + payload, s.seed);
  }

  function push(type, data) {
    const s = state.session;
    s.eventCount++;
    advance(type + ":" + JSON.stringify(data) + ":" + s.eventCount);
    state.auditLog.push({ t: Date.now(), type, data, hash: s.lastHash });
    if (state.auditLog.length > 500) state.auditLog.shift();
  }

  return {
    // Chains every tick; surfaces a throttled TICK_PRINTED entry for the log.
    tick(price) {
      const s = state.session;
      s.tickCount++;
      advance("T:" + price + ":" + s.tickCount);
      if (s.tickCount % 12 === 0) push("TICK_PRINTED", { price, n: s.tickCount });
    },
    event: push,
    integrity() { return state.session ? state.session.integrity : "CLEAR"; }
  };
}

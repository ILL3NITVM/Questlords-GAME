/* Session reports — JSON / CSV / copyable founder recap.
 * Built entirely from the recorded session, tally, metrics, and audit log.
 * Losses remain in the record; nothing is rewritten. */
import { money } from "./util.js";

export function buildReport(state) {
  const s = state.session, t = state.tally, m = state.metrics;
  const confAvg = t.confN ? t.confSum / t.confN : 0;
  return {
    product: "QuadCOM Desk Lite MAX",
    build: "Educational build stream",
    asset: state.asset.symbol,
    assetLong: state.asset.long,
    sessionId: s.id,
    seed: s.seed,
    startedISO: s.startedISO,
    endedISO: new Date().toISOString(),
    ticks: s.tickCount,
    events: s.eventCount,
    lastHash: s.lastHash,
    integrity: s.integrity,
    decisions: { CALL: t.call, PUT: t.put, HOLD: t.hold },
    confidenceAvg: +confAvg.toFixed(1),
    wins: m.wins, losses: m.losses, refunds: m.refunds, closed: m.closed,
    governorClears: t.govClears, governorBlocks: t.govBlocks,
    maxExposurePct: +t.maxExposure.toFixed(1),
    labOpened: t.labOpened, labResolved: t.labResolved,
    turnover: +m.turnover.toFixed(2),
    finalLabCapital: +m.balance.toFixed(2),
    eventLog: state.auditLog.map(e => ({ t: new Date(e.t).toISOString(), type: e.type, data: e.data, hash: e.hash })),
    disclaimer: "Synthetic substrate — educational build stream — not financial advice."
  };
}

export function toJSON(r) { return JSON.stringify(r, null, 2); }

export function toCSV(r) {
  const esc = v => `"${String(v).replace(/"/g, '""')}"`;
  const lines = [];
  lines.push("section,key,value");
  const flat = {
    product: r.product, asset: r.asset, sessionId: r.sessionId, seed: r.seed,
    startedISO: r.startedISO, endedISO: r.endedISO, ticks: r.ticks, events: r.events,
    lastHash: r.lastHash, integrity: r.integrity,
    "decisions.CALL": r.decisions.CALL, "decisions.PUT": r.decisions.PUT, "decisions.HOLD": r.decisions.HOLD,
    confidenceAvg: r.confidenceAvg, wins: r.wins, losses: r.losses, refunds: r.refunds,
    governorClears: r.governorClears, governorBlocks: r.governorBlocks, maxExposurePct: r.maxExposurePct,
    labOpened: r.labOpened, labResolved: r.labResolved, turnover: r.turnover, finalLabCapital: r.finalLabCapital
  };
  for (const k in flat) lines.push(`summary,${esc(k)},${esc(flat[k])}`);
  lines.push("");
  lines.push("event_time,event_type,event_hash,event_data");
  for (const e of r.eventLog) lines.push(`${esc(e.t)},${esc(e.type)},${esc(e.hash)},${esc(JSON.stringify(e.data))}`);
  return lines.join("\n");
}

export function recap(state) {
  const r = buildReport(state);
  const d = r.decisions, total = (d.CALL + d.PUT + d.HOLD) || 1;
  const holdPct = Math.round(d.HOLD / total * 100);
  const dom = (d.HOLD >= d.CALL && d.HOLD >= d.PUT) ? "held below threshold"
    : d.CALL >= d.PUT ? "leaned CALL" : "leaned PUT";
  const gov = r.governorBlocks > 0 ? `Governor intervened ${r.governorBlocks} time(s)` : "Governor remained clear";
  return `QuadCOM ${r.asset} session ${r.sessionId} completed. ` +
    `Oracle ${dom} for most of the session (${holdPct}% HOLD). ` +
    `Council confidence averaged ${r.confidenceAvg}. ${gov}. ` +
    `${r.labResolved} lab position(s) resolved (${r.wins}W / ${r.losses}L). ` +
    `No forced execution occurred. Final lab capital ${money(r.finalLabCapital)}. ` +
    `Integrity ${r.integrity} · seed ${r.seed} · ${r.ticks} ticks. ` +
    `Educational build stream — not financial advice.`;
}

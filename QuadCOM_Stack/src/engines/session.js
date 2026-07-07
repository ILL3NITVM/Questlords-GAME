/* Session model — a seeded, auditable run. The seed drives the tape RNG so a
 * session is reproducible; the rolling hash chains every tick + event so the
 * record is tamper-evident. Nothing here is hidden from the operator. */
import { mulberry32 } from "../util.js";

export function newSession(seed) {
  if (seed == null || !Number.isFinite(seed)) seed = Math.floor(Math.random() * 1e9);
  const started = Date.now();
  return {
    id: "QC-" + seed.toString(36).toUpperCase().padStart(6, "0"),
    seed,
    started,
    startedISO: new Date(started).toISOString(),
    tickCount: 0,
    eventCount: 0,
    lastHash: "genesis",
    integrity: "CLEAR"
  };
}

export function makeRng(seed) {
  return mulberry32(seed >>> 0);
}

/* Copy / Share Kit — ready-to-paste, compliant marketing strings.
 * Generated from live branding + the active asset. No banned wording. */
import { BRAND } from "./config.js";

export function shareKit(state) {
  const a = state.asset.symbol;
  return {
    "TikTok LIVE title": `QuadCOM ${a} — Vote the tape LIVE · CALL / PUT / HOLD`,
    "Pinned comment": `QuadCOM Desk Lite MAX — synthetic market lab. Vote the tape: CALL, PUT, or HOLD. We read structure, you read pressure, the tape decides. Educational build stream — not financial advice.`,
    "Telegram invite": `Join the QuadCOM build stream → ${BRAND.telegram}\nSynthetic market lab · ${a} live tape · Vote the tape · ${BRAND.phase}.`,
    "Short bio": `QuadCOM Desk Lite MAX — synthetic market lab. Vote the tape. Not financial advice.`,
    "Long description": `QuadCOM Desk Lite MAX is a synthetic market lab. A forward-printing tape prints ${a}, an Oracle reads structure and confidence, a Council votes CALL / PUT / HOLD, and a Governor protects capital state. Every tick and action is logged and auditable. This is an educational build stream — synthetic substrate, no real broker, no real money, not financial advice. ${BRAND.phase}.`,
    "Post caption": `We read structure. You read pressure. The tape decides. Vote CALL / PUT / HOLD on ${a}. Synthetic market lab. Not financial advice.`,
    "Hashtag-light caption": `QuadCOM ${a} live tape. Vote CALL, PUT, or HOLD. ${BRAND.phase}.`
  };
}

export function founderPack(state, report) {
  return [
    `QUADCOM DESK LITE MAX — FOUNDER PACK`,
    `${BRAND.tagline} · ${BRAND.phase}`,
    ``,
    `WHAT IT IS`,
    `A synthetic market lab. A forward-printing tape prints ${state.asset.symbol}; an Oracle reads`,
    `structure + confidence; a Council votes CALL / PUT / HOLD; a Governor protects capital state.`,
    `Every tick and action is logged and auditable. Educational build stream — not financial advice.`,
    ``,
    `SESSION SNAPSHOT`,
    report,
    ``,
    `CONTACT`,
    `${BRAND.handle} · ${BRAND.telegram} · ${BRAND.site}`
  ].join("\n");
}

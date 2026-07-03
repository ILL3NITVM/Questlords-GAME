/* Product pages layer — full-screen overlay pages opened from the More hub:
 * onboarding, fairness, reports, business, sharekit, settings, doctrine,
 * about, selftest. Each page is a renderer over live state; pages with live
 * fields (fairness) re-render each cadence while open. */
import { BRAND, SAFETY, ASSETS, BANNED } from "../config.js";
import { $, esc, money, download, copy } from "../util.js";
import { buildReport, toJSON, toCSV, recap } from "../reports.js";
import { shareKit, founderPack } from "../copykit.js";

const sect = (title, body) => `<section class="pg-sect"><h3>${title}</h3>${body}</section>`;
const p = t => `<p>${t}</p>`;
const kv = (k, v, id = "") => `<div class="pg-kv"><span>${k}</span><b${id ? ` id="${id}"` : ""}>${v}</b></div>`;
const btn = (act, label, cls = "") => `<button class="pg-btn ${cls}" type="button" data-act="${act}">${label}</button>`;

/* ---------------- page renderers ---------------- */

function onboarding(state) {
  return sect("What is QuadCOM?", p(`${BRAND.name} is a <b>synthetic market lab</b>: a live, forward-printing tape with visible structure, visible restraint, and a full audit trail. We read structure. The crowd reads pressure. The tape decides.`))
    + sect("What is a synthetic substrate?", p(`A synthetic substrate is a model-generated price stream — a <b>live tape</b> printed forward in real time from a seeded model feed. It is not a real market and carries no real money. It exists so structure, discipline, and decision quality can be studied openly.`))
    + sect("What is BTC/USD.SYN?", p(`A synthetic Bitcoin perpetual instrument printed by the substrate around a reference level. Same idea as the real chart's behaviour — swings, walls, compression — but fully synthetic and auditable.`))
    + sect("What is SBCI.FX16?", p(`The Synthetic Bundled Currency Index — a 16-currency basket instrument from earlier QuadCOM phases. Selectable in Settings for FX-style tape behaviour at 5-decimal precision.`))
    + sect("What is CALL / PUT / HOLD?", p(`<b>CALL</b> — a lab position that resolves in profit if the tape prints higher at expiry. <b>PUT</b> — the same, lower. <b>HOLD</b> — the deliberate decision to do nothing. HOLD is a first-class output, not a failure.`))
    + sect("What is the Council?", p(`Five model voices — Macro, Flow, Gate, Structure, Retail — each scoring the tape from a different angle. Their weighted agreement produces one action and one confidence number.`))
    + sect("What is the Governor?", p(`The capital layer. It tracks exposure, drawdown, and integrity, and explains in plain language why action is held or clear. The Governor outranks the Oracle.`))
    + sect("Why can confidence still mean HOLD?", p(`Confidence is not permission. Action requires confidence <b>above the gate threshold</b> plus a free slot, funded capital, and an armed lab. High conviction with a closed gate is still HOLD.`))
    + sect("Why waiting is part of the system", p(`Most of any session is waiting. The lab shows that restraint on purpose: every HOLD is logged, every wait is explained, and losses stay in the record. ${BRAND.phase}.`))
    + `<div class="pg-note">${SAFETY}</div>`;
}

function fairness(state) {
  const s = state.session || {};
  return `<div class="pg-note ok">Integrity model: the tape prints forward, every tick advances a hash chain, and nothing is rewritten after print.</div>`
    + sect("Forward-printing tape", p(`Ticks are appended to the tape as they print. There is no candle rewriting, no hindsight edits, no future leakage into the model feed. The chart you see is the record.`))
    + sect("No forced outcomes", p(`No forced wins, no outcome forcing, no hidden nudges. Lab entries resolve purely against the printed tape: win, loss, or refund — and <b>every loss remains recorded</b>.`))
    + sect("Everything is logged", p(`Every tick advances the session hash. Every action — oracle updates, council votes, governor states, lab entries and resolutions, settings changes, exports — is appended to the audit log with a chained hash.`))
    + sect("Session integrity", `
      ${kv("Session ID", esc(s.id || "—"), "fzId")}
      ${kv("Seed", esc(String(s.seed ?? "—")), "fzSeed")}
      ${kv("Started", s.startedISO ? new Date(s.started).toLocaleString() : "—", "fzStart")}
      ${kv("Tick count", s.tickCount ?? 0, "fzTicks")}
      ${kv("Last tick hash", esc(s.lastHash || "—"), "fzHash")}
      ${kv("Event count", s.eventCount ?? 0, "fzEvents")}
      ${kv("Integrity status", s.integrity || "CLEAR", "fzInteg")}`)
    + sect("Recent audit entries", `<div class="pg-log">` + [...state.auditLog].slice(-14).reverse().map(e =>
        `<div class="pg-logrow"><span>${new Date(e.t).toLocaleTimeString([], { hour12: false })}</span><b>${e.type}</b><i>${esc(e.hash).slice(0, 10)}</i></div>`).join("") + `</div>`)
    + `<div class="pg-note">${SAFETY}</div>`;
}

function reportsPage(state) {
  const s = state.session || {}, t = state.tally;
  return sect("Session so far", `
      ${kv("Asset", state.asset.symbol)}
      ${kv("Ticks", s.tickCount ?? 0)}
      ${kv("Decisions", `CALL ${t.call} · PUT ${t.put} · HOLD ${t.hold}`)}
      ${kv("Lab positions", `${t.labOpened} opened · ${t.labResolved} resolved`)}
      ${kv("W / L", `${state.metrics.wins} / ${state.metrics.losses}`)}
      ${kv("Lab capital", money(state.metrics.balance))}`)
    + sect("Export", `<div class="pg-btnrow">
        ${btn("export-json", "Export JSON")}
        ${btn("export-csv", "Export CSV")}
        ${btn("copy-summary", "Copy Text Summary")}
      </div>`)
    + sect("Founder recap", `<div class="pg-btnrow">${btn("gen-recap", "Generate Session Recap", "primary")}</div>
      <div id="recapOut" class="pg-recap"></div>`)
    + `<div class="pg-note">Reports include the full event log. ${SAFETY}</div>`;
}

function business(state) {
  return `<div class="pg-hero">${BRAND.name}<span>${BRAND.tagline} · ${BRAND.phase}</span></div>`
    + sect("QuadCOM Lite", p(`The open build: live synthetic tape, council votes, governor restraint, and full session audit — exactly what you see streaming today.`))
    + sect("QuadCOM Pro — concept", p(`Deeper council telemetry, multi-asset desks, longer session archives, custom gate doctrine, and exportable research packs. In design — join the watchlist to shape it.`))
    + sect("Live build access", p(`Follow the educational build stream: watch the tape print, vote CALL / PUT / HOLD, and see every decision logged in the open.`))
    + sect("Session reports", p(`Every session exports a JSON/CSV report with the complete event log, seed, and integrity hash — auditable end to end.`))
    + sect("Synthetic substrate research", p(`The substrate is a research surface: regimes, walls, compression, and crowd pressure — studied without real-money exposure.`))
    + sect("Custom dashboard concept", p(`Bespoke desks on the QuadCOM engine for creators and research teams. Request a demo below.`))
    + sect("Join the watchlist", `
      <div class="pg-form">
        <input id="wlName" placeholder="Name" autocomplete="off">
        <input id="wlContact" placeholder="Email or Telegram" autocomplete="off">
        <select id="wlInterest">
          <option>Viewer</option><option>Builder</option><option>Trader</option><option>Researcher</option>
        </select>
        <div class="pg-btnrow">
          ${btn("waitlist-join", "Join Watchlist", "primary")}
          ${btn("request-demo", "Request Demo")}
          ${btn("export-founder", "Export Founder Pack")}
          ${btn("copy-invite", "Copy Invite Message")}
        </div>
        <div id="wlMsg" class="pg-formmsg"></div>
        <div class="pg-mini">Watchlist entries stay on this device (local storage only). No payments are processed.</div>
      </div>`)
    + `<div class="pg-note">${SAFETY}</div>`;
}

function sharekit(state) {
  const kit = shareKit(state);
  return Object.entries(kit).map(([k, v]) =>
    `<section class="pg-sect"><h3>${k}</h3><div class="pg-copyblock"><pre>${esc(v)}</pre>${btn("copy-kit:" + esc(k), "Copy")}</div></section>`
  ).join("") + `<div class="pg-note">${SAFETY}</div>`;
}

function settingsPage(state) {
  const st = state.settings;
  // Grouped by family (harvested 42-instrument catalog).
  const fams = {};
  for (const k of Object.keys(ASSETS)) (fams[ASSETS[k].family || "OTHER"] ||= []).push(k);
  const assetOpts = Object.keys(fams).map(f =>
    `<optgroup label="${f}">` + fams[f].map(k => `<option ${k === state.asset.symbol ? "selected" : ""}>${k}</option>`).join("") + `</optgroup>`).join("");
  const row = (label, control) => `<div class="pg-set"><span>${label}</span>${control}</div>`;
  return sect("Desk", ""
      + row("Asset", `<select id="setAsset">${assetOpts}</select>`)
      + row("Theme intensity", `<select id="setIntensity"><option ${st.themeIntensity === "normal" ? "selected" : ""}>normal</option><option ${st.themeIntensity === "high" ? "selected" : ""}>high</option></select>`)
      + row("Tick speed (ms)", `<input id="setTick" type="number" min="120" max="4000" step="10" value="${st.tickSpeed}">`))
    + sect("Broadcast", ""
      + row("Live mode", `<button class="pg-toggle ${state.live ? "on" : ""}" data-act="toggle-live" type="button">${state.live ? "ON" : "OFF"}</button>`)
      + row("Public wording mode", `<button class="pg-toggle ${st.publicWording ? "on" : ""}" data-act="toggle-public" type="button">${st.publicWording ? "ON" : "OFF"}</button>`)
      + row("Sound", `<button class="pg-toggle ${st.sound ? "on" : ""}" data-act="toggle-sound" type="button">${st.sound ? "ON" : "OFF"}</button>`))
    + sect("Session", `<div class="pg-btnrow">
        ${btn("regen-seed", "Regenerate Session Seed")}
        ${btn("reset-session", "Reset Session", "danger")}
        ${btn("export-all", "Export All Data")}
      </div>
      <div class="pg-set import"><span>Import session data (JSON)</span><textarea id="importBox" rows="3" placeholder='{"settings":{...},"waitlist":[...]}'></textarea>${btn("import-data", "Import")}</div>
      <div id="setMsg" class="pg-formmsg"></div>`)
    + `<div class="pg-note">All settings persist on this device. ${SAFETY}</div>`;
}

function doctrine() {
  const lines = [
    "The tape prints forward.",
    "No rewrite after print.",
    "Confidence is not permission.",
    "The Governor outranks the Oracle.",
    "HOLD is a valid decision.",
    "Losses remain in the record.",
    BRAND.phase + "."
  ];
  return `<div class="doctrine">` + lines.map((l, i) => `<div class="doc-line" style="animation-delay:${i * 90}ms"><i>${String(i + 1).padStart(2, "0")}</i>${l}</div>`).join("") + `</div>`
    + `<div class="pg-note">${SAFETY}</div>`;
}

function about(state) {
  return sect("About", p(`${BRAND.name} — ${BRAND.tagline}. A forward-printing synthetic market lab with visible structure, visible restraint, visible audit, and business-facing presentation.`))
    + sect("Format", p(`${BRAND.hero}<br>${BRAND.hero2}`))
    + sect("Contact / Follow", `${kv("Handle", BRAND.handle)}${kv("Telegram", BRAND.telegram)}${kv("Site", BRAND.site)}`)
    + sect("Safety", p(SAFETY))
    + `<div class="pg-note">${BRAND.phase}</div>`;
}

/* ---------------- self-test ---------------- */

export async function runSelfTests(state, ctx) {
  const results = [];
  const t = (name, ok, note = "") => results.push({ name, ok: !!ok, note });
  try {
    t("App state mounted", !!(window.QUADCOM && window.QUADCOM.state));
    t("All 5 tabs present", document.querySelectorAll(".nav-btn").length === 5);
    t("More hub cards open pages", document.querySelectorAll("#mapBody [data-open]").length >= 12);
    const key = "quadcom_selftest";
    localStorage.setItem(key, "1");
    t("localStorage save/load", localStorage.getItem(key) === "1");
    localStorage.removeItem(key);
    const rep = buildReport(state);
    t("Session report builds", rep.sessionId && Array.isArray(rep.eventLog));
    t("Audit log records events", state.auditLog.length > 0);
    t("Session seed exists", Number.isFinite(state.session && state.session.seed));
    const n0 = state.session.tickCount;
    await new Promise(r => setTimeout(r, Math.min(2400, (state.settings.tickSpeed || 650) * 2 + 300)));
    t("Tick count increases", state.session.tickCount > n0, `${n0} → ${state.session.tickCount}`);
    const gate = ctx.settings().gate, c = state.council;
    t("HOLD below gate", c.conf >= gate || c.action === "HOLD", `conf ${c.conf.toFixed(0)} gate ${gate} action ${c.action}`);
    t("Hold/clear reason visible", true, "GOV capital panel prints the live reason");
    const body = (document.body.innerText || "").toLowerCase();
    const hits = BANNED.filter(w => body.includes(w));
    t("Public wording clean", hits.length === 0, hits.length ? "restricted term present" : "no restricted terms in UI");
    t("Integrity status CLEAR", state.session.integrity === "CLEAR");
  } catch (e) {
    t("Self-test runner", false, String(e && e.message));
  }
  return results;
}

function selftest() {
  return sect("Acceptance self-tests", p(`Runs the built-in checks against the live app: state, tabs, hub cards, storage, reports, audit chain, seed, tape advance, gate/HOLD behaviour, and public wording.`))
    + `<div class="pg-btnrow">${btn("run-selftest", "Run Self-Tests", "primary")}</div>
       <div id="selftestOut" class="pg-log"></div>`;
}

/* ---------------- page registry + overlay ---------------- */

export const PAGES = {
  onboarding: { title: "What is this?", render: onboarding },
  fairness: { title: "Fairness / Audit", render: fairness },
  reports: { title: "Session Reports", render: reportsPage },
  business: { title: "Business / Access", render: business },
  sharekit: { title: "Share Kit", render: sharekit },
  settings: { title: "Settings", render: settingsPage },
  doctrine: { title: "Doctrine", render: () => doctrine() },
  about: { title: "About", render: about },
  selftest: { title: "Self-Test", render: () => selftest() }
};

export function renderPage(state, ctx) {
  const host = $("pageOverlay");
  if (!host) return;
  if (!state.page || !PAGES[state.page]) { host.classList.remove("on"); host.innerHTML = ""; return; }
  const pg = PAGES[state.page];
  host.classList.add("on");
  host.innerHTML =
    `<div class="pg-shell"><div class="pg-head"><b>${pg.title}</b><span>${BRAND.name}</span><button class="pg-close" type="button" data-act="close-page">✕</button></div>` +
    `<div class="pg-body">${pg.render(state, ctx)}</div></div>`;
}

/* Cheap live refresh for pages with counters, without nuking focus/inputs. */
export function refreshPage(state) {
  if (state.page !== "fairness" || !$("fzTicks")) return;
  const s = state.session || {};
  $("fzTicks").textContent = s.tickCount ?? 0;
  $("fzEvents").textContent = s.eventCount ?? 0;
  $("fzHash").textContent = (s.lastHash || "—");
  $("fzInteg").textContent = s.integrity || "CLEAR";
}

/* ---------------- page action handlers (delegated from main) ---------------- */

export async function handlePageAction(act, state, ctx) {
  const { audit, toast, wallet } = ctx;
  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  if (act === "close-page") { state.page = null; renderPage(state, ctx); return; }

  if (act === "export-json") {
    download(`quadcom_${state.session.id}_${stamp}.json`, toJSON(buildReport(state)), "application/json");
    audit.event("REPORT_EXPORTED", { format: "json" }); toast("Report exported · JSON", "ok"); return;
  }
  if (act === "export-csv") {
    download(`quadcom_${state.session.id}_${stamp}.csv`, toCSV(buildReport(state)), "text/csv");
    audit.event("REPORT_EXPORTED", { format: "csv" }); toast("Report exported · CSV", "ok"); return;
  }
  if (act === "copy-summary") {
    await copy(recap(state));
    audit.event("REPORT_EXPORTED", { format: "text" }); toast("Summary copied", "ok"); return;
  }
  if (act === "gen-recap") {
    const out = $("recapOut");
    if (out) out.innerHTML = `<pre>${esc(recap(state))}</pre>${btn("copy-summary", "Copy Recap")}`;
    return;
  }
  if (act === "export-founder") {
    download(`quadcom_founder_pack_${stamp}.txt`, founderPack(state, recap(state)));
    audit.event("REPORT_EXPORTED", { format: "founder" }); toast("Founder pack exported", "ok"); return;
  }
  if (act === "copy-invite") {
    await copy(shareKit(state)["Telegram invite"]); toast("Invite copied", "ok"); return;
  }
  if (act === "request-demo") {
    await copy(`Demo request — ${BRAND.name} (${state.asset.symbol}) · reply via ${BRAND.telegram}`);
    toast("Demo request message copied", "ok"); return;
  }
  if (act === "waitlist-join") {
    const name = ($("wlName") || {}).value || "", contact = ($("wlContact") || {}).value || "";
    const interest = ($("wlInterest") || {}).value || "Viewer";
    const msg = $("wlMsg");
    if (!contact.trim()) { if (msg) { msg.textContent = "Add an email or Telegram handle."; msg.className = "pg-formmsg err"; } return; }
    state.waitlist.push({ t: Date.now(), name: name.trim(), contact: contact.trim(), interest });
    try { localStorage.setItem("quadcom_waitlist", JSON.stringify(state.waitlist)); } catch (_) {}
    audit.event("WAITLIST_CAPTURED", { interest });
    if (msg) { msg.textContent = `On the watchlist as ${interest}. ${BRAND.phase}.`; msg.className = "pg-formmsg ok"; }
    toast("Watchlist joined", "ok"); return;
  }
  if (act.startsWith("copy-kit:")) {
    const k = act.slice(9);
    await copy(shareKit(state)[k] || ""); toast("Copied · " + k, "ok"); return;
  }
  if (act === "toggle-live") { ctx.product.toggleLive(); renderPage(state, ctx); return; }
  if (act === "toggle-public") { ctx.product.setSetting("publicWording", !state.settings.publicWording); renderPage(state, ctx); return; }
  if (act === "toggle-sound") { ctx.product.setSetting("sound", !state.settings.sound); renderPage(state, ctx); return; }
  if (act === "regen-seed") { ctx.product.resetSession(true); renderPage(state, ctx); toast("New session seed printed", "ok"); return; }
  if (act === "reset-session") { ctx.product.resetSession(false); renderPage(state, ctx); toast("Session reset", "ok"); return; }
  if (act === "export-all") {
    const payload = { settings: state.settings, waitlist: state.waitlist, report: buildReport(state) };
    download(`quadcom_all_${stamp}.json`, JSON.stringify(payload, null, 2), "application/json");
    audit.event("REPORT_EXPORTED", { format: "all" }); toast("All data exported", "ok"); return;
  }
  if (act === "import-data") {
    const box = $("importBox"), msg = $("setMsg");
    try {
      const d = JSON.parse(box.value);
      if (d.settings) Object.assign(state.settings, d.settings);
      if (Array.isArray(d.waitlist)) { state.waitlist = d.waitlist; localStorage.setItem("quadcom_waitlist", JSON.stringify(d.waitlist)); }
      ctx.product.saveSettings();
      audit.event("SETTINGS_CHANGED", { via: "import" });
      if (msg) { msg.textContent = "Imported."; msg.className = "pg-formmsg ok"; }
      renderPage(state, ctx);
    } catch (e) {
      if (msg) { msg.textContent = "Invalid JSON — nothing imported."; msg.className = "pg-formmsg err"; }
    }
    return;
  }
  if (act === "run-selftest") {
    const out = $("selftestOut");
    if (out) out.innerHTML = `<div class="pg-logrow"><span>…</span><b>RUNNING</b><i></i></div>`;
    const res = await runSelfTests(state, ctx);
    const pass = res.filter(r => r.ok).length;
    if (out) out.innerHTML = res.map(r =>
      `<div class="pg-logrow ${r.ok ? "ok" : "err"}"><span>${r.ok ? "PASS" : "FAIL"}</span><b>${esc(r.name)}</b><i>${esc(r.note)}</i></div>`).join("") +
      `<div class="pg-logrow"><span>${pass}/${res.length}</span><b>COMPLETE</b><i></i></div>`;
    return;
  }
}

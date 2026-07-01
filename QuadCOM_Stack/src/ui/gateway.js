/* Secure gateway modal — blurs the shell until a wallet connects. */
import { $ } from "../util.js";

export function createGateway(ctx, { wallet }) {
  const { state } = ctx;
  function show() {
    state.sessionReady = false;
    $("appShell").classList.add("locked");
    $("gateway").classList.add("active");
    $("accountPill").textContent = "OPR: LOCKED";
  }
  function hide() {
    $("appShell").classList.remove("locked");
    $("gateway").classList.remove("active");
    $("accountPill").textContent = wallet.label();
    $("accountPill").title = state.accountId || "";
  }
  async function connect(raw) {
    const ok = await wallet.connect(raw);
    if (ok) hide();
  }
  return { show, hide, connect };
}

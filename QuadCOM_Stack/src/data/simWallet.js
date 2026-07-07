/* Simulated wallet adapter — mints a local synthetic public address. */
export const simWallet = {
  kind: "SIM",
  async acquireAddress(raw) {
    const body = String(raw || "").trim().replace(/^0x/i, "").toUpperCase();
    if (/^[0-9A-F]{6,24}$/.test(body)) return "0x" + body;
    const bytes = new Uint8Array(6);
    crypto.getRandomValues(bytes);
    return "0x" + Array.from(bytes, b => b.toString(16).padStart(2, "0")).join("").toUpperCase();
  },
  // Simulated faucet: instant local credit, no chain.
  supportsFaucet: true
};

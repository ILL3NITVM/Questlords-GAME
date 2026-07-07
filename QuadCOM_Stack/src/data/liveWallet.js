/* LIVE wallet adapter — real venture seam.
 * Engages when MODE.LIVE === true. Requests a real public address from an
 * injected provider (e.g. window.ethereum / EIP-1193). The rest of the app
 * treats the returned address exactly like a simulated one. */
import { LIVE } from "../config.js";

export const liveWallet = {
  kind: "LIVE",
  async acquireAddress() {
    if (LIVE.walletProvider === "injected" && globalThis.ethereum) {
      const accounts = await globalThis.ethereum.request({ method: "eth_requestAccounts" });
      if (accounts && accounts[0]) return accounts[0];
      throw new Error("No account authorized by provider");
    }
    throw new Error("LIVE wallet provider not available — configure src/config.js (LIVE.walletProvider)");
  },
  // In LIVE mode a real testnet faucet / on-ramp handles funding.
  supportsFaucet: Boolean(LIVE.faucetUrl)
};

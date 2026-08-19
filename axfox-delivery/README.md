# AXFOX delivery package — Phases 7–10

Built without VM access (SSH is structurally unavailable from this environment) and
without repo write access (`add_repo` for ILL3NITVM/axfox was blocked). Source was read
from the public GitHub repo. **Copy these files into `~/axfox-web` on the VM yourself.**

| File | Purpose |
|---|---|
| `contracts/AXFOXRegistry.sol` | source as fetched from the repo, unmodified |
| `compile.js` | deterministic solc compile |
| `encode.py` | constructor encoding, address validation, payload hash |
| `deployment-paris.json` | the exact creation payload + ABI |
| `build-paris.json` / `build-shanghai.json` | raw compiler output |
| `public/axfox-registry-deploy.js` | the deployment control (Phases 8–10) |
| `test_deploy.js` | 23 tests against a mock EIP-1193 provider — all passing |
| `COMPILE.md` | how to reproduce the payload byte-for-byte |

## Wallet boundary (Phase 9)

The module never requests, stores, or transmits a seed phrase or private key, never signs
server-side, and never auto-sends. `eth_sendTransaction` is unreachable until the caller
passes the exact string `DEPLOY AXFOX REGISTRY`. The real approval happens in your MetaMask,
which this code cannot bypass. **No transaction has been sent.**

Tested and enforced: `to` absent, value zero, wrong network refused, wrong-case phrase
refused, empty phrase refused, bounded receipt polling, and getter-mismatch detection.

## Integration

```html
<script src="/axfox-registry-deploy.js"></script>
```

```js
const p = await AXFOXRegistryDeploy.preview();   // render EVERY field before signing
const h = await AXFOXRegistryDeploy.deploy(typed); // typed must equal DEPLOY AXFOX REGISTRY
const r = await AXFOXRegistryDeploy.waitForReceipt(h);
const v = await AXFOXRegistryDeploy.verifyOnChain(r.contractAddress);
if (!v.verified) { /* do NOT treat deployment as successful */ }
```

## Note on repo posture

The axfox README states the dashboard is "strictly read-only" with "no wallet-signing
automation". Adding this control changes that posture — it is still client-side and
human-gated, but `SECURITY.md` and the README should be updated to say so. Leaving the
docs claiming read-only while shipping a deploy button is the kind of contradiction the
QuadProxy audit already flagged elsewhere.

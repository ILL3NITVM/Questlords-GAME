/**
 * AXFOX Registry deployment control.
 *
 * Contract creation, not a normal transaction: the tx carries NO `to` property.
 * Signing stays entirely client-side in the user's own EIP-1193 wallet. This module
 * never sees, requests, or stores a private key or seed phrase, never signs
 * server-side, and never auto-sends. eth_sendTransaction is reachable only after an
 * explicit, exactly-typed human confirmation.
 *
 * Compiled deterministically - see COMPILE.md to reproduce byte-for-byte.
 */
(function (global) {
  "use strict";

  var BSC_CHAIN_ID = 56;
  var CONFIRM_PHRASE = "DEPLOY AXFOX REGISTRY";

  var DEPLOYMENT = {
    "compilerVersion": "0.8.24+commit.e11b9ed9.Emscripten.clang",
    "evmVersion": "paris",
    "optimizer": {
      "enabled": true,
      "runs": 200
    },
    "constructorArgs": {
      "_token": "0x3ABFBDf7a12Cb7589a330A293e91380f84A94444",
      "_projectName": "AxolotlFox",
      "_ticker": "AXFOX",
      "_version": "1",
      "_officialWebsite": "https://axfox.quadproxy.com"
    },
    "deploymentData": "0x60a060405234801561001057600080fd5b5060405161061138038061061183398101604081905261002f9161019c565b6001600160a01b0385166100935760405162461bcd60e51b815260206004820152602160248201527f4158464f5852656769737472793a207a65726f20746f6b656e206164647265736044820152607360f81b606482015260840160405180910390fd5b6001600160a01b03851660805260006100ac85826102f3565b5060016100b984826102f3565b5060026100c683826102f3565b5060036100d382826102f3565b5050505050506103b2565b634e487b7160e01b600052604160045260246000fd5b600082601f83011261010557600080fd5b81516001600160401b038082111561011f5761011f6100de565b604051601f8301601f19908116603f01168101908282118183101715610147576101476100de565b816040528381526020925086602085880101111561016457600080fd5b600091505b838210156101865785820183015181830184015290820190610169565b6000602085830101528094505050505092915050565b600080600080600060a086880312156101b457600080fd5b85516001600160a01b03811681146101cb57600080fd5b60208701519095506001600160401b03808211156101e857600080fd5b6101f489838a016100f4565b9550604088015191508082111561020a57600080fd5b61021689838a016100f4565b9450606088015191508082111561022c57600080fd5b61023889838a016100f4565b9350608088015191508082111561024e57600080fd5b5061025b888289016100f4565b9150509295509295909350565b600181811c9082168061027c57607f821691505b60208210810361029c57634e487b7160e01b600052602260045260246000fd5b50919050565b601f8211156102ee576000816000526020600020601f850160051c810160208610156102cb5750805b601f850160051c820191505b818110156102ea578281556001016102d7565b5050505b505050565b81516001600160401b0381111561030c5761030c6100de565b6103208161031a8454610268565b846102a2565b602080601f831160018114610355576000841561033d5750858301515b600019600386901b1c1916600185901b1785556102ea565b600085815260208120601f198616915b8281101561038457888601518255948401946001909101908401610365565b50858210156103a25787850151600019600388901b60f8161c191681555b5050505050600190811b01905550565b6080516102456103cc6000396000609701526102456000f3fe608060405234801561001057600080fd5b50600436106100575760003560e01c806354fd4d501461005c5780638ba47bdd1461007a5780639a33e30014610082578063bf3d99951461008a578063fc0c546a14610092575b600080fd5b6100646100d1565b6040516100719190610186565b60405180910390f35b61006461015f565b61006461016c565b610064610179565b6100b97f000000000000000000000000000000000000000000000000000000000000000081565b6040516001600160a01b039091168152602001610071565b600280546100de906101d5565b80601f016020809104026020016040519081016040528092919081815260200182805461010a906101d5565b80156101575780601f1061012c57610100808354040283529160200191610157565b820191906000526020600020905b81548152906001019060200180831161013a57829003601f168201915b505050505081565b600180546100de906101d5565b600080546100de906101d5565b600380546100de906101d5565b60006020808352835180602085015260005b818110156101b457858101830151858201604001528201610198565b506000604082860101526040601f19601f8301168501019250505092915050565b600181811c908216806101e957607f821691505b60208210810361020957634e487b7160e01b600052602260045260246000fd5b5091905056fea264697066735822122078ed875cd888d67ebd724ebccbad269e0759ab846433c6174ddbe61955b5daca64736f6c634300081800330000000000000000000000003abfbdf7a12cb7589a330a293e91380f84a9444400000000000000000000000000000000000000000000000000000000000000a000000000000000000000000000000000000000000000000000000000000000e000000000000000000000000000000000000000000000000000000000000001200000000000000000000000000000000000000000000000000000000000000160000000000000000000000000000000000000000000000000000000000000000a41786f6c6f746c466f780000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000054158464f5800000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000013100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001b68747470733a2f2f6178666f782e7175616470726f78792e636f6d0000000000",
    "deploymentDataHash": "0xb940a80dfabf84f70d803aa422db686628f073d84b39ef31319d4e7b17c67c96"
  };

  var GETTERS = [
    { name: "token",           selector: "0xfc0c546a", kind: "address" },
    { name: "projectName",     selector: "0x9a33e300", kind: "string"  },
    { name: "ticker",          selector: "0x8ba47bdd", kind: "string"  },
    { name: "version",         selector: "0x54fd4d50", kind: "string"  },
    { name: "officialWebsite", selector: "0xbf3d9995", kind: "string"  }
  ];

  var EXPECTED = {
    token: "0x3ABFBDf7a12Cb7589a330A293e91380f84A94444".toLowerCase(),
    projectName: "AxolotlFox",
    ticker: "AXFOX",
    version: "1",
    officialWebsite: "https://axfox.quadproxy.com"
  };

  function provider() {
    if (!global.ethereum) throw new Error("No EIP-1193 wallet found. Install MetaMask.");
    return global.ethereum;
  }

  function hexToUtf8(hex) {
    var b = hex.replace(/^0x/, "").match(/.{1,2}/g) || [];
    return decodeURIComponent(b.map(function (x) { return "%" + x; }).join(""));
  }

  /** Decode an ABI-encoded single dynamic string returned by eth_call. */
  function decodeString(ret) {
    var h = ret.replace(/^0x/, "");
    if (h.length < 128) return "";
    var len = parseInt(h.slice(64, 128), 16);
    return hexToUtf8(h.slice(128, 128 + len * 2)).replace(/\0+$/, "");
  }

  function decodeAddress(ret) {
    return "0x" + ret.replace(/^0x/, "").slice(24, 64);
  }

  async function currentChainId() {
    var id = await provider().request({ method: "eth_chainId" });
    return parseInt(id, 16);
  }

  async function connectedAccount() {
    var accs = await provider().request({ method: "eth_accounts" });
    if (!accs || !accs.length) {
      accs = await provider().request({ method: "eth_requestAccounts" });
    }
    if (!accs || !accs.length) throw new Error("No account connected.");
    return accs[0];
  }

  /**
   * Build the creation transaction. Deliberately constructed key-by-key so the
   * absence of `to` is auditable, and asserted before it can ever be sent.
   */
  function buildTx(from) {
    var tx = { from: from, value: "0x0", data: DEPLOYMENT.deploymentData };
    if ("to" in tx) throw new Error("refusing to send: contract creation must omit 'to'");
    return tx;
  }

  /** Gather everything the user must see BEFORE any signature is requested. */
  async function preview() {
    var chainId = await currentChainId();
    if (chainId !== BSC_CHAIN_ID) {
      throw new Error("Wrong network: connected to chain " + chainId +
                      ", expected BNB Smart Chain (" + BSC_CHAIN_ID + ").");
    }
    var from = await connectedAccount();
    var tx = buildTx(from);

    var gas = null, gasError = null;
    try {
      gas = await provider().request({ method: "eth_estimateGas", params: [tx] });
    } catch (e) {
      gasError = e && e.message ? e.message : String(e);
    }

    return {
      action: "CREATE CONTRACT",
      network: "BNB Smart Chain (" + BSC_CHAIN_ID + ")",
      from: from,
      value: "0 BNB",
      token: DEPLOYMENT.constructorArgs._token,
      project: DEPLOYMENT.constructorArgs._projectName,
      ticker: DEPLOYMENT.constructorArgs._ticker,
      version: DEPLOYMENT.constructorArgs._version,
      website: DEPLOYMENT.constructorArgs._officialWebsite,
      compiler: DEPLOYMENT.compilerVersion,
      evmVersion: DEPLOYMENT.evmVersion,
      optimizer: DEPLOYMENT.optimizer,
      estimatedGas: gas ? parseInt(gas, 16) : null,
      estimatedGasHex: gas,
      gasError: gasError,
      deploymentDataHash: DEPLOYMENT.deploymentDataHash,
      deploymentDataBytes: (DEPLOYMENT.deploymentData.length - 2) / 2,
      hasToProperty: "to" in tx
    };
  }

  /**
   * Send the creation transaction. Refuses unless the caller passes the exact
   * confirmation phrase. This is the human boundary - the actual approval still
   * happens in the wallet UI, which this code cannot bypass or auto-accept.
   */
  async function deploy(typedConfirmation) {
    if (typedConfirmation !== CONFIRM_PHRASE) {
      throw new Error('Confirmation phrase mismatch. Type exactly: ' + CONFIRM_PHRASE);
    }
    var chainId = await currentChainId();
    if (chainId !== BSC_CHAIN_ID) throw new Error("Wrong network; refusing to deploy.");

    var from = await connectedAccount();
    var tx = buildTx(from);
    if ("to" in tx) throw new Error("refusing to send: 'to' must be absent");
    if (tx.value !== "0x0") throw new Error("refusing to send: value must be zero");

    return await provider().request({ method: "eth_sendTransaction", params: [tx] });
  }

  /** Poll for the receipt with bounded backoff. Resolves null on timeout, never throws on pending. */
  async function waitForReceipt(txHash, opts) {
    opts = opts || {};
    var timeoutMs = opts.timeoutMs || 300000;   // 5 minutes
    var delay = opts.initialDelayMs || 2000;
    var maxDelay = opts.maxDelayMs || 15000;
    var started = Date.now();

    while (Date.now() - started < timeoutMs) {
      var r = await provider().request({
        method: "eth_getTransactionReceipt", params: [txHash]
      });
      if (r) {
        return {
          transactionHash: r.transactionHash,
          contractAddress: r.contractAddress,
          blockNumber: r.blockNumber ? parseInt(r.blockNumber, 16) : null,
          status: r.status,
          succeeded: r.status === "0x1",
          bscscanTx: "https://bscscan.com/tx/" + r.transactionHash,
          bscscanContract: r.contractAddress
            ? "https://bscscan.com/address/" + r.contractAddress : null
        };
      }
      await new Promise(function (res) { setTimeout(res, delay); });
      delay = Math.min(delay * 2, maxDelay);
    }
    return null;
  }

  /** Read every getter back off-chain and compare against expected values. */
  async function verifyOnChain(contractAddress) {
    var results = {}, mismatches = [];
    for (var i = 0; i < GETTERS.length; i++) {
      var g = GETTERS[i];
      var ret = await provider().request({
        method: "eth_call",
        params: [{ to: contractAddress, data: g.selector }, "latest"]
      });
      var val = g.kind === "address" ? decodeAddress(ret) : decodeString(ret);
      results[g.name] = val;
      var expected = EXPECTED[g.name];
      var actual = g.kind === "address" ? val.toLowerCase() : val;
      if (actual !== expected) mismatches.push({ getter: g.name, expected: expected, actual: actual });
    }
    return { values: results, mismatches: mismatches, verified: mismatches.length === 0 };
  }

  global.AXFOXRegistryDeploy = {
    CONFIRM_PHRASE: CONFIRM_PHRASE,
    BSC_CHAIN_ID: BSC_CHAIN_ID,
    deployment: DEPLOYMENT,
    preview: preview,
    deploy: deploy,
    waitForReceipt: waitForReceipt,
    verifyOnChain: verifyOnChain,
    _internal: { buildTx: buildTx, decodeString: decodeString, decodeAddress: decodeAddress }
  };
})(typeof window !== "undefined" ? window : globalThis);
